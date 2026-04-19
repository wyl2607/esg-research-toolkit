"""Backfill historical rows via the disclosures auto-fetch/approve lane.

Goal:
  Fill missing 2022/2023 rows for core DAX demo companies by dog-fooding
  /disclosures/fetch -> /disclosures/pending -> /disclosures/{id}/approve.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote

import httpx

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "scripts" / "seed_data" / "german_demo_manifest.json"

DEFAULT_API_BASE = os.environ.get("API_BASE", "http://localhost:8000")
DEFAULT_HTTP_TIMEOUT_SECONDS = float(os.environ.get("BACKFILL_HTTP_TIMEOUT", "30"))
DEFAULT_POLL_TIMEOUT_SECONDS = float(os.environ.get("BACKFILL_POLL_TIMEOUT", "90"))
DEFAULT_POLL_INTERVAL_SECONDS = float(os.environ.get("BACKFILL_POLL_INTERVAL", "1.5"))

DEFAULT_SOURCE_HINTS: list[str] = ["company_site", "sec_edgar", "hkex", "csrc"]

# Hardcoded targets (pulled from german_demo_manifest.json)
BACKFILL_TARGETS: list[tuple[str, int]] = [
    ("BASF SE", 2022),
    ("BASF SE", 2023),
    ("BMW AG", 2022),
    ("BMW AG", 2023),
    ("DHL Group", 2022),
    ("DHL Group", 2023),
    ("RWE AG", 2022),
    ("RWE AG", 2023),
    ("SAP SE", 2022),
    ("SAP SE", 2023),
    ("Volkswagen AG", 2022),
    ("Volkswagen AG", 2023),
]


class SupportsHTTP(Protocol):
    def get(self, url: str, **kwargs: Any) -> Any: ...

    def post(self, url: str, **kwargs: Any) -> Any: ...


@dataclass(frozen=True)
class BackfillResult:
    company_name: str
    report_year: int
    status: str
    detail: str = ""


def _load_manifest_pairs(path: Path = MANIFEST_PATH) -> set[tuple[str, int]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    companies = payload.get("companies")
    if not isinstance(companies, list):
        raise ValueError(f"Manifest is missing 'companies' array: {path}")
    pairs: set[tuple[str, int]] = set()
    for item in companies:
        if not isinstance(item, dict):
            continue
        company_name = item.get("company_name")
        report_year = item.get("report_year")
        if isinstance(company_name, str) and isinstance(report_year, int):
            pairs.add((company_name.strip(), report_year))
    return pairs


def validate_targets_against_manifest(targets: list[tuple[str, int]], path: Path = MANIFEST_PATH) -> None:
    manifest_pairs = _load_manifest_pairs(path)
    missing = [pair for pair in targets if pair not in manifest_pairs]
    if missing:
        raise ValueError(
            "Backfill targets missing from manifest: "
            + ", ".join(f"{company} {year}" for company, year in missing)
        )


def _history_years(client: SupportsHTTP, company_name: str) -> set[int]:
    encoded = quote(company_name, safe="")
    response = client.get(f"/report/companies/{encoded}/history")
    if response.status_code == 404:
        return set()
    if response.status_code != 200:
        raise RuntimeError(
            f"history request failed for {company_name}: "
            f"HTTP {response.status_code} {response.text[:200]}"
        )
    payload = response.json()
    years: set[int] = set()
    for period in payload.get("periods", []):
        if isinstance(period, dict) and isinstance(period.get("report_year"), int):
            years.add(period["report_year"])
    for point in payload.get("trend", []):
        if isinstance(point, dict) and isinstance(point.get("year"), int):
            years.add(point["year"])
    return years


def _derive_fetch_state(item: dict[str, Any] | None) -> str:
    if not item:
        return "pending"

    status = str(item.get("status", "")).lower()
    review_note = str(item.get("review_note") or "").lower()

    if status == "approved":
        return "ready"
    if status == "rejected":
        return "failed"
    if review_note.startswith("fetch_succeeded") or review_note.startswith("fetch_skipped_contract_mode"):
        return "ready"
    if review_note.startswith("fetch_failed") or review_note.startswith("fetch_no_public_pdf_found"):
        return "failed"
    return "pending"


def _select_pending_item(items: list[dict[str, Any]], pending_id: int | None) -> dict[str, Any] | None:
    if pending_id is None:
        return items[0] if items else None
    for item in items:
        if item.get("id") == pending_id:
            return item
    return items[0] if items else None


def _queue_fetch(
    client: SupportsHTTP,
    *,
    company_name: str,
    report_year: int,
    source_hints: list[str],
) -> tuple[int | None, str]:
    body: dict[str, Any] = {
        "company_name": company_name,
        "report_year": report_year,
        "source_hint": source_hints[0] if source_hints else "company_site",
        "source_hints": source_hints or DEFAULT_SOURCE_HINTS,
    }
    response = client.post("/disclosures/fetch", json=body)
    if response.status_code != 202:
        return None, f"fetch_http_{response.status_code}"
    pending = response.json().get("pending") or {}
    pending_id = pending.get("id")
    if not isinstance(pending_id, int):
        return None, "fetch_missing_pending_id"
    return pending_id, ""


def _poll_until_ready_or_failed(
    client: SupportsHTTP,
    *,
    company_name: str,
    report_year: int,
    pending_id: int,
    poll_timeout_seconds: float,
    poll_interval_seconds: float,
) -> tuple[str, dict[str, Any] | None]:
    deadline = time.monotonic() + poll_timeout_seconds
    current_item: dict[str, Any] | None = None

    while time.monotonic() <= deadline:
        response = client.get(
            "/disclosures/pending",
            params={
                "company_name": company_name,
                "report_year": report_year,
                "status": "pending",
                "limit": 20,
            },
        )
        if response.status_code != 200:
            return f"pending_http_{response.status_code}", current_item

        rows = response.json()
        if isinstance(rows, list):
            typed_rows = [row for row in rows if isinstance(row, dict)]
            current_item = _select_pending_item(typed_rows, pending_id)
        else:
            current_item = None

        state = _derive_fetch_state(current_item)
        if state in {"ready", "failed"}:
            return state, current_item

        if poll_interval_seconds > 0:
            time.sleep(poll_interval_seconds)

    return "timeout", current_item


def _approve_pending(client: SupportsHTTP, pending_id: int) -> tuple[str, str]:
    response = client.post(f"/disclosures/{pending_id}/approve", json={})
    if response.status_code == 200:
        return "approved", ""
    detail = ""
    try:
        detail = response.json().get("detail", "")
    except Exception:  # noqa: BLE001
        detail = response.text[:200]
    return f"approve_http_{response.status_code}", str(detail or "")


def run_backfill(
    client: SupportsHTTP,
    *,
    targets: list[tuple[str, int]] = BACKFILL_TARGETS,
    source_hints: list[str] | None = None,
    poll_timeout_seconds: float = DEFAULT_POLL_TIMEOUT_SECONDS,
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
) -> tuple[list[BackfillResult], dict[str, int]]:
    results: list[BackfillResult] = []
    hints = source_hints or DEFAULT_SOURCE_HINTS

    for company_name, report_year in targets:
        existing_years = _history_years(client, company_name)
        if report_year in existing_years:
            results.append(BackfillResult(company_name, report_year, "exists"))
            continue

        pending_id, queue_error = _queue_fetch(
            client,
            company_name=company_name,
            report_year=report_year,
            source_hints=hints,
        )
        if pending_id is None:
            results.append(BackfillResult(company_name, report_year, queue_error))
            continue

        fetch_state, pending_item = _poll_until_ready_or_failed(
            client,
            company_name=company_name,
            report_year=report_year,
            pending_id=pending_id,
            poll_timeout_seconds=poll_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
        if fetch_state == "ready":
            pending_id_from_item = pending_item.get("id") if isinstance(pending_item, dict) else pending_id
            if isinstance(pending_id_from_item, int):
                approve_status, detail = _approve_pending(client, pending_id_from_item)
                results.append(BackfillResult(company_name, report_year, approve_status, detail))
            else:
                results.append(BackfillResult(company_name, report_year, "approve_missing_pending_id"))
            continue

        detail = ""
        if isinstance(pending_item, dict):
            detail = str(pending_item.get("review_note") or "")
        results.append(BackfillResult(company_name, report_year, fetch_state, detail))

    coverage: dict[str, int] = {}
    for company_name, _ in targets:
        coverage[company_name] = len(_history_years(client, company_name))
    return results, coverage


def _print_table(results: list[BackfillResult]) -> None:
    headers = ("company", "year", "status", "detail")
    company_width = max(len(headers[0]), *(len(row.company_name) for row in results))
    year_width = max(len(headers[1]), 4)
    status_width = max(len(headers[2]), *(len(row.status) for row in results))
    detail_width = max(len(headers[3]), *(len(row.detail) for row in results))

    line = (
        f"{headers[0]:<{company_width}}  "
        f"{headers[1]:<{year_width}}  "
        f"{headers[2]:<{status_width}}  "
        f"{headers[3]:<{detail_width}}"
    )
    print(line)
    print("-" * len(line))
    for row in results:
        print(
            f"{row.company_name:<{company_width}}  "
            f"{row.report_year:<{year_width}}  "
            f"{row.status:<{status_width}}  "
            f"{row.detail:<{detail_width}}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill DAX history via disclosures fetch/approve lane.")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE, help=f"API base URL (default: {DEFAULT_API_BASE})")
    parser.add_argument(
        "--poll-timeout",
        type=float,
        default=DEFAULT_POLL_TIMEOUT_SECONDS,
        help=f"Seconds to wait for fetch readiness (default: {DEFAULT_POLL_TIMEOUT_SECONDS})",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
        help=f"Polling interval seconds (default: {DEFAULT_POLL_INTERVAL_SECONDS})",
    )
    parser.add_argument(
        "--http-timeout",
        type=float,
        default=DEFAULT_HTTP_TIMEOUT_SECONDS,
        help=f"HTTP timeout per request in seconds (default: {DEFAULT_HTTP_TIMEOUT_SECONDS})",
    )
    parser.add_argument(
        "--source-hint",
        action="append",
        dest="source_hints",
        choices=DEFAULT_SOURCE_HINTS,
        help="Optional source lane hint(s); repeat to set multiple lanes.",
    )
    parser.add_argument(
        "--min-companies",
        type=int,
        default=5,
        help="Require at least this many companies with >=3 years in history (default: 5).",
    )
    args = parser.parse_args()

    validate_targets_against_manifest(BACKFILL_TARGETS)
    source_hints = args.source_hints or DEFAULT_SOURCE_HINTS

    with httpx.Client(base_url=args.api_base, timeout=args.http_timeout) as client:
        results, coverage = run_backfill(
            client,
            targets=BACKFILL_TARGETS,
            source_hints=source_hints,
            poll_timeout_seconds=args.poll_timeout,
            poll_interval_seconds=args.poll_interval,
        )

    _print_table(results)

    companies_with_three_years = [company for company, years in coverage.items() if years >= 3]
    print("\nHistory coverage (years per company):")
    for company_name in sorted(coverage):
        print(f"- {company_name}: {coverage[company_name]} years")
    print(
        f"\nDone-check: {len(companies_with_three_years)} companies have >=3 years "
        f"(target >= {args.min_companies})"
    )

    return 0 if len(companies_with_three_years) >= args.min_companies else 1


if __name__ == "__main__":
    raise SystemExit(main())


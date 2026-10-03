#!/usr/bin/env python3
"""Read-only smoke check of the selected revision and dashboard data semantics."""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from collections.abc import Mapping
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.request import urlopen

from verify_dashboard_stats import _is_number, validate_payload


def validate_fingerprint(payload, expected_sha: str) -> None:
    if not isinstance(payload, Mapping) or payload.get("status") != "ok":
        raise ValueError("deploy health must report status ok")
    if payload.get("git_sha") != expected_sha:
        raise ValueError("serving git_sha does not match selected revision")


def validate_dashboard(stats, companies) -> None:
    validate_payload(stats)
    if not isinstance(companies, list) or any(not isinstance(row, Mapping) for row in companies):
        raise ValueError("companies response must be a list of objects")
    if any(not isinstance(row.get("company_name"), str) for row in companies):
        raise ValueError("companies response missing company_name")
    if stats["total_companies"] != len({row["company_name"] for row in companies}):
        raise ValueError("dashboard company count disagrees with source records")
    for average, field in (
        ("avg_taxonomy_aligned", "taxonomy_aligned_revenue_pct"),
        ("avg_renewable_pct", "renewable_energy_pct"),
    ):
        if any(field not in row for row in companies):
            raise ValueError(f"source records missing {field}")
        values = [row[field] for row in companies if row[field] is not None]
        if any(not _is_number(value) for value in values):
            raise ValueError(f"source records contain invalid {field}")
        expected = round(statistics.mean(values), 1) if values else None
        if stats[average] != expected:
            raise ValueError(f"{average} disagrees with source records (unknown must remain null)")


def read_url(url: str) -> str:
    with urlopen(url, timeout=10) as response:
        return response.read().decode("utf-8")


def verify(backend_url: str, frontend_url: str | None, expected_sha: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", expected_sha):
        raise ValueError("expected SHA must be a full commit hash")
    backend_url = backend_url.rstrip("/")
    health = json.loads(read_url(backend_url + "/health"))
    if not isinstance(health, Mapping) or health.get("status") != "ok":
        raise ValueError("backend health must report status ok")
    validate_fingerprint(json.loads(read_url(backend_url + "/health/deploy")), expected_sha)
    # Requests do not share a snapshot. Reread both sides on a mismatch in case
    # records changed during the comparison.
    for attempt in range(3):
        # A partial page can falsely classify a metric as unknown.
        companies = []
        while True:
            page = json.loads(read_url(backend_url + f"/report/companies?skip={len(companies)}&limit=50"))
            if not isinstance(page, list):
                raise ValueError("companies response must be a list")
            companies.extend(page)
            if len(page) < 50:
                break
        stats = json.loads(read_url(backend_url + "/report/dashboard/stats"))
        try:
            validate_dashboard(stats, companies)
        except ValueError:
            if attempt == 2:
                raise
            time.sleep(1)
        else:
            break
    if frontend_url:
        shell = read_url(frontend_url)
        entrypoint = re.search(r'<script\b[^>]*\btype="module"[^>]*\bsrc="([^"]+)"', shell)
        if not entrypoint or 'id="root"' not in shell:
            raise ValueError("frontend did not serve the built dashboard shell")
        if not read_url(urljoin(frontend_url, entrypoint[1])).strip():
            raise ValueError("frontend entrypoint is empty")
    # Catch a revision swap during the smoke check.
    validate_fingerprint(json.loads(read_url(backend_url + "/health/deploy")), expected_sha)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-url", required=True)
    parser.add_argument("--frontend-url", help="Optional public frontend check (outside local rollback smoke)")
    parser.add_argument("--expected-sha", required=True)
    args = parser.parse_args()
    try:
        verify(args.backend_url, args.frontend_url, args.expected_sha)
    except (ValueError, URLError, OSError) as exc:
        # Avoid logging response bodies or environment values on failure.
        reason = str(exc) if type(exc) is ValueError else type(exc).__name__
        print(f"post-deploy check failed: {reason}", file=sys.stderr)
        return 1
    print(f"OK post-deploy dashboard semantics; deployed SHA {args.expected_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

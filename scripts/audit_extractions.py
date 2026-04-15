"""Evidence-grounded audit of extracted ESG records.

For each target CompanyReport, re-read the cached PDF, send the
(extracted data + full text + verbatim-quote requirement) to gpt-4o,
parse the structured verdict per field, and write a markdown report.

Optional --apply writes back high-confidence corrections via the
existing /report/manual endpoint.

Usage:
  python scripts/audit_extractions.py
  python scripts/audit_extractions.py --company "RWE"
  python scripts/audit_extractions.py --slug rwe-2024
  python scripts/audit_extractions.py --apply
  python scripts/audit_extractions.py --dry-run
  python scripts/audit_extractions.py --model gpt-5.3-codex
  python scripts/audit_extractions.py --max-chars 80000

Environment:
  OPENAI_API_KEY   required unless --dry-run
  OPENAI_MODEL     optional default model (fallback gpt-4o)
  API_BASE         default http://localhost:8000
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
import re
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

import httpx

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.compute import BENCHMARK_METRICS  # noqa: E402
from core.schemas import ManualReportInput  # noqa: E402
from report_parser.extractor import extract_text_from_pdf  # noqa: E402
from scripts.seed_german_demo import MANIFEST_PATH, PDF_CACHE_DIR, SeedCompany, load_manifest  # noqa: E402

AUDIT_DIR = ROOT / "scripts" / "seed_data" / "audit_reports"
SUMMARY_PATH = AUDIT_DIR / "SUMMARY.md"
DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")
DEFAULT_MAX_CHARS = 80_000
DEFAULT_API_BASE = os.environ.get("API_BASE", "http://localhost:8000")

AUDIT_FIELDS: list[str] = list(BENCHMARK_METRICS)
VALID_VERDICTS = {"correct", "incorrect", "missed", "not_disclosed"}
VALID_CONFIDENCE = {"high", "medium", "low"}
MANUAL_INPUT_FIELDS = set(ManualReportInput.model_fields.keys())

Verdict = str  # "correct" | "incorrect" | "missed" | "not_disclosed"


@dataclass
class FieldAudit:
    field: str
    current_value: float | None
    verdict: Verdict
    corrected_value: float | None
    source_page_hint: int | None
    evidence_quote: str | None
    confidence: str  # "high" | "medium" | "low"
    reason: str | None


@dataclass
class CompanyAuditResult:
    slug: str
    company_name: str
    report_year: int
    fields: list[FieldAudit]
    db_company_name: str | None = None
    error: str | None = None

    def corrections_to_apply(self) -> dict[str, float | None]:
        """Return fields whose verdict + confidence qualifies for auto-apply."""
        out: dict[str, float | None] = {}
        for field_result in self.fields:
            if field_result.confidence != "high":
                continue
            if field_result.verdict in ("incorrect", "missed") and field_result.corrected_value is not None:
                out[field_result.field] = field_result.corrected_value
            elif field_result.verdict == "not_disclosed" and field_result.current_value is not None:
                out[field_result.field] = None
        return out


def _company_profile_url(api_base: str, company_name: str) -> str:
    encoded = quote(company_name, safe="")
    return f"{api_base}/report/companies/{encoded}/profile"


_CORPORATE_TOKENS = {
    "ag",
    "se",
    "plc",
    "inc",
    "ltd",
    "llc",
    "corp",
    "corporation",
    "co",
    "company",
    "group",
    "holdings",
    "holding",
}


def _normalize_company_name(name: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", name.lower())
    compact = [token for token in tokens if token not in _CORPORATE_TOKENS]
    return "".join(compact) if compact else "".join(tokens)


def _extract_years_from_company_row(entry: dict[str, Any]) -> set[int]:
    years: set[int] = set()
    for key in ("report_year", "latest_report_year", "year"):
        value = entry.get(key)
        if isinstance(value, int):
            years.add(value)
        elif isinstance(value, str):
            try:
                years.add(int(value.strip()))
            except ValueError:
                continue

    years_available = entry.get("years_available")
    if isinstance(years_available, list):
        for value in years_available:
            if isinstance(value, int):
                years.add(value)
            elif isinstance(value, str):
                try:
                    years.add(int(value.strip()))
                except ValueError:
                    continue
    return years


def resolve_company_name(api_base: str, company_name: str, report_year: int) -> str | None:
    company_directory = fetch_company_directory(api_base)
    return resolve_company_name_from_directory(company_name, report_year, company_directory)


def fetch_company_directory(api_base: str) -> list[dict[str, Any]] | None:
    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(f"{api_base}/report/companies")
    except httpx.HTTPError:
        return None

    if response.status_code != 200:
        return None

    try:
        payload = response.json()
    except ValueError:
        return None
    if not isinstance(payload, list):
        return None
    return [entry for entry in payload if isinstance(entry, dict)]


def resolve_company_name_from_directory(
    company_name: str,
    report_year: int,
    company_directory: list[dict[str, Any]] | None,
) -> str | None:
    if not company_directory:
        return None

    target = _normalize_company_name(company_name)
    if not target:
        return None

    for entry in company_directory:
        candidate_name = entry.get("company_name")
        if not isinstance(candidate_name, str) or not candidate_name.strip():
            continue
        years = _extract_years_from_company_row(entry)
        if years and report_year not in years:
            continue
        if _normalize_company_name(candidate_name) == target:
            return candidate_name

    return None


def build_prompt(
    company_name: str,
    report_year: int,
    industry_sector: str | None,
    extracted: dict[str, Any],
    source_text: str,
) -> str:
    """Build the audit prompt with mandatory verbatim quote evidence."""
    extracted_subset = {field_name: extracted.get(field_name) for field_name in AUDIT_FIELDS}
    return f"""You are an ESG data auditor. You review previously extracted metrics against the original sustainability report text.

For each field below, return a JSON object with keys:
  current_value        - what was previously extracted (echoed back)
  verdict              - "correct" | "incorrect" | "missed" | "not_disclosed"
  corrected_value      - numeric correction or null
  source_page_hint     - page number if identifiable, else null
  evidence_quote       - VERBATIM sentence (max 200 chars) containing the number, or null if not_disclosed
  confidence           - "high" | "medium" | "low"
  reason               - brief explanation (max 120 chars)

Rules:
- "correct": current_value matches the document; set corrected_value=null
- "incorrect": document contains a different value (e.g. unit error, wrong scope); provide corrected_value + quote
- "missed": current_value is null but the document DOES disclose this metric; provide corrected_value + quote
- "not_disclosed": current_value is null (or spurious) and the document does NOT disclose this metric; evidence_quote=null
- confidence="high" ONLY if you can quote the exact sentence. If you are inferring, use "medium" or "low".
- Watch for common errors: year numbers (e.g. 2024) being confused with metric values; tonnes vs kilotonnes; % vs absolute.
- All corrected values must be numbers in the canonical unit (tonnes for emissions, MWh for energy, m3 for water, % for percentages).
- Return STRICT JSON with keys exactly matching the field names listed below.

COMPANY: {company_name}
REPORT YEAR: {report_year}
INDUSTRY: {industry_sector or "(unknown)"}

PREVIOUSLY EXTRACTED:
{json.dumps(extracted_subset, indent=2, ensure_ascii=False)}

SOURCE DOCUMENT (truncated to first chunk):
---
{source_text}
---

Return a JSON object with these exact top-level keys:
{json.dumps({field_name: "..." for field_name in AUDIT_FIELDS}, indent=2)}
"""


def _as_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_page_hint(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def parse_audit_response(raw: str, current_record: dict[str, Any]) -> list[FieldAudit]:
    payload = _extract_json_payload(raw)

    results: list[FieldAudit] = []
    for field_name in AUDIT_FIELDS:
        entry = payload.get(field_name)
        if not isinstance(entry, dict):
            entry = {}

        verdict = str(entry.get("verdict", "")).strip().lower() or "not_disclosed"
        if verdict not in VALID_VERDICTS:
            verdict = "not_disclosed"

        confidence = str(entry.get("confidence", "low")).strip().lower() or "low"
        if confidence not in VALID_CONFIDENCE:
            confidence = "low"

        evidence_quote_value = entry.get("evidence_quote")
        reason_value = entry.get("reason")
        results.append(
            FieldAudit(
                field=field_name,
                current_value=_as_number(current_record.get(field_name)),
                verdict=verdict,
                corrected_value=_as_number(entry.get("corrected_value")),
                source_page_hint=_as_page_hint(entry.get("source_page_hint")),
                evidence_quote=evidence_quote_value if isinstance(evidence_quote_value, str) else None,
                confidence=confidence,
                reason=reason_value if isinstance(reason_value, str) else None,
            )
        )
    return results


def _iter_json_objects(text: str):
    start = text.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
                continue
            if char == "{":
                depth += 1
                continue
            if char == "}":
                depth -= 1
                if depth == 0:
                    yield text[start : index + 1]
                    break

        start = text.find("{", start + 1)


def _extract_json_payload(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if not text:
        raise ValueError("audit response was empty")

    candidates: list[str] = []
    fence_pattern = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
    for match in fence_pattern.finditer(text):
        fenced = match.group(1).strip()
        candidates.extend(_iter_json_objects(fenced))
    candidates.extend(_iter_json_objects(text))

    if not candidates:
        raise ValueError("audit response did not contain a JSON object")

    best_payload: dict[str, Any] | None = None
    best_score = -1
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        score = sum(1 for field_name in AUDIT_FIELDS if field_name in payload)
        if score > best_score:
            best_score = score
            best_payload = payload
            if score == len(AUDIT_FIELDS):
                break

    if best_payload is None:
        raise ValueError("audit response was not valid JSON object")
    if best_score <= 0:
        raise ValueError("audit response JSON missing expected audit fields")
    return best_payload


def fetch_company_profile(
    api_base: str,
    company_name: str,
    *,
    report_year: int | None = None,
    company_directory: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(_company_profile_url(api_base, company_name))
    except httpx.HTTPError:
        response = None

    if response is not None and response.status_code == 200:
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict):
            return payload, company_name

    if report_year is None:
        return None, None

    resolved_name = resolve_company_name_from_directory(company_name, report_year, company_directory)
    if not resolved_name and company_directory is None:
        resolved_name = resolve_company_name(api_base, company_name, report_year)
    if not resolved_name or resolved_name == company_name:
        return None, None

    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(_company_profile_url(api_base, resolved_name))
    except httpx.HTTPError:
        return None, None

    if response.status_code != 200:
        return None, None
    try:
        payload = response.json()
    except ValueError:
        return None, None
    if not isinstance(payload, dict):
        return None, None
    return payload, resolved_name


def audit_one(
    company: SeedCompany,
    *,
    api_base: str,
    model: str,
    max_chars: int,
    openai_client: Any | None,
    dry_run: bool,
    company_directory: list[dict[str, Any]] | None = None,
) -> CompanyAuditResult:
    print(f"\n-> auditing {company.company_name} ({company.report_year}) [{company.slug}]")

    pdf_path = PDF_CACHE_DIR / f"{company.slug}.pdf"
    if not pdf_path.exists():
        return CompanyAuditResult(
            slug=company.slug,
            company_name=company.company_name,
            report_year=company.report_year,
            fields=[],
            error=f"PDF cache missing: {pdf_path}",
        )

    current_metrics: dict[str, Any] = {}
    if not dry_run:
        profile, resolved_name = fetch_company_profile(
            api_base,
            company.company_name,
            report_year=company.report_year,
            company_directory=company_directory,
        )
        profile = profile or {}
        latest_metrics = profile.get("latest_metrics") or {}
        if not isinstance(latest_metrics, dict) or not latest_metrics:
            return CompanyAuditResult(
                slug=company.slug,
                company_name=company.company_name,
                report_year=company.report_year,
                fields=[],
                error="record not found in DB; run seed first",
            )
        db_company_name = resolved_name or company.company_name
        if db_company_name != company.company_name:
            print(f"  profile resolved as DB name: {db_company_name}")
        current_metrics = latest_metrics

    source_text = extract_text_from_pdf(pdf_path)
    if len(source_text) > max_chars:
        source_text = source_text[:max_chars] + "\n\n[truncated]"
    print(f"  pdf text chars: {len(source_text)}")

    prompt = build_prompt(
        company_name=company.company_name,
        report_year=company.report_year,
        industry_sector=company.industry_sector,
        extracted=current_metrics,
        source_text=source_text,
    )

    if dry_run:
        print("  [dry-run] skipping OpenAI call")
        return CompanyAuditResult(
            slug=company.slug,
            company_name=company.company_name,
            report_year=company.report_year,
            fields=[],
            error="dry-run",
        )

    assert openai_client is not None
    try:
        completion = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0,
        )
    except Exception as exc:  # noqa: BLE001 - keep batch process resilient
        return CompanyAuditResult(
            slug=company.slug,
            company_name=company.company_name,
            report_year=company.report_year,
            fields=[],
            error=f"openai: {exc}",
        )

    raw = completion.choices[0].message.content or "{}"
    try:
        fields = parse_audit_response(raw, current_metrics)
    except ValueError as exc:
        return CompanyAuditResult(
            slug=company.slug,
            company_name=company.company_name,
            report_year=company.report_year,
            fields=[],
            error=f"parse: {exc}",
        )

    correct_count = sum(1 for field_result in fields if field_result.verdict == "correct")
    incorrect_count = sum(1 for field_result in fields if field_result.verdict == "incorrect")
    missed_count = sum(1 for field_result in fields if field_result.verdict == "missed")
    not_disclosed_count = sum(1 for field_result in fields if field_result.verdict == "not_disclosed")
    print(
        "  audited - "
        f"{correct_count} correct, "
        f"{incorrect_count} incorrect, "
        f"{missed_count} missed, "
        f"{not_disclosed_count} not_disclosed"
    )
    return CompanyAuditResult(
        slug=company.slug,
        company_name=company.company_name,
        report_year=company.report_year,
        fields=fields,
        db_company_name=db_company_name if not dry_run else None,
    )


def write_company_report(result: CompanyAuditResult) -> Path:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    path = AUDIT_DIR / f"{result.slug}.md"
    lines: list[str] = [
        f"# Audit - {result.company_name} ({result.report_year})",
        "",
        f"Slug: `{result.slug}`",
        "",
    ]
    if result.error:
        lines.append(f"**Status**: failed ({result.error})")
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    for field_result in result.fields:
        lines.append(f"## `{field_result.field}` - {field_result.verdict} ({field_result.confidence})")
        lines.append("")
        lines.append(f"- current: `{field_result.current_value}`")
        if field_result.corrected_value is not None or field_result.verdict in ("incorrect", "missed"):
            lines.append(f"- corrected: `{field_result.corrected_value}`")
        if field_result.source_page_hint is not None:
            lines.append(f"- page: {field_result.source_page_hint}")
        if field_result.evidence_quote:
            lines.append(f"- quote: {field_result.evidence_quote}")
        if field_result.reason:
            lines.append(f"- reason: {field_result.reason}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_summary(results: list[CompanyAuditResult]) -> Path:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    total_fields = sum(len(result.fields) for result in results)
    correct = sum(1 for result in results for field_result in result.fields if field_result.verdict == "correct")
    incorrect = sum(
        1 for result in results for field_result in result.fields if field_result.verdict == "incorrect"
    )
    missed = sum(1 for result in results for field_result in result.fields if field_result.verdict == "missed")
    not_disclosed = sum(
        1 for result in results for field_result in result.fields if field_result.verdict == "not_disclosed"
    )
    errors = [result for result in results if result.error]

    lines = [
        "# Extraction Audit - Summary",
        "",
        f"Total companies: {len(results)}",
        f"Total fields audited: {total_fields}",
        "",
        "| Verdict | Count |",
        "|---|---|",
        f"| correct | {correct} |",
        f"| incorrect | {incorrect} |",
        f"| missed | {missed} |",
        f"| not_disclosed | {not_disclosed} |",
        "",
    ]
    if errors:
        lines.append("## Errors")
        for result in errors:
            lines.append(f"- {result.company_name}: {result.error}")
        lines.append("")

    lines.append("## Per-company reports")
    for result in results:
        report_link = f"./{result.slug}.md"
        if result.error:
            lines.append(f"- [{result.company_name}]({report_link}) - failed ({result.error})")
        else:
            flags = sum(1 for field_result in result.fields if field_result.verdict in ("incorrect", "missed"))
            lines.append(f"- [{result.company_name}]({report_link}) - {flags} flags")

    SUMMARY_PATH.write_text("\n".join(lines), encoding="utf-8")
    return SUMMARY_PATH


def _latest_source_url(profile: dict[str, Any]) -> str | None:
    latest_sources = profile.get("latest_sources")
    if not isinstance(latest_sources, list):
        return None
    for source in latest_sources:
        if not isinstance(source, dict):
            continue
        source_url = source.get("source_url")
        if isinstance(source_url, str) and source_url:
            return source_url
    return None


def apply_corrections(
    api_base: str,
    result: CompanyAuditResult,
    *,
    company_directory: list[dict[str, Any]] | None = None,
) -> bool:
    """
    Reuse POST /report/manual to write corrected ManualReportInput data.
    """
    corrections = result.corrections_to_apply()
    if not corrections:
        return False

    canonical_name = result.db_company_name or result.company_name
    profile, _ = fetch_company_profile(
        api_base,
        canonical_name,
        report_year=result.report_year,
        company_directory=company_directory,
    )
    if not profile:
        print("  apply skipped: cannot fetch company profile")
        return False

    current_metrics = profile.get("latest_metrics") or {}
    if not isinstance(current_metrics, dict):
        print("  apply skipped: latest_metrics payload invalid")
        return False

    merged = dict(current_metrics)
    merged.update(corrections)
    merged["company_name"] = canonical_name
    merged["report_year"] = result.report_year
    source_url = _latest_source_url(profile)
    if source_url:
        merged["source_url"] = source_url
    payload = {key: value for key, value in merged.items() if key in MANUAL_INPUT_FIELDS}

    with httpx.Client(timeout=60) as client:
        response = client.post(f"{api_base}/report/manual", json=payload)
    if response.status_code != 200:
        print(f"  apply failed: {response.status_code} {response.text[:200]}")
        return False

    print(f"  applied {len(corrections)} correction(s): {', '.join(sorted(corrections.keys()))}")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--company", help="filter by company_name substring")
    parser.add_argument("--slug", help="filter by exact manifest slug")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument("--workers", type=int, default=1, help="number of companies to audit concurrently")
    parser.add_argument("--apply", action="store_true", help="auto-apply high-confidence corrections")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        companies = load_manifest()
    except Exception as exc:  # noqa: BLE001 - CLI error surface
        print(f"failed to load manifest {MANIFEST_PATH}: {exc}")
        return 2

    if args.slug:
        companies = [company for company in companies if company.slug == args.slug]
    if args.company:
        needle = args.company.lower()
        companies = [company for company in companies if needle in company.company_name.lower()]
    if not companies:
        print("no companies matched filter")
        return 1

    openai_client = None
    openai_client_factory: Callable[[], Any] | None = None
    company_directory: list[dict[str, Any]] | None = None
    if not args.dry_run:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key or api_key == "dummy":
            print("OPENAI_API_KEY not set; use --dry-run for offline mode")
            return 2
        try:
            from openai import OpenAI  # type: ignore
        except ImportError:
            print("openai package not installed")
            return 2
        openai_client_factory = lambda: OpenAI(api_key=api_key)
        company_directory = fetch_company_directory(args.api_base)

    workers = max(1, args.workers)
    workers = min(workers, len(companies))
    if workers > 1:
        print(f"running with {workers} workers")

    client_local = threading.local()
    if workers == 1 and openai_client_factory is not None:
        openai_client = openai_client_factory()

    def _run_company(company: SeedCompany) -> CompanyAuditResult:
        try:
            local_client = openai_client
            if local_client is None and openai_client_factory is not None:
                if workers == 1:
                    local_client = openai_client_factory()
                else:
                    local_client = getattr(client_local, "openai_client", None)
                    if local_client is None:
                        local_client = openai_client_factory()
                        client_local.openai_client = local_client
            return audit_one(
                company,
                api_base=args.api_base,
                model=args.model,
                max_chars=args.max_chars,
                openai_client=local_client,
                dry_run=args.dry_run,
                company_directory=company_directory,
            )
        except Exception as exc:  # noqa: BLE001 - keep batch process resilient
            return CompanyAuditResult(
                slug=company.slug,
                company_name=company.company_name,
                report_year=company.report_year,
                fields=[],
                error=f"worker: {exc}",
            )

    results: list[CompanyAuditResult] = []
    any_applied = False
    if workers == 1:
        for company in companies:
            result = _run_company(company)
            results.append(result)
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(_run_company, companies))

    for result in results:
        report_path = write_company_report(result)
        print(f"  wrote {report_path.relative_to(ROOT)}")

        if args.apply and not args.dry_run and not result.error:
            if apply_corrections(
                args.api_base,
                result,
                company_directory=company_directory,
            ):
                any_applied = True

    summary_path = write_summary(results)
    print(f"\nsummary: {summary_path.relative_to(ROOT)}")

    if any_applied:
        print("\ntriggering benchmark recompute...")
        with httpx.Client(timeout=60) as client:
            recompute_response = client.post(f"{args.api_base}/benchmarks/recompute")
            print(f"  status={recompute_response.status_code} body={recompute_response.text[:200]}")

    has_errors = any(result.error not in (None, "dry-run") for result in results)
    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main())

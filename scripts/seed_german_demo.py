"""German demo seed pipeline.

Phase A (default): for each manifest entry, download the PDF (or
load from local cache), POST it to /report/upload with the NACE
industry code, then trigger /benchmarks/recompute once at the end.

Phase B (--validate): for each seeded company, re-fetch the profile
and ask the configured validation model whether any extracted
numbers look hallucinated or anomalous given the evidence snippets.
Write findings to scripts/seed_data/anomalies_report.md.

Reset (--reset): delete every CompanyReport row covered by the
manifest (company_name + report_year), then recompute benchmarks.

Usage:
  python scripts/seed_german_demo.py                 # Phase A only
  python scripts/seed_german_demo.py --only rwe-2024 --only "RWE AG"
  python scripts/seed_german_demo.py --validate      # Phase A + B
  python scripts/seed_german_demo.py --validate-only # Phase B only
  python scripts/seed_german_demo.py --reset         # wipe seed rows
  python scripts/seed_german_demo.py --dry-run       # no network, no DB writes
  python scripts/seed_german_demo.py --slug rwe-2024 --slug basf-2024
  python scripts/seed_german_demo.py --company "RWE AG" --company "BASF SE"

Environment:
  API_BASE        default http://localhost:8000
  OPENAI_API_KEY  required for Phase B
  SEED_TIMEOUT    per-company timeout in seconds (default 300)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import httpx

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import settings
from core.ai_client import get_client
from core.database import SessionLocal, engine
from report_parser.storage import ensure_storage_schema, record_extraction_run

MANIFEST_PATH = ROOT / "scripts" / "seed_data" / "german_demo_manifest.json"
PDF_CACHE_DIR = ROOT / "scripts" / "seed_data" / "pdfs"
ANOMALIES_REPORT_PATH = ROOT / "scripts" / "seed_data" / "anomalies_report.md"
DEFAULT_API_BASE = os.environ.get("API_BASE", "http://localhost:8000")
DEFAULT_TIMEOUT = float(os.environ.get("SEED_TIMEOUT", "300"))
PDF_DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass(frozen=True)
class SeedCompany:
    slug: str
    company_name: str
    report_year: int
    industry_code: str
    industry_sector: str
    source_url: str
    verify: bool

    @classmethod
    def from_dict(cls, entry: dict) -> "SeedCompany":
        required = (
            "slug",
            "company_name",
            "report_year",
            "industry_code",
            "industry_sector",
            "source_url",
        )
        missing = [k for k in required if k not in entry]
        if missing:
            raise ValueError(f"manifest entry missing fields: {missing}")

        return cls(
            slug=str(entry["slug"]).strip(),
            company_name=str(entry["company_name"]).strip(),
            report_year=int(entry["report_year"]),
            industry_code=str(entry["industry_code"]).strip(),
            industry_sector=str(entry["industry_sector"]).strip(),
            source_url=str(entry["source_url"]).strip(),
            verify=bool(entry.get("verify", False)),
        )


def load_manifest(path: Path = MANIFEST_PATH) -> list[SeedCompany]:
    if not path.exists():
        raise FileNotFoundError(f"manifest not found: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("companies"), list):
        raise ValueError("manifest must be an object with a 'companies' array")

    companies = [SeedCompany.from_dict(entry) for entry in raw["companies"]]
    if not companies:
        raise ValueError("manifest has zero companies")
    return companies


def _normalize_filter_values(values: list[str] | None) -> set[str]:
    normalized: set[str] = set()
    for value in values or []:
        for token in value.split(","):
            cleaned = token.strip().lower()
            if cleaned:
                normalized.add(cleaned)
    return normalized


def filter_companies(
    companies: list[SeedCompany],
    *,
    slugs: list[str] | None = None,
    company_names: list[str] | None = None,
    only_filters: list[str] | None = None,
) -> list[SeedCompany]:
    selected = companies

    normalized_only = _normalize_filter_values(only_filters)
    if normalized_only:
        return [
            company
            for company in selected
            if company.slug.lower() in normalized_only or company.company_name.lower() in normalized_only
        ]

    normalized_slugs = _normalize_filter_values(slugs)
    if normalized_slugs:
        selected = [company for company in selected if company.slug.lower() in normalized_slugs]

    normalized_names = _normalize_filter_values(company_names)
    if normalized_names:
        selected = [company for company in selected if company.company_name.lower() in normalized_names]

    return selected


def _is_probably_pdf(content: bytes) -> bool:
    return len(content) > 1024 and content.lstrip().startswith(b"%PDF")


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _record_extract_run(company: SeedCompany, pdf_path: Path, payload: dict) -> None:
    parsed_name = payload.get("company_name") if isinstance(payload.get("company_name"), str) else company.company_name
    parsed_year = payload.get("report_year") if isinstance(payload.get("report_year"), int) else company.report_year
    notes = f"Seed extraction succeeded for {parsed_name} {parsed_year} from {pdf_path.name}."

    try:
        ensure_storage_schema(engine)
        with SessionLocal() as db:
            record_extraction_run(
                db,
                run_kind="extract",
                file_hash=_hash_file(pdf_path),
                model=settings.openai_model,
                notes=notes,
            )
    except Exception as exc:  # noqa: BLE001 - audit trail must not break existing seed flow
        print(f"  ⚠️ failed to record extraction run: {exc}")


def ensure_pdf(company: SeedCompany, *, dry_run: bool, timeout: float) -> Path | None:
    """Return local PDF path, downloading if cache miss."""
    PDF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    local_path = PDF_CACHE_DIR / f"{company.slug}.pdf"

    if local_path.exists() and local_path.stat().st_size > 1024:
        return local_path

    if dry_run:
        print(f"  [dry-run] would download {company.source_url}")
        return local_path

    print(f"  downloading {company.source_url}")
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(company.source_url, headers=PDF_DOWNLOAD_HEADERS)
    except httpx.HTTPError as exc:
        print(f"  ⚠️ download error: {exc}")
        print(f"  → place manual PDF at {local_path} and retry")
        return None

    if response.status_code != 200:
        print(f"  ⚠️ download failed: HTTP {response.status_code}")
        print(f"  → place manual PDF at {local_path} and retry")
        return None

    content = response.content
    if not _is_probably_pdf(content):
        print(
            "  ⚠️ download succeeded but content does not look like a valid PDF "
            f"(bytes={len(content)})"
        )
        print(f"  → place manual PDF at {local_path} and retry")
        return None

    local_path.write_bytes(content)
    return local_path


def _company_profile_url(api_base: str, company_name: str) -> str:
    encoded = quote(company_name, safe="")
    return f"{api_base}/report/companies/{encoded}/profile"


def already_seeded(api_base: str, company: SeedCompany) -> bool:
    """Skip upload when same company/year already present."""
    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(_company_profile_url(api_base, company.company_name))
    except httpx.HTTPError:
        return False

    if response.status_code != 200:
        return False

    try:
        payload = response.json()
    except ValueError:
        return False

    years_available = payload.get("years_available") or []
    return company.report_year in years_available


def upload_company(api_base: str, company: SeedCompany, pdf_path: Path, *, timeout: float) -> dict | None:
    print(f"  uploading {company.company_name} ({company.industry_code})...")
    with httpx.Client(timeout=timeout) as client:
        with pdf_path.open("rb") as fh:
            response = client.post(
                f"{api_base}/report/upload",
                files={"file": (pdf_path.name, fh, "application/pdf")},
                data={
                    "industry_code": company.industry_code,
                    "industry_sector": company.industry_sector,
                    "override_company_name": company.company_name,
                },
            )

    if response.status_code != 200:
        print(f"  ❌ upload failed: {response.status_code} {response.text[:200]}")
        return None

    try:
        payload = response.json()
    except ValueError:
        print("  ❌ upload returned non-JSON response")
        return None

    report_year = payload.get("report_year", "?")
    parsed_name = payload.get("company_name", "?")
    print(f"  ✅ extracted: {parsed_name} {report_year}")
    return payload


def trigger_recompute(api_base: str) -> dict | None:
    print("triggering benchmark recompute...")
    with httpx.Client(timeout=60) as client:
        response = client.post(f"{api_base}/benchmarks/recompute")
    if response.status_code != 200:
        print(f"❌ recompute failed: {response.status_code} {response.text[:200]}")
        return None

    payload = response.json()
    print(f"✅ recomputed: {payload}")
    return payload


def phase_a(api_base: str, companies: list[SeedCompany], *, dry_run: bool, timeout: float) -> dict:
    succeeded: list[str] = []
    failed: list[tuple[str, str]] = []
    skipped: list[str] = []

    verify_warnings = [company.slug for company in companies if company.verify]
    if verify_warnings:
        print(
            "⚠️ Manifest contains entries marked verify=true. "
            "Confirm URLs before relying on auto-download:"
        )
        for slug in verify_warnings:
            print(f"   - {slug}")

    for company in companies:
        print(f"\n→ {company.company_name} ({company.report_year}) [{company.slug}]")

        if not dry_run and already_seeded(api_base, company):
            print("  ↺ already seeded, skipping")
            skipped.append(company.slug)
            continue

        pdf_path = ensure_pdf(company, dry_run=dry_run, timeout=timeout)
        if pdf_path is None:
            failed.append((company.slug, "no PDF available"))
            continue

        if dry_run:
            print(f"  [dry-run] would upload {pdf_path}")
            succeeded.append(company.slug)
            continue

        result = upload_company(api_base, company, pdf_path, timeout=timeout)
        if result is None:
            failed.append((company.slug, "upload failed"))
            continue

        _record_extract_run(company, pdf_path, result)
        succeeded.append(company.slug)

    if not dry_run and succeeded:
        trigger_recompute(api_base)

    summary = {
        "succeeded": succeeded,
        "failed": failed,
        "skipped": skipped,
        "total": len(companies),
    }
    print("\n=== Phase A summary ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def phase_b(api_base: str, companies: list[SeedCompany]) -> None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or api_key == "dummy":
        print("❌ OPENAI_API_KEY not set (or set to 'dummy'); skipping Phase B")
        return

    try:
        ai_client = get_client()
    except ImportError:
        print("❌ openai package not installed; pip install openai and retry")
        return

    validation_model = settings.openai_validation_model
    findings: list[dict] = []

    print(f"running Phase B sanity checks for {len(companies)} companies...")
    with httpx.Client(timeout=60) as client:
        for company in companies:
            try:
                profile_resp = client.get(_company_profile_url(api_base, company.company_name))
            except httpx.HTTPError as exc:
                findings.append({"company": company.company_name, "issue": f"network: {exc}"})
                continue

            if profile_resp.status_code != 200:
                findings.append(
                    {"company": company.company_name, "issue": f"profile fetch {profile_resp.status_code}"}
                )
                continue

            try:
                profile = profile_resp.json()
            except ValueError:
                findings.append({"company": company.company_name, "issue": "profile JSON decode error"})
                continue

            metrics = profile.get("latest_metrics") or {}
            evidence = profile.get("evidence_summary") or []

            prompt = (
                "You are reviewing ESG numbers extracted from a corporate sustainability report. "
                "Below are extracted values and evidence snippets. Identify any value that looks "
                "hallucinated, off by a factor of 10/100/1000, or inconsistent with evidence. "
                "Return strict JSON: "
                '{"company": "...", "concerns": [{"metric": "...", "value": ..., "reason": "..."}]}. '
                "If everything looks plausible, return concerns as an empty list.\n\n"
                f"COMPANY: {company.company_name}\n"
                f"YEAR: {company.report_year}\n"
                f"INDUSTRY: {company.industry_sector} ({company.industry_code})\n\n"
                f"EXTRACTED METRICS:\n{json.dumps(metrics, ensure_ascii=False, indent=2)[:4000]}\n\n"
                f"EVIDENCE SNIPPETS:\n{json.dumps(evidence, ensure_ascii=False, indent=2)[:6000]}"
            )

            try:
                completion = ai_client.chat.completions.create(
                    model=validation_model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0,
                )
                raw = completion.choices[0].message.content or "{}"
                payload = json.loads(raw)
            except Exception as exc:  # noqa: BLE001 - keep script resilient
                findings.append({"company": company.company_name, "issue": f"openai: {exc}"})
                continue

            concerns = []
            for concern in payload.get("concerns") or []:
                if not isinstance(concern, dict):
                    continue
                reason = concern.get("reason")
                if isinstance(reason, str) and "no concern" in reason.lower():
                    continue
                concerns.append(concern)
            if concerns:
                findings.append({"company": company.company_name, "concerns": concerns})
                print(f"  ⚠️ {company.company_name}: {len(concerns)} concern(s)")
            else:
                print(f"  ✅ {company.company_name}: clean")

    write_anomalies_report(findings)


def write_anomalies_report(findings: list[dict]) -> None:
    lines = [
        "# German Demo Seed — AI Cross-Check Report",
        "",
        "Generated by `scripts/seed_german_demo.py --validate`. ",
        "Reviewer: spot-check each flagged item against the source PDF before demo.",
        "",
    ]

    if not findings:
        lines.append("_No anomalies flagged. All extracted records passed the sanity check._")
    else:
        for entry in findings:
            lines.append(f"## {entry.get('company', 'unknown')}")
            lines.append("")
            if "issue" in entry:
                lines.append(f"- ❌ {entry['issue']}")
            for concern in entry.get("concerns", []):
                lines.append(
                    f"- ⚠️ **{concern.get('metric')}**: value=`{concern.get('value')}` "
                    f"— {concern.get('reason')}"
                )
            lines.append("")

    ANOMALIES_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ANOMALIES_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n📝 anomalies report written to {ANOMALIES_REPORT_PATH}")


def reset_seed(api_base: str, companies: list[SeedCompany], *, dry_run: bool) -> None:
    if dry_run:
        print("[dry-run] would reset these seed records:")
        for company in companies:
            print(f"  - {company.company_name} / {company.report_year}")
        return

    print(f"resetting {len(companies)} seed records via DELETE /report/companies/{{name}}/{{year}}?hard=true")
    with httpx.Client(timeout=60) as client:
        for company in companies:
            encoded_name = quote(company.company_name, safe="")
            url = f"{api_base}/report/companies/{encoded_name}/{company.report_year}"
            try:
                response = client.delete(url, params={"hard": "true"})
            except httpx.HTTPError as exc:
                print(f"  ⚠️ {company.company_name} ({company.report_year}): {exc}")
                continue

            if response.status_code in (200, 204, 404):
                print(f"  ✓ {company.company_name} ({company.report_year})")
            else:
                print(
                    f"  ⚠️ {company.company_name} ({company.report_year}): "
                    f"{response.status_code} {response.text[:120]}"
                )

    trigger_recompute(api_base)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--validate", action="store_true", help="run Phase A then Phase B")
    parser.add_argument("--validate-only", action="store_true", help="run Phase B only")
    parser.add_argument("--reset", action="store_true", help="delete all seed rows")
    parser.add_argument("--dry-run", action="store_true", help="no network and no writes")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="request timeout seconds")
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="limit run to slugs or company names (repeatable; accepts comma-separated values)",
    )
    parser.add_argument(
        "--slug",
        action="append",
        default=[],
        help="limit the run to one or more manifest slugs (repeatable)",
    )
    parser.add_argument(
        "--company",
        action="append",
        default=[],
        help="limit the run to one or more exact company names from the manifest (repeatable)",
    )
    args = parser.parse_args(argv)

    if args.validate and args.validate_only:
        print("❌ --validate and --validate-only are mutually exclusive")
        return 2
    if args.only and (args.slug or args.company):
        print("❌ --only cannot be combined with --slug/--company")
        return 2

    try:
        companies = load_manifest()
    except Exception as exc:  # noqa: BLE001 - CLI error surface
        print(f"❌ failed to load manifest: {exc}")
        return 2

    companies = filter_companies(
        companies,
        slugs=args.slug,
        company_names=args.company,
        only_filters=args.only,
    )
    if not companies:
        print("❌ no manifest entries matched the provided filters (--only/--slug/--company)")
        return 2

    print(f"loaded {len(companies)} companies from {MANIFEST_PATH.name}")

    if args.reset:
        reset_seed(args.api_base, companies, dry_run=args.dry_run)
        return 0

    if args.validate_only:
        phase_b(args.api_base, companies)
        return 0

    summary = phase_a(args.api_base, companies, dry_run=args.dry_run, timeout=args.timeout)

    if args.validate and not args.dry_run:
        phase_b(args.api_base, companies)

    return 0 if not summary["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())

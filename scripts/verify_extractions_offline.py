"""Deterministic, LLM-free verification of extracted ESG metrics against source PDFs.

For every company report with a stored PDF, each extracted metric value is
rendered into the number formats that appear in real reports (English/German
thousands separators, decimal comma, unit scalings like kt/Mt or GWh/TWh) and
searched in the PDF text. Pages are classified by metric keywords so a match
near the right context ranks higher than a match elsewhere.

Verdicts per (company, year, field):
  verified         value found on a page that also matches the field keywords
  found_elsewhere  value found, but only on pages without field keywords
  not_found        non-null value not found in any candidate format
  not_extracted    DB value is NULL (potential_miss=True if keyword pages exist)

Usage:
  python scripts/verify_extractions_offline.py                 # all reports
  python scripts/verify_extractions_offline.py --company "PUMA SE"
  python scripts/verify_extractions_offline.py --json out.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import SessionLocal  # noqa: E402
from report_parser.storage import CompanyReport  # noqa: E402
from scripts.extraction_qa_audit import (  # noqa: E402
    METRIC_KEYWORDS,
    extract_pdf_pages,
)

REPORTS_DIR = ROOT / "data" / "reports"

# fields whose values are large absolute quantities that reports often scale
SCALED_FIELDS = {
    "scope1_co2e_tonnes": [1, 1_000, 1_000_000],        # t, kt, Mt
    "scope2_co2e_tonnes": [1, 1_000, 1_000_000],
    "scope3_co2e_tonnes": [1, 1_000, 1_000_000],
    "energy_consumption_mwh": [1, 1_000, 1_000_000],    # MWh, GWh, TWh
    "water_usage_m3": [1, 1_000, 1_000_000],
    "total_revenue_eur": [1, 1_000_000, 1_000_000_000],  # EUR, mEUR, bnEUR
    "total_capex_eur": [1, 1_000_000, 1_000_000_000],
}

PCT_FIELDS = {
    "renewable_energy_pct",
    "waste_recycled_pct",
    "taxonomy_aligned_revenue_pct",
    "taxonomy_aligned_capex_pct",
    "female_pct",
}

EXPLICIT_NUMERIC_FIELDS = {
    "total_employees",
}

VERIFIABLE_FIELDS = sorted(set(METRIC_KEYWORDS) | set(SCALED_FIELDS) | PCT_FIELDS | EXPLICIT_NUMERIC_FIELDS)


def _number_variants(value: float, field: str) -> set[str]:
    """Render value into the formats corporate reports actually print."""
    variants: set[str] = set()

    def render(v: float) -> None:
        if v < 0:
            return
        forms = []
        if abs(v - round(v)) < 1e-9:
            iv = int(round(v))
            forms += [f"{iv:,}", str(iv)]
        for dec in (1, 2):
            if v < 10_000:  # decimals only plausible for smaller magnitudes
                forms.append(f"{v:,.{dec}f}")
        for f in forms:
            variants.add(f)                                   # 1,234,567.8
            variants.add(f.replace(",", "X").replace(".", ",").replace("X", "."))  # 1.234.567,8

    if field in SCALED_FIELDS:
        for scale in SCALED_FIELDS[field]:
            render(value / scale)
    elif field in PCT_FIELDS:
        for dec in (0, 1, 2):
            s = f"{value:.{dec}f}"
            variants.add(s)
            variants.add(s.replace(".", ","))
    else:
        render(value)

    # drop trivially short strings that would match everywhere
    return {v for v in variants if len(v.replace(",", "").replace(".", "")) >= 2}


def _normalize(text: str) -> str:
    # unify narrow/thin/nbsp spaces that PDFs use inside numbers
    for ch in (" ", " ", " ", " "):
        text = text.replace(ch, "")
    return text


def verify_record(record: CompanyReport, pages: list[str]) -> list[dict]:
    norm_pages = [_normalize(p) for p in pages]
    lower_pages = [p.lower() for p in norm_pages]
    results = []

    for field in VERIFIABLE_FIELDS:
        keywords = METRIC_KEYWORDS.get(field, field.split("_"))
        value = getattr(record, field, None)
        keyword_pages = [
            i for i, p in enumerate(lower_pages, start=1)
            if sum(p.count(kw.lower()) for kw in keywords) >= 2
        ]

        if value is None:
            results.append({
                "company": record.company_name,
                "year": record.report_year,
                "field": field,
                "value": None,
                "verdict": "not_extracted",
                "potential_miss": bool(keyword_pages),
                "pages": keyword_pages[:3],
            })
            continue

        variants = _number_variants(float(value), field)
        hit_pages = [
            i for i, p in enumerate(norm_pages, start=1)
            if any(v in p for v in variants)
        ]
        on_keyword_page = sorted(set(hit_pages) & set(keyword_pages))

        if on_keyword_page:
            verdict = "verified"
        elif hit_pages:
            verdict = "found_elsewhere"
        else:
            verdict = "not_found"

        results.append({
            "company": record.company_name,
            "year": record.report_year,
            "field": field,
            "value": value,
            "verdict": verdict,
            "pages": (on_keyword_page or hit_pages)[:3],
        })

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--company", help="verify a single company")
    parser.add_argument("--json", help="write full results to this JSON file")
    args = parser.parse_args()

    db = SessionLocal()
    query = (
        db.query(CompanyReport)
        .filter(CompanyReport.pdf_filename.isnot(None))
        .order_by(CompanyReport.company_name.asc(), CompanyReport.report_year.desc())
    )
    if args.company:
        query = query.filter(CompanyReport.company_name == args.company)
    records = query.all()

    all_results: list[dict] = []
    skipped: list[str] = []

    for record in records:
        pdf_path = REPORTS_DIR / record.pdf_filename
        if not pdf_path.exists():
            skipped.append(f"{record.company_name} {record.report_year}: PDF missing")
            continue
        ctx = extract_pdf_pages(pdf_path)
        if not ctx or ctx.total_chars < 100:
            skipped.append(f"{record.company_name} {record.report_year}: PDF unreadable")
            continue
        rows = verify_record(record, ctx.pages)
        all_results.extend(rows)
        verified = sum(1 for r in rows if r["verdict"] == "verified")
        nonnull = sum(1 for r in rows if r["value"] is not None)
        print(f"[{record.company_name} {record.report_year}] "
              f"{verified}/{nonnull} non-null values verified on keyword pages")

    db.close()

    # aggregate
    counts: dict[str, int] = {}
    for r in all_results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    nonnull_total = sum(counts.get(k, 0) for k in ("verified", "found_elsewhere", "not_found"))
    misses = sum(1 for r in all_results if r["verdict"] == "not_extracted" and r["potential_miss"])

    print("\n=== Aggregate ===")
    for verdict in ("verified", "found_elsewhere", "not_found", "not_extracted"):
        print(f"  {verdict}: {counts.get(verdict, 0)}")
    if nonnull_total:
        rate = (counts.get("verified", 0) + counts.get("found_elsewhere", 0)) / nonnull_total
        print(f"  non-null values traceable to source PDF: {rate:.1%}")
    print(f"  not_extracted with keyword pages present (potential misses): {misses}")
    if skipped:
        print("\nSkipped:")
        for s in skipped:
            print(f"  - {s}")

    if args.json:
        Path(args.json).write_text(json.dumps(all_results, indent=1))
        print(f"\nFull results written to {args.json}")

    return 0


if __name__ == "__main__":
    main()

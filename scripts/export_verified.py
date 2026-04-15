#!/usr/bin/env python3
"""Export verified company_reports rows for VPS sync.

Output: data/exports/<YYYY-MM-DD-HHMMSS>/ containing
    - company_reports.jsonl    one row per record (deletion_requested=False)
    - industry_benchmarks.jsonl one row per cached benchmark metric
    - manifest.json            sha256 of every file + row counts + audit pointer
    - README.txt               1-line description for the receiver

Design rules:
- Only verified rows leave local. Anything with deletion_requested=True is excluded.
- L0 validation is run again on every row; rows with validation errors are SKIPPED
  (not silently exported) and listed in manifest.json.skipped[].
- PDF binaries are NEVER included. Only the file_hash + source_url.
  The VPS will lazy-fetch the PDF from source_url when first profile request hits.
- Output is gzip-friendly JSONL so import_verified.py on the VPS can stream it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running as a script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import SessionLocal  # noqa: E402
from core.validation import has_errors, validate_record  # noqa: E402
from report_parser.storage import CompanyReport  # noqa: E402

try:
    from benchmark.models import IndustryBenchmark  # noqa: E402
except Exception:  # pragma: no cover - optional, depends on benchmark module shape
    try:
        from benchmark.storage import IndustryBenchmark  # noqa: E402
    except Exception:
        IndustryBenchmark = None  # type: ignore[assignment,misc]


METRIC_FIELDS = [
    "scope1_co2e_tonnes",
    "scope2_co2e_tonnes",
    "scope3_co2e_tonnes",
    "energy_consumption_mwh",
    "renewable_energy_pct",
    "water_usage_m3",
    "waste_recycled_pct",
    "total_revenue_eur",
    "taxonomy_aligned_revenue_pct",
    "total_capex_eur",
    "taxonomy_aligned_capex_pct",
    "total_employees",
    "female_pct",
]


def _row_to_dict(row: CompanyReport) -> dict:
    out: dict = {
        "company_name": row.company_name,
        "report_year": row.report_year,
        "reporting_period_label": row.reporting_period_label,
        "reporting_period_type": row.reporting_period_type,
        "source_document_type": row.source_document_type,
        "industry_code": row.industry_code,
        "industry_sector": row.industry_sector,
        "pdf_filename": row.pdf_filename,
        "source_url": row.source_url,
        "file_hash": row.file_hash,
    }
    for field in METRIC_FIELDS:
        out[field] = getattr(row, field)
    return out


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def export(out_root: Path) -> dict:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    out_dir = out_root / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    exported: list[dict] = []
    skipped: list[dict] = []
    bench_rows: list[dict] = []

    with SessionLocal() as db:
        rows = (
            db.query(CompanyReport)
            .filter(CompanyReport.deletion_requested.is_(False))
            .order_by(CompanyReport.company_name.asc(), CompanyReport.report_year.asc())
            .all()
        )
        for row in rows:
            payload = _row_to_dict(row)
            issues = validate_record(payload)
            if has_errors(issues):
                skipped.append(
                    {
                        "company_name": row.company_name,
                        "report_year": row.report_year,
                        "errors": [i.to_dict() for i in issues if i.severity == "error"],
                    }
                )
                continue
            exported.append(payload)

        if IndustryBenchmark is not None:
            for row in db.query(IndustryBenchmark).all():
                bench_rows.append(
                    {
                        column.name: getattr(row, column.name)
                        for column in row.__table__.columns
                    }
                )

    company_path = out_dir / "company_reports.jsonl"
    with company_path.open("w", encoding="utf-8") as fh:
        for record in exported:
            fh.write(json.dumps(record, default=str) + "\n")

    bench_path = out_dir / "industry_benchmarks.jsonl"
    with bench_path.open("w", encoding="utf-8") as fh:
        for record in bench_rows:
            fh.write(json.dumps(record, default=str) + "\n")

    manifest = {
        "exported_at": timestamp,
        "exported_count": len(exported),
        "skipped_count": len(skipped),
        "benchmark_rows": len(bench_rows),
        "files": {
            "company_reports.jsonl": {
                "sha256": _sha256(company_path),
                "bytes": company_path.stat().st_size,
            },
            "industry_benchmarks.jsonl": {
                "sha256": _sha256(bench_path),
                "bytes": bench_path.stat().st_size,
            },
        },
        "skipped": skipped,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str), encoding="utf-8"
    )
    (out_dir / "README.txt").write_text(
        "ESG verified export — feed both .jsonl files into scripts/import_verified.py on the VPS, "
        "then POST /benchmarks/recompute. PDFs are NOT included; receiver fetches them lazily from source_url.\n",
        encoding="utf-8",
    )

    return {"out_dir": str(out_dir), **manifest}


def main() -> int:
    parser = argparse.ArgumentParser(description="Export verified rows for VPS sync")
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data" / "exports",
        help="Output root (default: data/exports)",
    )
    args = parser.parse_args()

    summary = export(args.out)
    print(json.dumps(summary, indent=2, default=str))
    if summary["exported_count"] == 0:
        print("WARN: 0 rows exported", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Import a verified export bundle on the VPS side.

Reads <export_dir>/{company_reports.jsonl, industry_benchmarks.jsonl, manifest.json},
verifies file hashes, then upserts into the local DB.

Idempotent: re-running the same bundle is a no-op.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import SessionLocal  # noqa: E402
from report_parser.storage import CompanyReport  # noqa: E402


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify(export_dir: Path) -> dict:
    manifest = json.loads((export_dir / "manifest.json").read_text("utf-8"))
    for fname, meta in manifest["files"].items():
        actual = _sha256(export_dir / fname)
        if actual != meta["sha256"]:
            raise RuntimeError(f"sha256 mismatch on {fname}: got {actual} expected {meta['sha256']}")
    return manifest


def _import_companies(export_dir: Path) -> tuple[int, int]:
    inserted = 0
    updated = 0
    with SessionLocal() as db:
        with (export_dir / "company_reports.jsonl").open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                company = payload["company_name"]
                year = payload["report_year"]
                file_hash = payload.get("file_hash")
                source_url = payload.get("source_url")

                # Match by (company, year, file_hash) primarily; fall back to (company, year, source_url)
                q = db.query(CompanyReport).filter(
                    CompanyReport.company_name == company,
                    CompanyReport.report_year == year,
                )
                row = None
                if file_hash:
                    row = q.filter(CompanyReport.file_hash == file_hash).first()
                if row is None and source_url:
                    row = q.filter(CompanyReport.source_url == source_url).first()
                if row is None:
                    row = CompanyReport(
                        company_name=company,
                        report_year=year,
                        downloaded_at=datetime.now(timezone.utc),
                    )
                    db.add(row)
                    inserted += 1
                else:
                    updated += 1

                for key, value in payload.items():
                    if key in ("company_name", "report_year"):
                        continue
                    if hasattr(row, key):
                        setattr(row, key, value)

        db.commit()
    return inserted, updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Import verified export bundle into local DB")
    parser.add_argument("export_dir", type=Path)
    args = parser.parse_args()

    if not args.export_dir.is_dir():
        print(f"ERROR: not a directory: {args.export_dir}", file=sys.stderr)
        return 1

    manifest = _verify(args.export_dir)
    print(f"manifest verified — {manifest['exported_count']} rows in bundle")

    inserted, updated = _import_companies(args.export_dir)
    print(json.dumps({"inserted": inserted, "updated": updated}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

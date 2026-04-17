from __future__ import annotations

import argparse
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from sqlalchemy import func

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import SessionLocal
from report_parser.company_identity import report_quality_score
from report_parser.storage import CompanyReport


RENAMES: tuple[tuple[str, str], ...] = (
    ("BMW Group", "BMW AG"),
    ("Deutsche Telekom", "Deutsche Telekom AG"),
    ("Fresenius", "Fresenius SE & Co. KGaA"),
    ("Linde", "Linde plc"),
    ("PUMA", "PUMA SE"),
    ("RWE", "RWE AG"),
    ("SAP", "SAP SE"),
    ("Volkswagen Group", "Volkswagen AG"),
    ("thyssenkrupp", "thyssenkrupp AG"),
)


def _db_path() -> Path:
    return Path("data/esg_toolkit.db")


def _projected_groups(session, renames: tuple[tuple[str, str], ...]) -> dict[tuple[str, int], list[CompanyReport]]:
    rename_map = {source: target for source, target in renames}
    all_rows = session.query(CompanyReport).all()
    projected: dict[tuple[str, int], list[CompanyReport]] = defaultdict(list)
    for row in all_rows:
        projected_name = rename_map.get(row.company_name, row.company_name)
        projected[(projected_name, row.report_year)].append(row)
    return projected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migrate legacy company names to canonical names.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="execute UPDATEs (default is dry-run preview only)",
    )
    args = parser.parse_args(argv)

    db_path = _db_path()
    if not db_path.exists():
        print(f"❌ database not found: {db_path}")
        return 2

    with SessionLocal() as session:
        affected_total = 0
        print("=== Canonical company-name migration preview ===")
        for source_name, target_name in RENAMES:
            affected = (
                session.query(CompanyReport)
                .filter(CompanyReport.company_name == source_name)
                .count()
            )
            affected_total += affected
            print(f"{source_name} -> {target_name}: {affected} row(s)")

        projected_groups = _projected_groups(session, RENAMES)
        duplicates = [
            (company_name, report_year, rows)
            for (company_name, report_year), rows in sorted(projected_groups.items())
            if len(rows) > 1
        ]
        if duplicates:
            print("\nProjected duplicate groups after rename (will be auto-deduped by quality score):")
            for company_name, report_year, rows in duplicates:
                best = max(rows, key=report_quality_score)
                losers = [row.id for row in rows if row.id != best.id]
                print(
                    f"  - {company_name} / {report_year}: keep id={best.id}, "
                    f"delete ids={losers}"
                )

        print(f"\nTotal affected rows: {affected_total}")
        if not args.apply:
            print("Dry run only. Re-run with --apply to execute.")
            return 0

    backup_path = db_path.with_suffix(f".db.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(db_path, backup_path)
    print(f"Backup written: {backup_path}")

    with SessionLocal() as session:
        for source_name, target_name in RENAMES:
            rows = (
                session.query(CompanyReport)
                .filter(CompanyReport.company_name == source_name)
                .all()
            )
            for row in rows:
                row.company_name = target_name

        projected_groups = _projected_groups(session, RENAMES)
        deleted_ids: list[int] = []
        for (_company_name, _report_year), rows in projected_groups.items():
            if len(rows) < 2:
                continue
            best = max(rows, key=report_quality_score)
            for row in rows:
                if row.id == best.id:
                    continue
                session.delete(row)
                deleted_ids.append(row.id)

        session.commit()

        remaining_legacy = (
            session.query(CompanyReport.company_name, func.count(CompanyReport.id))
            .filter(CompanyReport.company_name.in_([source for source, _ in RENAMES]))
            .group_by(CompanyReport.company_name)
            .all()
        )

    if remaining_legacy:
        print("\n❌ migration incomplete; legacy names still present:")
        for company_name, count in remaining_legacy:
            print(f"  - {company_name}: {count}")
        return 1

    if deleted_ids:
        print(f"\nDeduped duplicate rows by quality score; deleted ids: {deleted_ids}")
    print("\n✅ canonical company-name migration applied successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

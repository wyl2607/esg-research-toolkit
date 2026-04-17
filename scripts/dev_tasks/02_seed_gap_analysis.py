#!/usr/bin/env python3
"""Cross-check the seed manifest against what's actually loaded in the DB.

For each (company_name, report_year) in the manifest, check whether the DB has
a corresponding AnalysisResult row. Output a gap report that:
  - Lists every manifest entry missing from the DB
  - For each manifest company that's missing 2022-2023 data, suggests URL
    patterns to hunt down (derived from the 2024 URL template)
  - Lists companies in the DB that have no manifest entry (possible drift)

Output: docs/dev-tasks/02_seed_gap_analysis.md
This script is READ-ONLY.

Usage:
  OPENAI_API_KEY=dummy .venv/bin/python scripts/dev_tasks/02_seed_gap_analysis.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.config import settings
from report_parser.storage import CompanyReport


MANIFEST_PATH = PROJECT_ROOT / "scripts" / "seed_data" / "german_demo_manifest.json"
REPORT_PATH = PROJECT_ROOT / "docs" / "dev-tasks" / "02_seed_gap_analysis.md"
TARGET_YEARS = [2022, 2023, 2024]


def derive_prior_year_url_pattern(url_2024: str, year: int) -> list[str]:
    """Given a 2024 URL, suggest plausible prior-year variants."""
    candidates: list[str] = []
    # Replace obvious year tokens
    for pattern in [str(2024), "24", "2024-report", "FY24"]:
        if pattern in url_2024:
            replacement_map = {
                str(2024): str(year),
                "24": str(year)[-2:],
                "2024-report": f"{year}-report",
                "FY24": f"FY{str(year)[-2:]}",
            }
            candidates.append(url_2024.replace(pattern, replacement_map[pattern]))
    return list(dict.fromkeys(candidates))  # dedupe, preserve order


def main() -> int:
    # Load manifest
    with MANIFEST_PATH.open() as f:
        raw = json.load(f)

    # Manifest is either a bare list or {"_comment": ..., "companies": [...]}
    manifest = raw["companies"] if isinstance(raw, dict) else raw

    manifest_entries: dict[tuple[str, int], dict] = {
        (entry["company_name"], entry["report_year"]): entry
        for entry in manifest
    }
    manifest_companies = {entry["company_name"] for entry in manifest}

    # Load DB state
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    db_rows = session.query(
        CompanyReport.company_name,
        CompanyReport.report_year,
    ).all()
    db_pairs: set[tuple[str, int]] = {(r.company_name, r.report_year) for r in db_rows}
    db_companies_by_year: dict[int, set[str]] = defaultdict(set)
    for name, year in db_pairs:
        db_companies_by_year[year].add(name)

    # Classify
    in_manifest_not_in_db: list[dict] = []
    in_db_not_in_manifest: list[tuple[str, int]] = []

    for (company, year), entry in manifest_entries.items():
        if (company, year) not in db_pairs:
            in_manifest_not_in_db.append(entry)

    for company, year in sorted(db_pairs):
        if (company, year) not in manifest_entries:
            in_db_not_in_manifest.append((company, year))

    # Build multi-year coverage map from manifest
    manifest_years_by_company: dict[str, set[int]] = defaultdict(set)
    for entry in manifest:
        manifest_years_by_company[entry["company_name"]].add(entry["report_year"])

    # Identify companies that have 2024 in manifest but are missing 2022 or 2023
    missing_prior_years: list[tuple[str, list[int], dict]] = []
    for company, years in manifest_years_by_company.items():
        if 2024 not in years:
            continue
        missing = [y for y in [2022, 2023] if y not in years]
        if missing:
            # Find the 2024 entry so we can derive URL patterns
            entry_2024 = next(
                (e for e in manifest if e["company_name"] == company and e["report_year"] == 2024),
                None,
            )
            if entry_2024:
                missing_prior_years.append((company, missing, entry_2024))

    # Write report
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as f:
        f.write("# Seed Pipeline Gap Analysis\n\n")
        f.write(f"**Manifest**: `{MANIFEST_PATH.relative_to(PROJECT_ROOT)}` ({len(manifest)} entries)\n")
        f.write(f"**DB**: `{settings.database_url}` ({len(db_pairs)} (company, year) pairs)\n\n")

        f.write("## 1. Manifest Coverage Matrix\n\n")
        f.write("| Company | 2022 | 2023 | 2024 |\n")
        f.write("|---|:-:|:-:|:-:|\n")
        for company in sorted(manifest_years_by_company.keys()):
            years = manifest_years_by_company[company]
            cells = [
                "✅" if 2022 in years else "—",
                "✅" if 2023 in years else "—",
                "✅" if 2024 in years else "—",
            ]
            f.write(f"| `{company}` | {cells[0]} | {cells[1]} | {cells[2]} |\n")
        f.write("\n")

        f.write("## 2. In Manifest but NOT in DB\n\n")
        if in_manifest_not_in_db:
            f.write(f"**{len(in_manifest_not_in_db)} entries need to be seeded:**\n\n")
            for entry in in_manifest_not_in_db:
                f.write(f"- `{entry['slug']}` — `{entry['company_name']}` / {entry['report_year']}\n")
            f.write("\n**Action**: re-run seed pipeline, e.g.\n")
            f.write("```bash\n")
            slugs = [e["slug"] for e in in_manifest_not_in_db[:5]]
            f.write(".venv/bin/python scripts/seed_german_demo.py \\\n")
            for slug in slugs:
                f.write(f"  --only {slug} \\\n")
            f.write("  --validate\n```\n")
        else:
            f.write("_All manifest entries are loaded._ 🎉\n")
        f.write("\n")

        f.write("## 3. In DB but NOT in Manifest (possible drift)\n\n")
        if in_db_not_in_manifest:
            f.write(f"**{len(in_db_not_in_manifest)} entries:**\n\n")
            for company, year in in_db_not_in_manifest:
                f.write(f"- `{company}` / {year}\n")
            f.write("\n**Action**: decide whether these should be added to the manifest or deleted from the DB.\n")
        else:
            f.write("_All DB rows have a matching manifest entry._ 🎉\n")
        f.write("\n")

        f.write("## 4. Companies Missing 2022/2023 (high-impact gaps)\n\n")
        if missing_prior_years:
            f.write("These companies have 2024 data but are missing historical years. ")
            f.write("Filling these would immediately unlock more multi-year trend charts.\n\n")
            for company, missing, entry_2024 in missing_prior_years:
                f.write(f"### `{company}`\n\n")
                f.write(f"- Missing: {missing}\n")
                f.write(f"- 2024 URL: `{entry_2024['source_url']}`\n")
                f.write(f"- Industry: `{entry_2024.get('industry_code', '?')}` / `{entry_2024.get('industry_sector', '?')}`\n\n")
                f.write("**Candidate URLs to verify (HTTP 200 + PDF magic)**:\n\n")
                for year in missing:
                    candidates = derive_prior_year_url_pattern(entry_2024["source_url"], year)
                    if candidates:
                        for url in candidates:
                            f.write(f"- {year}: `{url}`\n")
                    else:
                        f.write(f"- {year}: _no obvious URL pattern_ — search IR site manually\n")
                f.write("\n")
        else:
            f.write("_All companies with 2024 data also have 2022 + 2023._ 🎉\n")
        f.write("\n")

        f.write("## Next Steps\n\n")
        f.write("1. Add discovered URLs to `scripts/seed_data/german_demo_manifest.json`.\n")
        f.write("2. Verify each candidate URL returns HTTP 200 and starts with `%PDF` magic bytes.\n")
        f.write("3. Re-run the seed pipeline for new entries:\n")
        f.write("   `python scripts/seed_german_demo.py --slug <new-slug> --validate`\n")
        f.write("4. Re-run this audit to confirm gaps are closed.\n")

    print(f"Report written: {REPORT_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Manifest entries: {len(manifest)}")
    print(f"DB (company, year) pairs: {len(db_pairs)}")
    print(f"Missing from DB: {len(in_manifest_not_in_db)}")
    print(f"In DB but not in manifest: {len(in_db_not_in_manifest)}")
    print(f"Companies needing 2022/2023: {len(missing_prior_years)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

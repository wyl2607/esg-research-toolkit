#!/usr/bin/env python3
"""Generate a complete identity-merge migration plan.

Root cause confirmed by Script 01 + 02:
  - seed_german_demo.py calls POST /report/upload, which lets the AI extractor
    decide the final company_name. The manifest's curated company_name is
    never used to override the extracted value.
  - Result: the same legal entity is stored under 2+ names
    (e.g., "Volkswagen AG" vs "Volkswagen Group", "SAP" vs "SAP SE"), which
    splits multi-year trend data.

This script is READ-ONLY. It produces:
  1. A precise UPDATE SQL preview (row counts per rename)
  2. A proposed patch to `_KNOWN_CANONICAL_NAMES` (alias additions)
  3. A proposed long-term fix for `scripts/seed_german_demo.py`
     (manifest name should override extractor output)
  4. Verification commands to run AFTER the fix lands

Output: docs/dev-tasks/04_identity_migration_plan.md

Usage:
  OPENAI_API_KEY=dummy .venv/bin/python scripts/dev_tasks/04_identity_migration_plan.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from core.config import settings
from report_parser.storage import CompanyReport
from report_parser.company_identity import canonical_company_name, _KNOWN_CANONICAL_NAMES, _normalize_key


MANIFEST_PATH = PROJECT_ROOT / "scripts" / "seed_data" / "german_demo_manifest.json"
REPORT_PATH = PROJECT_ROOT / "docs" / "dev-tasks" / "04_identity_migration_plan.md"

# Manual canonical choices (for clusters where auto-pick is ambiguous).
# These reflect the manifest's intended canonical name. Every normalized key
# that might appear in the DB as an extractor variant should map to the
# canonical the manifest agreed on.
MANUAL_CANONICAL: dict[str, str] = {
    # Linde
    "linde": "Linde plc",
    "linde plc": "Linde plc",
    # PUMA
    "puma": "PUMA SE",
    "puma se": "PUMA SE",
    # RWE
    "rwe": "RWE AG",
    "rwe ag": "RWE AG",
    # SAP
    "sap": "SAP SE",
    "sap se": "SAP SE",
    # Volkswagen — extractor may emit "Volkswagen Group" from English PDFs
    "volkswagen": "Volkswagen AG",
    "volkswagen ag": "Volkswagen AG",
    "volkswagen group": "Volkswagen AG",
    "volkswagen aktiengesellschaft": "Volkswagen AG",
    # BMW
    "bmw": "BMW AG",
    "bmw ag": "BMW AG",
    "bmw group": "BMW AG",
    # Deutsche Telekom
    "deutsche telekom": "Deutsche Telekom AG",
    "deutsche telekom ag": "Deutsche Telekom AG",
    # DHL
    "dhl": "DHL Group",
    "dhl group": "DHL Group",
    "deutsche post dhl": "DHL Group",
    "deutsche post dhl group": "DHL Group",
    # Henkel
    "henkel": "Henkel AG & Co. KGaA",
    "henkel ag co kgaa": "Henkel AG & Co. KGaA",
    # Fresenius
    "fresenius": "Fresenius SE & Co. KGaA",
    "fresenius se co kgaa": "Fresenius SE & Co. KGaA",
    # thyssenkrupp
    "thyssenkrupp": "thyssenkrupp AG",
    "thyssenkrupp ag": "thyssenkrupp AG",
}


def build_manifest_name_map() -> dict[str, str]:
    """Return {normalized_short_name: manifest_full_name} from the manifest."""
    with MANIFEST_PATH.open() as f:
        raw = json.load(f)
    entries = raw["companies"] if isinstance(raw, dict) else raw

    result: dict[str, str] = {}
    for entry in entries:
        canonical = entry["company_name"]
        # Strip common suffixes to get the lookup key
        short = canonical
        for suffix in [" SE & Co. KGaA", " AG & Co. KGaA", " AG", " SE", " plc", " Group", ", Darmstadt, Germany"]:
            if short.endswith(suffix):
                short = short[: -len(suffix)]
        short_key = _normalize_key(short)
        if short_key and short_key != _normalize_key(canonical):
            result[short_key] = canonical
        result[_normalize_key(canonical)] = canonical
    return result


def main() -> int:
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    rows = (
        session.query(
            CompanyReport.company_name,
            func.count(CompanyReport.id).label("n_reports"),
        )
        .group_by(CompanyReport.company_name)
        .all()
    )

    manifest_name_map = build_manifest_name_map()

    # Classify every DB name:
    #   A) already equals canonical → no action
    #   B) collapses via existing alias → needs DB rename only
    #   C) should collapse to a manifest name but no alias exists → needs alias + rename
    db_rename_plan: list[tuple[str, str, int]] = []  # (from, to, row_count)
    new_alias_proposals: list[tuple[str, str]] = []   # (normalized_key, canonical)
    untouched: list[tuple[str, int]] = []

    for name, count in rows:
        current_canonical = canonical_company_name(name)
        normalized = _normalize_key(name)
        # Prefer manifest's curated name
        manifest_choice = manifest_name_map.get(normalized)
        manual_choice = MANUAL_CANONICAL.get(normalized)
        target = manifest_choice or manual_choice or current_canonical

        if target == name:
            untouched.append((name, count))
            continue

        db_rename_plan.append((name, target, count))

        # Do we need to also add an alias?
        target_key = _normalize_key(target)
        if normalized not in _KNOWN_CANONICAL_NAMES or _KNOWN_CANONICAL_NAMES[normalized] != target:
            new_alias_proposals.append((normalized, target))

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as f:
        f.write("# Identity Migration Plan\n\n")
        f.write(f"**DB**: `{settings.database_url}`\n")
        f.write(f"**Manifest**: `{MANIFEST_PATH.relative_to(PROJECT_ROOT)}`\n")
        f.write(f"**Renames needed**: {len(db_rename_plan)}\n")
        f.write(f"**New alias entries needed**: {len(new_alias_proposals)}\n")
        f.write(f"**Untouched (already canonical)**: {len(untouched)}\n\n")

        # ── Section 1: Root cause ────────────────────────────────────────────
        f.write("## 1. Root Cause\n\n")
        f.write("`scripts/seed_german_demo.py::upload_company()` POSTs the PDF to ")
        f.write("`/report/upload` and uses whatever `company_name` the AI extractor returns. ")
        f.write("The manifest's curated `company_name` is never used to override this. ")
        f.write("The extractor produces slightly different names per PDF vintage, so the ")
        f.write("same legal entity ends up split across multiple DB rows.\n\n")
        f.write("**Proof** (from Script 01):\n\n")
        f.write("```\nRWE: 2 reports (2024×2)\nRWE AG: 3 reports (2022,2023,2024)\n")
        f.write("SAP: 2 reports (2022,2023)\nSAP SE: 1 report (2024)\n")
        f.write("Volkswagen AG: 2 reports (2024×2)\nVolkswagen Group: 2 reports (2022,2023)\n```\n\n")

        # ── Section 2: UPDATE SQL preview ────────────────────────────────────
        f.write("## 2. DB Rename Preview (READ-ONLY — not executed)\n\n")
        if not db_rename_plan:
            f.write("_No renames needed._\n\n")
        else:
            f.write("```sql\n")
            f.write("BEGIN TRANSACTION;\n\n")
            total_rows = 0
            for from_name, to_name, count in sorted(db_rename_plan, key=lambda r: -r[2]):
                f.write(f"-- Merge {count} row(s)\n")
                f.write("UPDATE company_reports\n")
                f.write(f"   SET company_name = '{to_name.replace(chr(39), chr(39)*2)}'\n")
                f.write(f" WHERE company_name = '{from_name.replace(chr(39), chr(39)*2)}';\n\n")
                total_rows += count
            f.write("-- Verify no duplicate (company_name, report_year) after merge\n")
            f.write("SELECT company_name, report_year, COUNT(*) AS n\n")
            f.write("  FROM company_reports\n")
            f.write(" GROUP BY company_name, report_year\n")
            f.write(" HAVING n > 1;\n\n")
            f.write("-- If the check above returns rows, ROLLBACK; otherwise COMMIT.\n")
            f.write("COMMIT;\n")
            f.write("```\n\n")
            f.write(f"**Total affected rows**: {total_rows}\n\n")

        # ── Section 3: Alias additions ───────────────────────────────────────
        f.write("## 3. Proposed `_KNOWN_CANONICAL_NAMES` Additions\n\n")
        if not new_alias_proposals:
            f.write("_No new aliases needed._\n\n")
        else:
            f.write("Add these entries to `report_parser/company_identity.py` so that any future ")
            f.write("extraction producing the short form auto-canonicalizes:\n\n")
            f.write("```python\n")
            # Deduplicate by (normalized, target)
            seen_pairs: set[tuple[str, str]] = set()
            for normalized, target in new_alias_proposals:
                if (normalized, target) in seen_pairs:
                    continue
                seen_pairs.add((normalized, target))
                f.write(f'    "{normalized}": "{target}",\n')
                # Also add the canonical itself self-mapping for idempotency
                target_key = _normalize_key(target)
                if target_key != normalized and (target_key, target) not in seen_pairs:
                    seen_pairs.add((target_key, target))
                    f.write(f'    "{target_key}": "{target}",\n')
            f.write("```\n\n")

        # ── Section 4: Long-term seed fix ────────────────────────────────────
        f.write("## 4. Long-term Fix — Prevent Future Splits\n\n")
        f.write("Patch `scripts/seed_german_demo.py::upload_company()` to force the manifest's ")
        f.write("curated `company_name` as the final identity:\n\n")
        f.write("```python\n")
        f.write("# After upload_company() returns, reconcile the name before\n")
        f.write("# downstream storage / history uses kick in.\n")
        f.write("#\n")
        f.write("# Option A (preferred): pass override to /report/upload via a new\n")
        f.write("#   optional form field `override_company_name`. Backend path uses\n")
        f.write("#   it verbatim, ignoring the AI extraction.\n")
        f.write("#\n")
        f.write("# Option B (quick fix, no backend change): after upload success,\n")
        f.write("#   issue a direct UPDATE on company_reports where id = new_id,\n")
        f.write("#   setting company_name = company.company_name.\n")
        f.write("```\n\n")

        # ── Section 5: Verification ──────────────────────────────────────────
        f.write("## 5. Verification (run AFTER migration)\n\n")
        f.write("```bash\n")
        f.write("# 1. Re-run identity audit — should report 0 clusters\n")
        f.write("OPENAI_API_KEY=dummy .venv/bin/python scripts/dev_tasks/01_company_identity_audit.py\n\n")
        f.write("# 2. Re-run seed gap analysis — 'In DB but NOT in manifest' should drop to 0\n")
        f.write("OPENAI_API_KEY=dummy .venv/bin/python scripts/dev_tasks/02_seed_gap_analysis.py\n\n")
        f.write("# 3. Full pytest — must stay at 127 passed\n")
        f.write("OPENAI_API_KEY=dummy .venv/bin/pytest -q tests/\n\n")
        f.write("# 4. Spot-check multi-year trend for VW (should now show 3 points)\n")
        f.write("curl -s 'http://localhost:8000/report/companies/Volkswagen%20AG/history' | \\\n")
        f.write("  jq '.trend | length, .periods | length'\n")
        f.write("```\n\n")
        f.write("Expected after success:\n")
        f.write("- VW, SAP, RWE each show 3 trend points (2022/2023/2024)\n")
        f.write("- identity audit reports 0 clusters\n")
        f.write("- seed gap drift count is 0\n\n")

        # ── Section 6: Execution order ───────────────────────────────────────
        f.write("## 6. Recommended Execution Order\n\n")
        f.write("1. **Review this plan** with Claude — especially the canonical choices in §2.\n")
        f.write("2. **Create a DB backup**: `cp data/esg_toolkit.db data/esg_toolkit.db.pre-merge-$(date +%Y%m%d)`\n")
        f.write("3. **Apply alias additions** (§3) via an `Edit` on `company_identity.py`.\n")
        f.write("4. **Apply UPDATE SQL** (§2) inside a transaction — commit only if the dedup check returns 0 rows.\n")
        f.write("5. **Patch seed script** (§4 Option A or B) to prevent regression.\n")
        f.write("6. **Re-run verification** (§5).\n")
        f.write("7. **Add a pytest regression** asserting `canonical_company_name('Volkswagen Group') == 'Volkswagen AG'` and similar for all 5 clusters.\n")
        f.write("8. **Commit** as one cohesive change with message referencing this plan.\n")

    print(f"Report written: {REPORT_PATH.relative_to(PROJECT_ROOT)}")
    print(f"  Renames needed: {len(db_rename_plan)}")
    print(f"  New aliases needed: {len(new_alias_proposals)}")
    print(f"  Untouched: {len(untouched)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

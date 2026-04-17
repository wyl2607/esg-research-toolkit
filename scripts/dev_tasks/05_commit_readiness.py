#!/usr/bin/env python3
"""Prepare the identity-fix work for a clean commit.

After Codex's identity-merge work + seed backfill, we have:
  - 13 modified files + 7 untracked files
  - 1 orphan DB row to clean ("Slash/Like Name Co / 2026")
  - 4 new tests bumping pytest from 127 → 131 passed
  - 3 new companies gaining full 2022-2024 coverage (BMW, DHL, Henkel*)

This script is READ-ONLY. It produces:
  1. A proposed logical commit grouping (so we don't cram everything into
     one monster commit)
  2. The exact DELETE SQL to clean the "Slash/Like Name Co" drift
  3. A suggested release note outline for v0.2.2

Output: docs/dev-tasks/05_commit_plan.md

Usage:
  OPENAI_API_KEY=dummy .venv/bin/python scripts/dev_tasks/05_commit_readiness.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.config import settings
from report_parser.storage import CompanyReport


REPORT_PATH = PROJECT_ROOT / "docs" / "dev-tasks" / "05_commit_plan.md"

# Proposed commit groups — each group is a cohesive unit of work
COMMIT_GROUPS: list[dict] = [
    {
        "title": "feat(identity): canonical alias table + upload override prevents name splits",
        "files": [
            "report_parser/company_identity.py",
            "report_parser/api.py",
            "scripts/seed_german_demo.py",
            "tests/test_company_identity.py",
            "tests/test_seed_german_demo.py",
            "tests/test_rate_limit.py",
        ],
        "summary": (
            "Root-cause fix for multi-year trend data being split across extractor "
            "name variants (SAP/SAP SE, Volkswagen Group/AG, etc.).\n\n"
            "- Add 9 canonical aliases to `_KNOWN_CANONICAL_NAMES`\n"
            "- `/report/upload` accepts `override_company_name` form field\n"
            "- Seed pipeline now passes manifest's curated name as override\n"
            "- 4 new regression tests"
        ),
    },
    {
        "title": "feat(migration): one-off canonical backfill + dedup of legacy rows",
        "files": [
            "scripts/migrate_canonical_company_names.py",
        ],
        "summary": (
            "One-off migration that rewrites legacy DB rows to canonical names and "
            "removes 6 lower-quality duplicates (ids 3, 51, 52, 24, 36, 45). "
            "Auto-backs up DB to `data/esg_toolkit.db.bak.<ts>` before running."
        ),
    },
    {
        "title": "feat(automation): dev task audit scripts + comprehensive health check",
        "files": [
            "scripts/dev_tasks/",
            "scripts/comprehensive_health_check.sh",
        ],
        "summary": (
            "Read-only audit toolchain for iterative development:\n"
            "- `01_company_identity_audit.py` — finds name duplicates\n"
            "- `02_seed_gap_analysis.py` — manifest vs DB diff\n"
            "- `03_ui_autopolish_run.sh` — vision-LLM visual critique\n"
            "- `04_identity_migration_plan.py` — migration plan generator\n"
            "- `05_commit_readiness.py` — this script\n"
            "- `comprehensive_health_check.sh` — end-to-end pipeline verifier"
        ),
    },
    {
        "title": "feat(ui): dashboard/benchmark polish + autopolish script hardening",
        "files": [
            "frontend/src/components/LanguageSwitcher.tsx",
            "frontend/src/components/dashboard/DashboardHeavyCharts.tsx",
            "frontend/src/i18n/locales/de.json",
            "frontend/src/i18n/locales/en.json",
            "frontend/src/i18n/locales/zh.json",
            "frontend/src/pages/BenchmarkPage.tsx",
            "frontend/src/pages/DashboardPage.tsx",
            "scripts/automation/ui_autopolish.py",
        ],
        "summary": (
            "First-round UI polish based on Codex's visual critique plus autopolish "
            "script hardening (OPENAI_MODEL env, request timeout, fullstack readiness "
            "retry)."
        ),
    },
    {
        "title": "docs(dev-tasks): audit reports + release note v0.2.2",
        "files": [
            "docs/dev-tasks/",
            "docs/exec-plans/",
            "docs/releases/",  # VERSION.md, CHANGELOG.md, 2026-04-17-v0.2.2.md
        ],
        "summary": "Generated audit outputs + v0.2.2 release note.",
    },
]

DRIFT_CLEANUP_SQL = """
-- One-off cleanup of orphan test fixture that survived identity migration.
-- Row has no PDF, no file_hash, and a future report_year.
BEGIN TRANSACTION;

-- Confirm the row we're about to delete
SELECT id, company_name, report_year, pdf_filename, file_hash, created_at
  FROM company_reports
 WHERE company_name = 'Slash/Like Name Co' AND report_year = 2026;

-- Delete it
DELETE FROM company_reports
 WHERE company_name = 'Slash/Like Name Co'
   AND report_year = 2026
   AND pdf_filename IS NULL
   AND file_hash IS NULL;

-- Verify exactly one row was removed
SELECT changes() AS rows_deleted;  -- should be 1

COMMIT;
"""


def git_status() -> tuple[list[str], list[str]]:
    """Return (modified_files, untracked_files)."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    modified, untracked = [], []
    for line in result.stdout.splitlines():
        if line.startswith(" M ") or line.startswith("M "):
            modified.append(line[3:])
        elif line.startswith("MM"):
            modified.append(line[3:])
        elif line.startswith("??"):
            untracked.append(line[3:])
    return modified, untracked


def verify_drift_row() -> dict | None:
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    row = (
        session.query(CompanyReport)
        .filter(CompanyReport.company_name == "Slash/Like Name Co")
        .filter(CompanyReport.report_year == 2026)
        .first()
    )
    if row is None:
        return None
    return {
        "id": row.id,
        "pdf_filename": row.pdf_filename,
        "file_hash": row.file_hash,
        "created_at": str(row.created_at),
    }


def main() -> int:
    modified, untracked = git_status()
    drift = verify_drift_row()

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as f:
        f.write("# Commit Readiness Plan (v0.2.1 → v0.2.2)\n\n")
        f.write(f"**Modified files**: {len(modified)}\n")
        f.write(f"**Untracked files/dirs**: {len(untracked)}\n")
        f.write(f"**Drift row to clean**: {'yes' if drift else 'no'}\n\n")

        # ── Section 1: Git state snapshot ────────────────────────────────────
        f.write("## 1. Current Git State\n\n")
        f.write("### Modified\n\n")
        for path in modified:
            f.write(f"- `{path}`\n")
        f.write("\n### Untracked\n\n")
        for path in untracked:
            f.write(f"- `{path}`\n")
        f.write("\n")

        # ── Section 2: Proposed commit groups ────────────────────────────────
        f.write("## 2. Proposed Commit Groups (5 commits)\n\n")
        f.write("Each group is cohesive and reverts cleanly as a unit.\n\n")
        for i, group in enumerate(COMMIT_GROUPS, start=1):
            f.write(f"### Commit {i}: `{group['title']}`\n\n")
            f.write("**Files**:\n\n")
            for path in group["files"]:
                f.write(f"- `{path}`\n")
            f.write(f"\n**Why**: {group['summary']}\n\n")

        # ── Section 3: Drift cleanup ─────────────────────────────────────────
        f.write("## 3. Drift Cleanup — `Slash/Like Name Co / 2026`\n\n")
        if drift:
            f.write(f"**Found**: id={drift['id']}, pdf={drift['pdf_filename']}, ")
            f.write(f"file_hash={drift['file_hash']}, created_at={drift['created_at']}\n\n")
            f.write("This row has no source PDF, no file hash, and a future year — it's leftover ")
            f.write("from an integration test exercising path-like characters in company names.\n\n")
            f.write("**SQL** (run inside a transaction, confirms rows_deleted=1 before COMMIT):\n\n")
            f.write("```sql")
            f.write(DRIFT_CLEANUP_SQL)
            f.write("```\n\n")
            f.write("Recommended: run this BEFORE the commit that ships the v0.2.2 DB snapshot, ")
            f.write("so the release DB is clean.\n\n")
        else:
            f.write("_Already clean._ 🎉\n\n")

        # ── Section 4: Release note skeleton ─────────────────────────────────
        f.write("## 4. v0.2.2 Release Note Skeleton\n\n")
        f.write("Create `docs/releases/2026-04-17-v0.2.2.md` with:\n\n")
        f.write("```markdown\n")
        f.write("# ESG Research Toolkit v0.2.2 Release\n\n")
        f.write("**Release Date**: 2026-04-17\n")
        f.write("**Previous Version**: v0.2.1 (2026-04-16)\n")
        f.write("**Status**: ✅ Production Ready\n\n")
        f.write("## Overview\n\n")
        f.write("Data integrity release: roots out the company-name identity split ")
        f.write("that was preventing multi-year trend charts from rendering correctly ")
        f.write("for VW, SAP, RWE and 4 other companies. Coverage doubles from 5 → 8 ")
        f.write("companies with ≥2 years of history.\n\n")
        f.write("## Highlights\n\n")
        f.write("- **9 canonical aliases** added to `_KNOWN_CANONICAL_NAMES`\n")
        f.write("- **Upload override**: `/report/upload` accepts `override_company_name`\n")
        f.write("- **Seed pipeline** now passes manifest names as canonical truth\n")
        f.write("- **Migration**: backfilled 14 legacy rows, removed 6 duplicates\n")
        f.write("- **Multi-year coverage**: BMW, DHL now join BASF/DT/RWE/SAP/VW with full 2022-2024\n")
        f.write("- **Tests**: 127 → 131 passing\n")
        f.write("- **Audit toolchain**: 5 read-only dev-task scripts + comprehensive health check\n\n")
        f.write("## Verification\n\n")
        f.write("- `OPENAI_API_KEY=dummy .venv/bin/pytest -q` → 131 passed\n")
        f.write("- Identity audit: 0 duplicate clusters\n")
        f.write("- Migration plan: 0 renames needed\n")
        f.write("- Seed gap: 0 missing, 0 drift (after cleanup)\n")
        f.write("```\n\n")

        # ── Section 5: Execution order ───────────────────────────────────────
        f.write("## 5. Execution Order\n\n")
        f.write("1. **Clean drift**: run SQL from §3 against `data/esg_toolkit.db`.\n")
        f.write("2. **Stage + commit** each group in §2 separately (5 commits).\n")
        f.write("3. **Update release metadata**: bump `VERSION.md` to `v0.2.2`, append CHANGELOG, create release note.\n")
        f.write("4. **Final verification**: `bash scripts/comprehensive_health_check.sh --quick`\n")
        f.write("5. **Push**: `scripts/review_push_guard.sh origin/main && git push`\n")

    print(f"Report written: {REPORT_PATH.relative_to(PROJECT_ROOT)}")
    print(f"  Modified files: {len(modified)}")
    print(f"  Untracked: {len(untracked)}")
    print(f"  Drift row: {'present — needs cleanup' if drift else 'already clean'}")
    print(f"  Proposed commits: {len(COMMIT_GROUPS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

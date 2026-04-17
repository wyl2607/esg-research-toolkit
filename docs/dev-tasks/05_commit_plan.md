# Commit Readiness Plan (v0.2.1 → v0.2.2)

**Modified files**: 13
**Untracked files/dirs**: 7
**Drift row to clean**: yes

## 1. Current Git State

### Modified

- `frontend/src/components/LanguageSwitcher.tsx`
- `frontend/src/components/dashboard/DashboardHeavyCharts.tsx`
- `frontend/src/i18n/locales/de.json`
- `frontend/src/i18n/locales/en.json`
- `frontend/src/i18n/locales/zh.json`
- `frontend/src/pages/BenchmarkPage.tsx`
- `frontend/src/pages/DashboardPage.tsx`
- `report_parser/api.py`
- `report_parser/company_identity.py`
- `scripts/automation/ui_autopolish.py`
- `scripts/seed_german_demo.py`
- `tests/test_rate_limit.py`
- `tests/test_seed_german_demo.py`

### Untracked

- `data/`
- `docs/dev-tasks/`
- `docs/exec-plans/`
- `scripts/comprehensive_health_check.sh`
- `scripts/dev_tasks/`
- `scripts/migrate_canonical_company_names.py`
- `tests/test_company_identity.py`

## 2. Proposed Commit Groups (5 commits)

Each group is cohesive and reverts cleanly as a unit.

### Commit 1: `feat(identity): canonical alias table + upload override prevents name splits`

**Files**:

- `report_parser/company_identity.py`
- `report_parser/api.py`
- `scripts/seed_german_demo.py`
- `tests/test_company_identity.py`
- `tests/test_seed_german_demo.py`
- `tests/test_rate_limit.py`

**Why**: Root-cause fix for multi-year trend data being split across extractor name variants (SAP/SAP SE, Volkswagen Group/AG, etc.).

- Add 9 canonical aliases to `_KNOWN_CANONICAL_NAMES`
- `/report/upload` accepts `override_company_name` form field
- Seed pipeline now passes manifest's curated name as override
- 4 new regression tests

### Commit 2: `feat(migration): one-off canonical backfill + dedup of legacy rows`

**Files**:

- `scripts/migrate_canonical_company_names.py`

**Why**: One-off migration that rewrites legacy DB rows to canonical names and removes 6 lower-quality duplicates (ids 3, 51, 52, 24, 36, 45). Auto-backs up DB to `data/esg_toolkit.db.bak.<ts>` before running.

### Commit 3: `feat(automation): dev task audit scripts + comprehensive health check`

**Files**:

- `scripts/dev_tasks/`
- `scripts/comprehensive_health_check.sh`

**Why**: Read-only audit toolchain for iterative development:
- `01_company_identity_audit.py` — finds name duplicates
- `02_seed_gap_analysis.py` — manifest vs DB diff
- `03_ui_autopolish_run.sh` — vision-LLM visual critique
- `04_identity_migration_plan.py` — migration plan generator
- `05_commit_readiness.py` — this script
- `comprehensive_health_check.sh` — end-to-end pipeline verifier

### Commit 4: `feat(ui): dashboard/benchmark polish + autopolish script hardening`

**Files**:

- `frontend/src/components/LanguageSwitcher.tsx`
- `frontend/src/components/dashboard/DashboardHeavyCharts.tsx`
- `frontend/src/i18n/locales/de.json`
- `frontend/src/i18n/locales/en.json`
- `frontend/src/i18n/locales/zh.json`
- `frontend/src/pages/BenchmarkPage.tsx`
- `frontend/src/pages/DashboardPage.tsx`
- `scripts/automation/ui_autopolish.py`

**Why**: First-round UI polish based on Codex's visual critique plus autopolish script hardening (OPENAI_MODEL env, request timeout, fullstack readiness retry).

### Commit 5: `docs(dev-tasks): audit reports + release note v0.2.2`

**Files**:

- `docs/dev-tasks/`
- `docs/exec-plans/`
- `docs/releases/`

**Why**: Generated audit outputs + v0.2.2 release note.

## 3. Drift Cleanup — `Slash/Like Name Co / 2026`

**Found**: id=49, pdf=None, file_hash=None, created_at=2026-04-15 17:51:15.390656

This row has no source PDF, no file hash, and a future year — it's leftover from an integration test exercising path-like characters in company names.

**SQL** (run inside a transaction, confirms rows_deleted=1 before COMMIT):

```sql
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
```

Recommended: run this BEFORE the commit that ships the v0.2.2 DB snapshot, so the release DB is clean.

## 4. v0.2.2 Release Note Skeleton

Create `docs/releases/2026-04-17-v0.2.2.md` with:

```markdown
# ESG Research Toolkit v0.2.2 Release

**Release Date**: 2026-04-17
**Previous Version**: v0.2.1 (2026-04-16)
**Status**: ✅ Production Ready

## Overview

Data integrity release: roots out the company-name identity split that was preventing multi-year trend charts from rendering correctly for VW, SAP, RWE and 4 other companies. Coverage doubles from 5 → 8 companies with ≥2 years of history.

## Highlights

- **9 canonical aliases** added to `_KNOWN_CANONICAL_NAMES`
- **Upload override**: `/report/upload` accepts `override_company_name`
- **Seed pipeline** now passes manifest names as canonical truth
- **Migration**: backfilled 14 legacy rows, removed 6 duplicates
- **Multi-year coverage**: BMW, DHL now join BASF/DT/RWE/SAP/VW with full 2022-2024
- **Tests**: 127 → 131 passing
- **Audit toolchain**: 5 read-only dev-task scripts + comprehensive health check

## Verification

- `OPENAI_API_KEY=dummy .venv/bin/pytest -q` → 131 passed
- Identity audit: 0 duplicate clusters
- Migration plan: 0 renames needed
- Seed gap: 0 missing, 0 drift (after cleanup)
```

## 5. Execution Order

1. **Clean drift**: run SQL from §3 against `data/esg_toolkit.db`.
2. **Stage + commit** each group in §2 separately (5 commits).
3. **Update release metadata**: bump `VERSION.md` to `v0.2.2`, append CHANGELOG, create release note.
4. **Final verification**: `bash scripts/comprehensive_health_check.sh --quick`
5. **Push**: `scripts/review_push_guard.sh origin/main && git push`

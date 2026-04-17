# Identity Migration Plan

**DB**: `sqlite:///./data/esg_toolkit.db`
**Manifest**: `scripts/seed_data/german_demo_manifest.json`
**Renames needed**: 0
**New alias entries needed**: 0
**Untouched (already canonical)**: 22

## 1. Root Cause

`scripts/seed_german_demo.py::upload_company()` POSTs the PDF to `/report/upload` and uses whatever `company_name` the AI extractor returns. The manifest's curated `company_name` is never used to override this. The extractor produces slightly different names per PDF vintage, so the same legal entity ends up split across multiple DB rows.

**Proof** (from Script 01):

```
RWE: 2 reports (2024×2)
RWE AG: 3 reports (2022,2023,2024)
SAP: 2 reports (2022,2023)
SAP SE: 1 report (2024)
Volkswagen AG: 2 reports (2024×2)
Volkswagen Group: 2 reports (2022,2023)
```

## 2. DB Rename Preview (READ-ONLY — not executed)

_No renames needed._

## 3. Proposed `_KNOWN_CANONICAL_NAMES` Additions

_No new aliases needed._

## 4. Long-term Fix — Prevent Future Splits

Patch `scripts/seed_german_demo.py::upload_company()` to force the manifest's curated `company_name` as the final identity:

```python
# After upload_company() returns, reconcile the name before
# downstream storage / history uses kick in.
#
# Option A (preferred): pass override to /report/upload via a new
#   optional form field `override_company_name`. Backend path uses
#   it verbatim, ignoring the AI extraction.
#
# Option B (quick fix, no backend change): after upload success,
#   issue a direct UPDATE on company_reports where id = new_id,
#   setting company_name = company.company_name.
```

## 5. Verification (run AFTER migration)

```bash
# 1. Re-run identity audit — should report 0 clusters
OPENAI_API_KEY=dummy .venv/bin/python scripts/dev_tasks/01_company_identity_audit.py

# 2. Re-run seed gap analysis — 'In DB but NOT in manifest' should drop to 0
OPENAI_API_KEY=dummy .venv/bin/python scripts/dev_tasks/02_seed_gap_analysis.py

# 3. Full pytest — must stay at 127 passed
OPENAI_API_KEY=dummy .venv/bin/pytest -q tests/

# 4. Spot-check multi-year trend for VW (should now show 3 points)
curl -s 'http://localhost:8000/report/companies/Volkswagen%20AG/history' | \
  jq '.trend | length, .periods | length'
```

Expected after success:
- VW, SAP, RWE each show 3 trend points (2022/2023/2024)
- identity audit reports 0 clusters
- seed gap drift count is 0

## 6. Recommended Execution Order

1. **Review this plan** with Claude — especially the canonical choices in §2.
2. **Create a DB backup**: `cp data/esg_toolkit.db data/esg_toolkit.db.pre-merge-$(date +%Y%m%d)`
3. **Apply alias additions** (§3) via an `Edit` on `company_identity.py`.
4. **Apply UPDATE SQL** (§2) inside a transaction — commit only if the dedup check returns 0 rows.
5. **Patch seed script** (§4 Option A or B) to prevent regression.
6. **Re-run verification** (§5).
7. **Add a pytest regression** asserting `canonical_company_name('Volkswagen Group') == 'Volkswagen AG'` and similar for all 5 clusters.
8. **Commit** as one cohesive change with message referencing this plan.

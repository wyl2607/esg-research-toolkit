# Non-NULL Lane Precision Triage — 2026-06-12

Follow-up to [recall-quantification-2026-06-11.md](recall-quantification-2026-06-11.md): the 28 `verdict=incorrect` rows from the non-NULL (precision) lane were adjudicated one by one against the source PDFs.

**Reviewer tag:** `claude-adjudication-20260612` in `audit_qa_results` (append-only, page + quote evidence per row).
**Result:** 19 approved (16 value corrections + 3 NULL-clears), 9 rejected (stored value confirmed correct).

## Headline findings

1. **VW 2024 systematic extraction error (6 fields).** The extractor captured the *"Material non-financial indicators of Volkswagen AG"* parent-entity table (112k employees) instead of Volkswagen Group (614k employees). Scope 1, Scope 2, energy, water, female share and renewable share were all parent-entity or mis-scoped values. All six replaced with Group-consolidated figures (e.g. Scope 1: 1.37 → 3.0 Mt; energy: 1.75 → 19.0M MWh; female: 18.9 → 20.2%).
2. **Auditor-LLM failure modes catalogued.** Of the 9 rejections: column misalignment (DHL 2023 Scope 1: 2022 column read as 2023 — same mode as the Uniper case in the recall audit), a fabricated quote (DHL 2022 Scope 2 "0.98 Mt" appears nowhere in the report), wrong-denominator suggestions (EnBW female: management ratios vs total workforce), category conflation (BMW 2022: Scope 1+2+3 total offered as Scope 3) and digit-clipped PDF text layers (Salzgitter: stored value vindicated by an energy-intensity cross-check).
3. **Canonical definitions applied** (2026-06-12 ruling): Scope 2 = market-based with location-based fallback when market-based is not disclosed (RWE 2023); `female_pct` denominator = total workforce.
4. **Derived ratios stay out.** `renewable_energy_pct` cleared to NULL for VW/Linde 2024 — neither report states a group-wide renewable share as a percentage; ratios computed from energy tables are rejected per the recall-audit precedent.

## Verifier outcome

| metric | baseline (post-recall) | post-triage |
|---|---|---|
| verified | 270 | 268 |
| not_found | 5 | 4 |
| traceability | 98.3% | **98.6%** |

The −2 verified is fully accounted for: 3 wrong values that previously matched stray digits in the PDFs were cleared to NULL (false positives removed), 1 value (Linde water) moved from not_found to verified. Per-row records: `runtime/qa/incorrect-triage-20260612.md` (local), `audit_qa_results` (DB).

## Remaining known issues

- Uniper 2024 Scope 3 `not_found` — pre-existing artifact of the recall-audit precision correction (64,365,479.53 is a summed exact value not printed verbatim).
- Salzgitter ESRS tables need render-based parsing (text layer clips leading digits in two-column layouts).
- VW 2024 orphan empty row on VPS (id=37) still pending SSH-approved cleanup.

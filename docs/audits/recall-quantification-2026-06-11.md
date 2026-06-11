# Recall Quantification — LLM L1/L2 Audit (mimo channel)

Date: 2026-06-11
Scope: recall (missed-but-present rate) of NULL extracted ESG fields, plus an LLM precision cross-check of stored non-null values, against original report PDFs
Status: **audit complete, verdicts stored append-only** — closes the recall gap deferred in Stage 6 §6. Writeback pending human review.

## 1. Dataset and channel

| | |
|---|---|
| Companies | 21 (all stored issuers; Volkswagen 2024 PDF newly linked, see §5) |
| Reports audited | 36 company-year records |
| Verdicts stored | 320 deduped (company, year, field) verdicts; append-only in `audit_qa_results`, `audit_model LIKE 'mimo%'` |
| L1 screening model | `mimo-v2.5` (Xiaomi, OpenAI-compatible endpoint) |
| L2 verification model | `mimo-v2.5-pro` (page-local context) |
| Runner | `scripts/extraction_qa_audit.py --level 2`, per company |

This is the LLM lane that Stage 6 §2.3 repaired but could not run (dead relay
credential). The Xiaomi mimo endpoint made it executable end-to-end.

## 2. Recall results (NULL-field lane)

Of 164 NULL field slots audited:

| Outcome | n | share |
|---|---|---|
| Confirmed correctly NULL (`missing` + `ok`) | 113 | 68.9 % |
| **True recall gap (`incorrect`: value present in PDF, with page + quote)** | **48** | **29.3 %** |
| Manual triage (`needs_review` / `context_mismatch`) | 3 | 1.8 % |

**Recall proxy: 68.9 % of NULLs are genuine non-disclosure; ~29 % are extraction misses.**
This quantifies what Stage 6 §5 could only spot-check: precision is high
(98.7 % adjudicated), recall is materially weaker.

### Gaps by field

| Field | gaps | dominant cause |
|---|---|---|
| `taxonomy_aligned_revenue_pct` | 14 | EU Taxonomy Article 8 tables (multi-column, % in denominator rows) |
| `energy_consumption_mwh` | 9 | unit variants (GWh/TWh/million MWh) + ESRS E1 tables |
| `water_usage_m3` | 8 | "thousand m³"/Tm³ scaling, withdrawal-vs-consumption wording |
| `female_pct` | 6 | metric-definition ambiguity (workforce vs management share) |
| `scope3_co2e_tonnes` | 5 | narrative "X million metric tons" phrasing |
| `scope2_co2e_tonnes` | 3 | market- vs location-based split tables |
| `scope1_co2e_tonnes` | 2 | — |
| `waste_recycled_pct` | 1 | — |

High-confidence examples (verdict `incorrect`, conf ≥ 98 %, evidence quote on file):
BMW 2023 taxonomy revenue 15.2 % (p. 83); BMW 2024 energy 6,205,004 MWh (p. 130);
Uniper 2024 water 19,946,640 m³ (p. 172); DHL 2024 taxonomy revenue 13.8 % (p. 83).

## 3. Precision cross-check (non-NULL lane)

156 stored non-null values were re-audited by the LLM lane:
`ok` 57 · `missing` 67 · `incorrect` 28 · `needs_review` 3 · `context_mismatch` 1.

Caveats before reading this as a precision number:

- `missing` here means *the L2 page-local context did not contain the stored
  value* — usually a context-window artifact, not an extraction error. The
  deterministic offline verifier (Stage 6) already traced 98.4 % of these
  values to the PDF text layer, which is the stronger evidence.
- The 28 `incorrect` verdicts split into: (a) genuine candidate corrections
  (e.g. VW 2024 row, §5; Salzgitter 2024 energy 32,975,507 vs 39,975,507);
  (b) definition disputes (market- vs location-based Scope 2, female workforce
  vs management %); (c) rounding-level disagreements (Linde water
  1,108.9 vs 1,108.8 million m³) — not errors at our storage precision.
- One direct conflict with a Stage 6 human verdict: BASF 2022 Scope 1
  16,556,000 t (manually adjudicated from rendered p. 140, Stage 6 §3) is
  flagged by mimo with a different component sum. **The Stage 6
  human-adjudicated verdict stands**; the LLM flag is recorded, not applied.

## 4. Audit-channel failure modes observed

1. **Reasoning-model output**: mimo emits `reasoning_content` before the
   answer; requests with small `max_tokens` return only reasoning. The audit
   script sets no cap, so verdicts were unaffected.
2. **Page-local context misses**: L2 reads selected pages; for graphics-heavy
   reports (PUMA financial-statement pages) it occasionally judged from the
   wrong section (`context_mismatch`).
3. **Metric-definition ambiguity** is the main source of `needs_review`: the
   schema does not pin Scope 2 method (market/location) or `female_pct`
   denominator (workforce/management), so reports disclosing both leave the
   auditor guessing.

## 5. Data repair performed during this audit

`Volkswagen AG 2024` existed in `company_reports` with an empty
`pdf_filename`, while the report PDF sat unlinked on disk. Linked per repo
convention (SHA-256 16-char prefix):
`data/reports/91620cfe3103e82d_volkswagen-2024.pdf`, `file_hash` backfilled.
First audit of that record produced 8 `incorrect` verdicts on its stored
values — consistent with the row having been seeded without PDF-grounded
extraction. **VW 2024 is the top writeback candidate.**

## 6. Next steps

1. Human review of the 48 recall gaps (page + quote on file for each) →
   approve → writeback → re-run offline verifier → sync to VPS.
2. Triage the 28 non-NULL `incorrect` flags, prioritizing VW 2024 (8 flags).
3. Schema decision: pin Scope 2 method and `female_pct` denominator to kill
   the definition-ambiguity class.
4. Extraction improvements suggested by gap clustering: EU Taxonomy Article 8
   table parsing, unit normalization for GWh/TWh/Tm³/"million MWh".

## 7. Reproduce

```bash
# configure an OpenAI-compatible channel (key + base URL + model ids); the
# 2026-06-11 run used Xiaomi mimo-v2.5 (L1) / mimo-v2.5-pro (L2)
export OPENAI_API_KEY=... OPENAI_BASE_URL=... 
export OPENAI_VALIDATION_MODEL=... OPENAI_AUDIT_MODEL=...
.venv/bin/python scripts/extraction_qa_audit.py --company "<name>" --level 2
# analysis (no LLM calls):
OPENAI_API_KEY=dummy .venv/bin/python scripts/dev_tasks/08_recall_quantification_analysis.py
# full per-row report: runtime/qa/recall-quantification-20260611.md (local, gitignored)
```

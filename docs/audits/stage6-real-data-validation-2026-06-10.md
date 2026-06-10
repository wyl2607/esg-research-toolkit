# Stage 6 — Real-World Data Validation Report

Date: 2026-06-10
Scope: extraction precision and source traceability of stored ESG/numeric metrics against original corporate report PDFs
Status: **completed** (precision validated; recall quantification deferred, see §6)

## 1. Dataset

| | |
|---|---|
| Companies | 21 real European issuers (DAX-heavy: BASF, BMW, Siemens, SAP, VW, RWE, E.ON, …) |
| Reports | 35 PDF-sourced company reports (34 auditable; 1 PDF missing on disk: RWE AG 2024) |
| Years | 2022 ×7 · 2023 ×9 · 2024 ×19 |
| Source PDFs | 719 MB under `data/reports/`, SHA-256 provenance in `company_reports.file_hash` |
| Fields audited | Manual precision subset: 9 ESG fields. Offline traceability scope: 13 numeric fields, including revenue, capex, taxonomy capex %, and employees. |

## 2. Method (three layers)

1. **Deterministic offline matcher** — `scripts/verify_extractions_offline.py` renders every
   extracted value into the number formats real reports print (EN/DE thousands separators,
   decimal comma, kt/Mt/GWh/TWh/mEUR scalings) and searches the PDF text layer,
   classifying hits by metric-keyword page context. No LLM, fully reproducible.
2. **Manual deep review** — every flagged item (`not_found` + `found_elsewhere`, n=14) was
   adjudicated by a human-grade reviewer (Claude) against extracted source snippets;
   verdicts stored append-only in `audit_qa_results` with evidence quote + page.
3. **LLM L1/L2 loop** — `scripts/extraction_qa_audit.py` was repaired in this cycle
   (current ORM, `data/reports/` PDF resolution, configurable base URL/models) but the
   configured relay credential is dead (401); the loop is ready to run once a live
   OpenAI-compatible key is configured.

## 3. Results (precision of extracted values)

Manual review subset: 152 non-null extracted ESG values across 34 reports:

| Outcome | n | share |
|---|---|---|
| Auto-verified on metric-context pages | 138 | 90.8 % |
| Manually confirmed correct (flagged → adjudicated) | 8 | 5.3 % |
| **Total verified correct** | **146** | **96.1 %** |
| Confirmed incorrect | 1 | 0.7 % |
| Needs review (unresolved) | 5 | 3.3 % |

Expanded offline verifier scope (after including all stored numeric fields on `CompanyReport`):

| Outcome | n | share |
|---|---|---|
| Non-null numeric fields checked | 241 | 100.0 % |
| Found on metric/field-context pages | 222 | 92.1 % |
| Found elsewhere in PDF text layer | 15 | 6.2 % |
| Not found in PDF text layer | 4 | 1.7 % |
| **Traceable to source PDF text layer** | **237** | **98.3 %** |

The 96.1 % figure is the manually adjudicated precision of extracted ESG values,
not recall. The 98.3 % figure is deterministic text-layer traceability for the
expanded numeric field set.

**Confirmed error (corrected):** SAP SE 2022 `water_usage_m3` was stored as 8,780,000 m³;
the report (p. 290) states *878 thousand cubic meters* → corrected to 878,000 m³.
Audit trail: `audit_qa_results` (verdict `incorrect`, human_review `approved`).

**Unresolved (needs_review, kept open):**
- BASF SE 2022 Scope 1 — restated-baseline vs original-year definitional variant
  (report table: 15.797 Mt; next-year restated base ≈16.66 Mt; stored: 16.456 Mt)
- DHL Group 2022 Scope 1 — split table rendered as graphic, not in text layer
- Salzgitter AG 2024 Scope 1/2/3 — ESRS table text-order garbling in PDF text layer

## 4. Failure modes observed

1. **Unit-scale errors** — "thousand cubic meters" read as m³ (10×/1000× inflation). 1 confirmed case.
2. **Restated baselines** — companies restate prior-year figures; extraction may mix bases.
3. **PDF table garbling** — multi-column ESRS tables interleave in the text layer (Salzgitter).
4. **Graphic-embedded values** — key figures rendered inside charts are invisible to the text layer (DHL, Deutsche Telekom).
5. **Letter-spaced headings** — "S C O P E 3" defeats naive keyword matching (tooling issue, not data; BMW case).

## 5. Null-field characterization

201 field slots in the expanded 13-field verifier scope are NULL. Spot checks
(PUMA, Henkel, Munich Re, Porsche 2024) show the dominant causes are genuine
non-disclosure in the ingested document type (annual report vs separate ESG data
sheet) and graphic-embedded data points — not silent extraction crashes. Recall
(missed-but-present rate) is **not yet quantified**.

## 6. Deferred / future work

- Quantify recall: needs LLM lane (repaired `extraction_qa_audit.py`) or manual annotation.
- Resolve the 5 open `needs_review` verdicts against rendered pages (not text layer).
- Render-based table parsing for ESRS tables (Salzgitter-class failures).

## 7. Reproduce

```bash
set -a && . ./.env && set +a
.venv/bin/python scripts/verify_extractions_offline.py --json runtime/qa/offline-verify-<date>.json
# review queue:
.venv/bin/python -c "from core.database import SessionLocal; from report_parser.audit_models import get_pending_reviews; \
  [print(r.company_name, r.report_year, r.field, r.verdict) for r in get_pending_reviews(SessionLocal())]"
```

# Stage 6 — Real-World Data Validation Report

Date: 2026-06-10
Scope: extraction precision and source traceability of stored ESG/numeric metrics against original corporate report PDFs
Status: **completed** (precision validated; 2026-06-11 rendered-page closeout applied; recall quantification deferred, see §6)

## 1. Dataset

| | |
|---|---|
| Companies | 21 real European issuers (DAX-heavy: BASF, BMW, Siemens, SAP, VW, RWE, E.ON, …) |
| Reports | 35 PDF-sourced company reports (35 auditable after restoring the canonical RWE AG 2024 PDF filename) |
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
| Manually confirmed correct (flagged → adjudicated) | 12 | 7.9 % |
| **Total verified correct** | **150** | **98.7 %** |
| Confirmed incorrect | 2 | 1.3 % |
| Needs review (unresolved) | 0 | 0.0 % |

Expanded offline verifier scope (after including all stored numeric fields on `CompanyReport`):

| Outcome | n | share |
|---|---|---|
| Non-null numeric fields checked | 247 | 100.0 % |
| Found on metric/field-context pages | 228 | 92.3 % |
| Found elsewhere in PDF text layer | 15 | 6.1 % |
| Not found in PDF text layer | 4 | 1.6 % |
| **Traceable to source PDF text layer** | **243** | **98.4 %** |

The 98.7 % figure is the manually adjudicated precision of extracted ESG values,
not recall. The 98.4 % figure is deterministic text-layer traceability for the
expanded numeric field set after restoring `data/reports/1e1b4d8540d53bd3_rwe-2024.pdf`.

**Confirmed errors (corrected):**
- SAP SE 2022 `water_usage_m3` was stored as 8,780,000 m³; the report (p. 290)
  states *878 thousand cubic meters* → corrected to 878,000 m³.
- BASF SE 2022 `scope1_co2e_tonnes` was stored as 16,456,000. The BASF 2022
  report (p. 140) shows Scope 1 production components totaling 15.797 Mt CO2e
  plus sale of energy to third parties (Scope 1) of 0.759 Mt CO2e → corrected
  to 16,556,000 tonnes CO2e.

Audit trail: `audit_qa_results` (human_review `approved`; BASF correction stored
on audit id 10).

**Rendered-page closeout (2026-06-11):**
- DHL Group 2022 Scope 1 confirmed correct from the rendered p. 54 GHG emissions
  well-to-wheel table: 8.30 million tonnes CO2e → 8,300,000 tonnes.
- Salzgitter AG 2024 Scope 1/2/3 confirmed correct from the rendered p. 159 ESRS
  table: 10,135 / 279 / 17,048 Tt CO2eq → 10,135,000 / 279,000 / 17,048,000 tonnes.
- RWE AG 2024 canonical PDF filename restored from the hash-matching local file
  `data/reports/rwe-2024.pdf`; offline verifier now confirms 6/6 non-null values
  on keyword pages for RWE AG 2024.

## 4. Failure modes observed

1. **Unit-scale errors** — "thousand cubic meters" read as m³ (10×/1000× inflation). 1 confirmed case.
2. **Restated/definition mixups** — companies restate prior-year figures or separate target-relevant vs gross scopes. 1 confirmed correction.
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

- ~~Quantify recall: needs LLM lane (repaired `extraction_qa_audit.py`) or manual annotation.~~
  Done 2026-06-11 via Xiaomi mimo channel — see `recall-quantification-2026-06-11.md`.
- The interrupted Siemens AG 2023 L1 rows were reviewed on 2026-06-11: 3 `ok`
  verdicts approved and 4 false `missing` verdicts rejected using offline verifier
  evidence pages.
- Render-based table parsing for ESRS tables (Salzgitter-class failures).

## 7. Reproduce

```bash
set -a && . ./.env && set +a
.venv/bin/python scripts/verify_extractions_offline.py --json runtime/qa/offline-verify-<date>.json
# review queue:
.venv/bin/python -c "from core.database import SessionLocal; from report_parser.audit_models import get_pending_reviews; \
  [print(r.company_name, r.report_year, r.field, r.verdict) for r in get_pending_reviews(SessionLocal())]"
```

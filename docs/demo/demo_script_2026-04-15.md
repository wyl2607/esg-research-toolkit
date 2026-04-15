# 3-Minute Demo Script — 2026-04-15

This script is aligned to the current repo behavior (`frontend/src/App.tsx`, `frontend/src/lib/api.ts`, backend routers in `main.py`).

## Pre-demo setup (do this before recording/live demo)

- Backend running (`uvicorn main:app --reload --port 8000`).
- Frontend running (`cd frontend && npm run dev`).
- At least one company record available in `/report/companies`.
  - Fast path if empty: seed with `/manual` page (`frontend/src/pages/ManualCaseBuilderPage.tsx` -> `POST /report/manual`).

---

## Timeline narration (3:00)

### 0:00–0:30 — Open with portfolio view (Dashboard)

**Action**
- Land on `/` (`DashboardPage.tsx`).
- Point out 3 KPIs and trend/emitters visuals.

**Narration**
> “This is the ESG operations cockpit. These cards are not static: they come from `GET /report/dashboard/stats` and the company table from `GET /report/companies`. We can see portfolio-level alignment and coverage before drilling into one issuer.”

### 0:30–1:10 — Show ingestion path (Upload or Manual)

**Action (preferred if API key is configured)**
- Go to `/upload`.
- Drag one PDF or show existing recent upload result card.
- Mention batch mode is available.

**Narration**
> “Ingestion is centered on one workflow: single-file upload or batch upload. The backend extracts report text, runs ESG metric extraction, and saves normalized records with evidence metadata. Batch status is polled live from `/report/jobs/{batch_id}`.”

**Fallback narration if avoiding live upload**
> “For deterministic demos, we can seed records via the Manual Case Builder at `/manual`, which calls `/report/manual` and feeds the exact same downstream scoring and comparison pages.”

### 1:10–1:50 — Show Taxonomy result + export

**Action**
- Go to `/taxonomy`.
- Select one company-year.
- Highlight revenue/capex/opex alignment, DNSH status, gaps/recommendations.
- Click “Download PDF” (or mention endpoint if skipping file save).

**Narration**
> “Here we run EU Taxonomy scoring on stored company data. The page uses `/taxonomy/report` for structured output and can export a PDF through `/taxonomy/report/pdf`. You can see objective-level scoring, DNSH pass/fail, and concrete remediation recommendations.”

### 1:50–2:30 — Show multi-framework and regional comparison

**Action**
- Go to `/frameworks` and select the same company-year.
- Then go to `/regional` (or `/frameworks/regional`) for EU/CN/US matrix.

**Narration**
> “The same underlying company record is scored across multiple disclosure frameworks. This lets us compare grade, coverage, and dimension gaps side by side. The regional page then reframes it into EU/CN/US requirement matrices and compliance priorities.”

### 2:30–3:00 — Close with peer benchmark + provenance traceability

**Action**
- Go to `/benchmarks`, pick an industry code, and show percentile table + contributing companies.
- Optionally open `/companies/:companyName` and show provenance/source summary.

**Narration**
> “Finally, benchmarking puts one company in an industry context via percentile bands. Recompute is one click from `/benchmarks/recompute`. At company profile level, we keep source/provenance context so analysts can explain where each metric came from and which source won during merge.”

---

## If asked “what is production-ready today?”

Use this precise answer:

- Working now in repo: report storage/listing, taxonomy scoring/reporting, multi-framework comparison, regional matrix, benchmark recomputation, LCOE+sensitivity APIs, React workflow pages, Playwright smoke/a11y suite.
- Caveat to state honestly: some frontend client methods are ahead of backend routes (e.g., `/techno/results`, `/techno/compare` in `frontend/src/lib/api.ts`), so avoid claiming those endpoints are live until implemented.

# Technical Interview Q&A (Repo-Tied)

Below are 20 practical Q&A prompts mapped to concrete modules in this repository.

## 1) Q: Where does the backend start, and how are features mounted?
A: `main.py` is the FastAPI entrypoint. It wires routers from `report_parser`, `taxonomy_scorer`, `techno_economics`, `esg_frameworks`, and `benchmark`, and initializes DB on startup.

## 2) Q: How does the frontend reach backend APIs without hardcoding full URLs?
A: `frontend/vite.config.ts` proxies `/api/*` to `http://localhost:8000/*` by rewriting the `/api` prefix.

## 3) Q: What is the core ESG data contract across modules?
A: `core/schemas.py::CompanyESGData` is the shared model used by parser, taxonomy scorer, frameworks scoring, and API responses.

## 4) Q: How does PDF extraction degrade when one parser fails?
A: `report_parser/extractor.py` tries PyMuPDF first; if extraction is too short or errors, it falls back to pdfplumber.

## 5) Q: What happens if LLM extraction fails?
A: `report_parser/analyzer.py` catches failures and applies regex fallback extraction. It can also run regex-only mode via `PARSER_REGEX_ONLY=1`.

## 6) Q: Which endpoint should I use for deterministic demo seeding without files?
A: `POST /report/manual` in `report_parser/api.py`, surfaced by `frontend/src/pages/ManualCaseBuilderPage.tsx`.

## 7) Q: How are duplicate company names consolidated?
A: `report_parser/company_identity.py` canonicalizes aliases and collapses records by quality score (document priority + metric completeness + evidence density).

## 8) Q: Where is merge logic for multi-source company-year records?
A: `report_parser/merge_engine.py`, exposed as `/report/merge/preview` and used in company history/profile assembly in `report_parser/api.py`.

## 9) Q: How are taxonomy objective scores and DNSH computed?
A: `taxonomy_scorer/scorer.py` computes objective scores and DNSH checks with simplified rule logic keyed by activities and disclosed metrics.

## 10) Q: Which endpoint returns taxonomy report text vs structured output?
A: Text summary: `POST /taxonomy/report/text`; structured JSON: `POST /taxonomy/report`; lookup by company-year: `GET /taxonomy/report`.

## 11) Q: How is multi-framework scoring cached?
A: `esg_frameworks/api.py` uses an in-memory `TTLCache` (`maxsize=200`, `ttl=300`) for `/frameworks/compare` requests and exposes `/frameworks/cache/clear`.

## 12) Q: Where are framework run results persisted?
A: `esg_frameworks/storage.py` stores runs in `framework_analysis_results` with payload dedup based on normalized result JSON + framework version.

## 13) Q: How are industry benchmarks computed?
A: `benchmark/compute.py` groups `CompanyReport` values by `(industry_code, year, metric)` and computes p10/p25/p50/p75/p90 summaries.

## 14) Q: Which frontend pages are data-heavy and API-driven?
A: `DashboardPage`, `UploadPage`, `TaxonomyPage`, `FrameworksPage`, `RegionalPage`, `BenchmarkPage`, `CompanyProfilePage` (all in `frontend/src/pages/`).

## 15) Q: How is deletion handled for compliance workflows?
A: `report_parser/storage.py` supports soft deletion (`request_deletion`: removes local PDF, marks deletion requested) and hard delete (`hard_delete_report`). API routes: `POST /report/companies/.../request-deletion`, `DELETE /report/companies/...`.

## 16) Q: What tests verify seeded end-to-end UI behavior?
A: `frontend/tests/workflow.spec.ts` seeds manual records through API and validates `/companies` and `/frameworks` flows in Playwright.

## 17) Q: Give one example of frontend/backend API drift visible today.
A: `frontend/src/lib/api.ts` includes `/techno/results` and `/techno/compare`, but `techno_economics/api.py` does not implement those routes.

## 18) Q: Are there data-shape drifts in techno-economics between frontend and backend?
A: Yes. Backend sensitivity returns `variations` and `lcoe_values` (`techno_economics/api.py`), while frontend chart code expects `values` and `lcoe_results` (`frontend/src/lib/types.ts`, `frontend/src/pages/LcoePage.tsx`).

## 19) Q: What deployment topology is defined in-repo?
A: Containerized FastAPI service with persisted `data/` and `reports/` volumes (`docker-compose.yml`, `docker-compose.prod.yml`) and health probe on `/health`.

## 20) Q: If asked for an immediate stabilization roadmap, what are first 3 tasks?
A: (1) Enforce API contract sync between `frontend/src/lib/api.ts` and backend routes; (2) split `report_parser/api.py` into smaller routers; (3) normalize DB session injection in taxonomy GET endpoints.

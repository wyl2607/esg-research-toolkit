# Architecture Audit — 2026-04-15

## Scope and method

This audit is based on the current `burn/lane-4-docs` worktree state and focuses on runtime code in:

- Backend: `main.py`, `core/`, `report_parser/`, `taxonomy_scorer/`, `esg_frameworks/`, `benchmark/`, `techno_economics/`
- Frontend: `frontend/src/` (routing, API client, page flows)
- Tests and runtime support: `tests/`, `frontend/tests/`, `docker-compose*.yml`

---

## 1) Current module map (repo-as-built)

## Runtime entry and composition

- `main.py`
  - Creates FastAPI app, CORS, startup DB init, and mounts module routers.
  - Current mounted domains: `/report`, `/taxonomy`, `/techno`, `/frameworks`, `/benchmarks`.
- `core/config.py`
  - Pydantic settings contract (`OPENAI_API_KEY`, `DATABASE_URL`, model/base URL, batch worker count).
- `core/database.py`
  - SQLAlchemy engine/session/base.
  - `init_db()` also calls `report_parser.storage.ensure_storage_schema()` for additive schema migration compatibility.

## Backend domain modules

- `report_parser/`
  - Ingestion and storage hub.
  - `api.py` handles file upload, batch jobs, manual entry, merge preview, company/profile/history, dashboard stats, export, deletion requests.
  - `analyzer.py` uses `core.ai_client.complete()` plus regex fallback.
  - `extractor.py` uses PyMuPDF first, pdfplumber fallback.
  - `storage.py` defines `CompanyReport` model and data-access helpers.
- `taxonomy_scorer/`
  - `/taxonomy/*` scoring, report generation, activity catalog, PDF export.
  - `scorer.py` defines simplified taxonomy alignment/DNSH logic.
- `esg_frameworks/`
  - Multi-framework scoring (`EU taxonomy`, `CSRC 2023`, `CSRD`, `SEC`, `GRI`, `SASB`), regional comparison, result caching/persistence.
  - `storage.py` persists framework run payloads in `framework_analysis_results`.
- `benchmark/`
  - Recomputes percentile bands per industry/year/metric from `CompanyReport`.
- `techno_economics/`
  - LCOE/NPV/IRR + sensitivity endpoints.

## Frontend structure

- `frontend/src/App.tsx`
  - Route shell (`Layout`) with lazy-loaded pages:
    - `/`, `/upload`, `/companies`, `/companies/:companyName`, `/taxonomy`, `/frameworks`, `/frameworks/regional`, `/benchmarks`, `/compare`, `/manual`, `/lcoe`, `/regional`.
- `frontend/src/lib/api.ts`
  - Single typed fetch client module used by all pages.
- `frontend/vite.config.ts`
  - `/api` proxy to `http://localhost:8000`, rewriting `/api/*` -> `/*`.

## Data and deployment

- SQLite default: `data/esg_toolkit.db` (`core/config.py`).
- Local/prod compose mount persistent `data/` and `reports/` volumes (`docker-compose.yml`, `docker-compose.prod.yml`).

---

## 2) Dependency/coupling observations

### Observation A — `report_parser` is the backend coupling center

Evidence:

- `report_parser/api.py` imports from:
  - `benchmark.compute` (`BENCHMARK_METRICS`)
  - `esg_frameworks.storage` (`list_framework_results`)
  - `esg_frameworks.api` (`_SCORERS`)
- `core/database.py` imports `report_parser.storage.ensure_storage_schema` in startup.

Impact:

- High change blast radius: ingestion, profile, benchmark, and framework concerns are tightly entangled in one API module.
- Harder to test/extend in isolated slices.

### Observation B — API contract drift exists between frontend client and backend routes

Evidence:

- Frontend client declares routes with no backend handler:
  - `frontend/src/lib/api.ts`: `/techno/results`, `/techno/compare`
  - Backend `techno_economics/api.py`: only `/techno/lcoe`, `/techno/sensitivity`, `/techno/benchmarks`
- Frontend client has `updateCompany()` using `PUT /report/companies/{name}/{year}` but backend only exposes `GET`/`DELETE` for that path (`report_parser/api.py`).
- Sensitivity payload mismatch:
  - Backend returns `variations` + `lcoe_values` (`techno_economics/api.py`)
  - Frontend chart code expects `values` + `lcoe_results` (`frontend/src/pages/LcoePage.tsx`, `frontend/src/lib/types.ts`).

Impact:

- Hidden runtime defects (no TS compile failure, but empty/incorrect runtime behavior).
- Documentation and demo behavior can diverge from actual API capability.

### Observation C — session lifecycle is inconsistent in some GET flows

Evidence:

- `taxonomy_scorer/api.py` uses `db = next(get_db())` in `get_report_by_name()` and `download_pdf_report()` instead of dependency-injected `Session` parameters.

Impact:

- Session cleanup relies on generator finalization behavior rather than explicit request lifecycle wiring.
- Harder to enforce consistent transaction/session handling across routes.

### Observation D — front-end/backend schema mismatch around LCOE input

Evidence:

- Frontend `LCOEInput` includes `capacity_mw` (`frontend/src/lib/types.ts`, `frontend/src/pages/LcoePage.tsx`).
- Backend `core/schemas.py::LCOEInput` has no `capacity_mw` field.

Impact:

- UI implies a parameter that backend ignores.
- Confuses demo narratives about what actually drives computation.

---

## 3) Top 3 structure recommendations (actionable)

### 1. Generate and enforce API contracts from OpenAPI

What to change:

- Treat backend OpenAPI (`/openapi.json`) as source of truth and generate frontend client/types.
- Replace hand-maintained endpoint strings in `frontend/src/lib/api.ts` for core paths.
- Add CI check that fails if frontend references nonexistent endpoints.

Why now:

- Current contract drift is already visible (`/techno/results`, `/techno/compare`, `PUT /report/companies/...`).
- This is the fastest risk reduction for docs/demo correctness.

First small PR:

- Add a route inventory test validating `frontend/src/lib/api.ts` endpoint literals against backend routes.
- Remove or mark unsupported client methods until backend support exists.

### 2. Split `report_parser/api.py` into router slices with a shared service layer

What to change:

- Extract routers by concern:
  - `report_ingest_router` (`/upload`, `/upload/batch`, `/manual`, `/jobs/*`)
  - `report_company_router` (`/companies*`, `/history`, `/profile`, exports, deletion)
  - `report_merge_router` (`/merge/preview`)
  - `report_dashboard_router` (`/dashboard/stats`)
- Keep shared transforms/normalizers in service modules (not router files).

Why now:

- Current ~1000-line router file is a maintenance hotspot and import hub.
- Smaller router units reduce merge conflicts and speed targeted tests.

First small PR:

- Move only `/dashboard/stats` and `/companies` list/export handlers first (minimal risk), preserving public API paths.

### 3. Introduce a thin “domain contract” boundary for cross-module reads

What to change:

- Stop importing internal symbols across domains where possible (e.g., `esg_frameworks.api._SCORERS` from `report_parser/api.py`).
- Export stable service functions/interfaces instead (e.g., `esg_frameworks.service.score_all_frameworks(data)`).
- Normalize DB session injection on all read endpoints (`Depends(get_db)`), including taxonomy GET/PDF routes.

Why now:

- Current direct cross-module imports raise coupling and make future refactors brittle.
- Session handling inconsistency is a reliability footgun in long-running/API-heavy deployments.

First small PR:

- Create `esg_frameworks/service.py` with wrapper around existing scorers and migrate `report_parser/api.py` to consume it.
- Convert taxonomy read routes to dependency injection style sessions.

---

## Quick risk summary

- **Highest immediate correctness risk:** frontend/backend contract drift.
- **Highest structural debt hotspot:** `report_parser/api.py` as multi-concern router/service hybrid.
- **Most leverage per effort:** contract enforcement + router decomposition sequence above.

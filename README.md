# ESG Research Toolkit

🌐 [English](README.md) · [中文](README.zh.md) · [Deutsch](README.de.md)

> Evidence-backed analyst workspace for public corporate sustainability disclosures:
> ingest official reports, review extracted evidence, track company history across
> periods, compare framework interpretations, and export a defensible analysis pack.

![Python](https://img.shields.io/badge/Python-3.12%2B-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688) ![React](https://img.shields.io/badge/React-19%2B-61DAFB) ![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Features

- 📄 Parse annual sustainability and company reports from uploaded public disclosures.
- 🎯 Use a gap-aware **Company+Year picker** to find missing reporting periods and deep-link into upload or official-source backfill.
- 📥 Review auto-fetched official-source disclosures in **Pending Disclosures** before they merge into company history.
- 🔎 Preserve source-document context, period metadata, and evidence anchors for important metrics.
- 🧠 Run multi-framework scoring across EU Taxonomy, China CSRC, and EU CSRD/ESRS-style surfaces with version-aware context.
- 📈 Compare companies and periods with normalized source/period/evidence summaries.
- 📊 Export company records to CSV/XLSX and generate PDF reports for external review.
- 🔬 Keep LCOE, SAF, and renewable-energy economics as optional analysis tools rather than the first demo path.
- 🖥️ Provide a React frontend for company history, disclosure review, comparison, framework analysis, and export workflows.
- 💱 Region-aware LCOE defaults (EUR / USD) with EIA US wholesale price reference on the English UI.
- 🐳 Support local Docker deployment with persistent `data/` and `reports/` volumes.

## Analyst Workflow

The primary workflow is intentionally narrow and repeatable:

```text
Companies missing year
  -> Upload or Auto Fetch
  -> Pending Disclosures review
  -> Company Profile trends and evidence
  -> Framework Compare
  -> CSV/XLSX/PDF delivery pack
```

The first strong MVP should prove that an analyst can explain how a company's
disclosure quality and regulatory readiness changed over time, with every
important claim tied back to a reporting period and source document. Renewable
economics tools remain available for deeper project analysis, but they are not
the default product narrative.

## ✅ Real-World Validation

Extraction precision has been validated against **35 real corporate reports
(34 validated; 1 PDF missing; 21 European issuers, 2022–2024, 719 MB of source PDFs)**
using a deterministic offline matcher plus manual evidence review. This measures
precision of extracted values; recall is not yet quantified.

| Metric | Result |
|---|---|
| Extracted values verified correct against source PDF (precision) | **96.1 %** (146/152) |
| Expanded numeric-field traceability to source PDF text layer | **98.3 %** (237/241) |
| Confirmed extraction errors | 1 (unit-scale error, corrected with audit trail) |
| Open `needs_review` items | 5 |

Known failure modes: unit-scale confusion ("thousand m³"), restated baselines,
PDF table garbling, and chart-embedded values. Full report:
[`docs/audits/stage6-real-data-validation-2026-06-10.md`](docs/audits/stage6-real-data-validation-2026-06-10.md) ·
Reproduce with `scripts/verify_extractions_offline.py`.

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker (optional)

### Local Development

1. Clone and enter the repository:

```bash
git clone https://github.com/wyl2607/esg-research-toolkit.git
cd esg-research-toolkit
```

2. Set up backend dependencies and run FastAPI:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
```

3. Start frontend dev server in a new terminal:

```bash
cd frontend
npm install
npm run dev
```

### Weekday Frontend Health Check

Run a full frontend health pass (lint, build, Playwright smoke, axe, Lighthouse):

```bash
cd frontend
npm run health:check
```

When failures, bundle regressions, obvious layout issues, or new console/network errors are detected, a summary is generated at:

```text
frontend/health-reports/latest/summary.md
```

### Docker

Run the whole backend stack with Docker Compose:

```bash
cp .env.example .env
docker-compose up -d --build
```

Backend API will be exposed on `http://localhost:8000`.

## 📡 API Reference

The table below is generated from current FastAPI routes in `main.py`.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Root health/info landing response. |
| GET | `/docs` | Swagger UI for interactive API documentation. |
| GET | `/docs/oauth2-redirect` | OAuth redirect helper used by Swagger UI. |
| GET | `/frameworks/compare` | Compare scoring output across ESG frameworks. |
| GET | `/frameworks/list` | List supported ESG frameworks and metadata. |
| GET | `/frameworks/score` | Score a company across frameworks using query params. |
| POST | `/frameworks/score/upload` | Upload report and run cross-framework scoring. |
| GET | `/health` | Service health probe endpoint. |
| GET | `/openapi.json` | OpenAPI schema document. |
| GET | `/redoc` | ReDoc API documentation UI. |
| GET | `/report/companies` | List stored company report records. |
| GET | `/report/companies/v2` | List companies with imported + suggested years (feeds the gap-aware company/year picker). |
| POST | `/disclosures/fetch` | Queue an auto-fetch attempt against official sources for `(company, year)`. |
| GET | `/disclosures/pending` | List pending auto-fetched disclosures awaiting analyst review. |
| POST | `/disclosures/{id}/approve` | Merge selected metrics from a pending disclosure into company history. |
| POST | `/disclosures/{id}/reject` | Reject a pending disclosure with an analyst note. |
| GET | `/disclosures/lane-stats` | Per-source-lane fetch reliability telemetry + recommended lane order. |
| GET | `/report/companies/export/csv` | Export stored company records as CSV. |
| GET | `/report/companies/export/xlsx` | Export stored company records as Excel. |
| GET | `/report/companies/{company_name}/{report_year:int}` | Get one stored company record by key. |
| DELETE | `/report/companies/{company_name}/{report_year:int}` | Hard-delete a stored company record. |
| POST | `/report/companies/{company_name}/{report_year:int}/request-deletion` | Create deletion request workflow for a record. |
| GET | `/report/jobs/{batch_id}` | Check status of an async batch upload job. |
| POST | `/report/upload` | Upload and parse one ESG report. |
| POST | `/report/upload/batch` | Upload multiple reports for batch parsing. |
| GET | `/taxonomy/activities` | List taxonomy activity catalog. |
| POST | `/taxonomy/report` | Generate taxonomy report from structured input. |
| GET | `/taxonomy/report` | Query existing taxonomy report by company/year. |
| GET | `/taxonomy/report/pdf` | Generate and download taxonomy PDF report. |
| POST | `/taxonomy/report/text` | Generate narrative text taxonomy report. |
| POST | `/taxonomy/score` | Run EU Taxonomy scoring for supplied metrics. |
| GET | `/techno/benchmarks` | Get benchmark assumptions for techno-economic analysis. |
| POST | `/techno/lcoe` | Compute LCOE from project input parameters. |
| POST | `/techno/sensitivity` | Run sensitivity analysis around techno assumptions. |

## 🛡 Auto-Fetch Compliance Guardrails (F2)

The disclosure backfill flow (`POST /disclosures/fetch` + pending review in Upload page) is intentionally constrained:

- **Supported official-source lanes:** company website disclosure pages, SEC EDGAR, HKEX filings, and CSRC/CNINFO search entry points.
- **Explicitly excluded:** paid/proprietary ESG data providers and third-party scraped aggregation sites.
- **Identification:** requests include a project user-agent (`esg-research-toolkit/<ver> (+contact)`).
- **Rate limits by policy:** per-host fetch pace and global concurrency are restricted; records go to `pending_disclosures` first and require explicit approve/reject before merge.

## 🏗 Architecture

```text
React Frontend (Vite)
        |
        v
      Nginx
        |
        v
 FastAPI Backend (main.py)
        |
        v
 SQLite (data/esg_toolkit.db) + File Reports (reports/)
```

Frontend handles the analyst workflow: company/year coverage, upload,
official-source disclosure review, company profile trends, framework comparison,
and exports. FastAPI exposes the ingestion, scoring, review, and reporting APIs.
Persistent data is stored in SQLite and generated artifacts are saved under
`reports/`.

## 🌍 Multi-Framework ESG

### EU Taxonomy 2020

EU Taxonomy evaluates environmental alignment by activity-level criteria and percentage alignment for revenue/CapEx/OpEx. This project includes DNSH checks and targeted recommendations for gaps.

### China CSRC 2023

CSRC 2023 emphasizes mandatory ESG disclosure for listed companies with practical E/S/G disclosure dimensions. The toolkit maps extracted report data into CSRC-compatible scoring outputs.

### EU CSRD / ESRS

CSRD/ESRS introduces broader sustainability reporting requirements across environmental, social, and governance themes. The platform supports comparison so teams can identify overlap and reporting deltas.

## 📊 Frontend Pages

- `DashboardPage.tsx`: overall KPI dashboard with high-level scoring and trend blocks.
- `UploadPage.tsx`: report upload workflow for single/batch file ingestion (honors `?company=&year=` deep-links from the gap picker).
- `PendingDisclosuresPage.tsx`: analyst review lane for auto-fetched official-source disclosures (`/disclosures`).
- `CompanyProfilePage.tsx`: multi-period company profile with normalized period, source-document, framework, and evidence context.
- `ComparePage.tsx`: side-by-side company comparison with normalized source/period/evidence summaries.
- `FrameworksPage.tsx`: framework-specific scoring and standards view.
- `TaxonomyPage.tsx`: EU Taxonomy scoring and report generation workspace.
- `LcoePage.tsx`: optional techno-economic calculator with LCOE and sensitivity outputs.
- `SafPage.tsx`: optional sustainable aviation fuel cost calculator.
- `CompaniesPage.tsx`: saved company records, lookup, and export actions.

## 🔧 Configuration

Environment variables are loaded from `.env`.

| Variable | Example | Description |
|---|---|---|
| `OPENAI_API_KEY` | `sk-...` | API key for model-backed parsing and enrichment features. |
| `APP_ENV` | `development` | Runtime mode, affects logging and runtime toggles. |
| `APP_HOST` | `0.0.0.0` | Backend bind host. |
| `APP_PORT` | `8000` | Backend bind port. |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173,http://localhost:4173` | Comma-separated allowed browser origins. Set deployed origins explicitly in production. |
| `ADMIN_API_TOKEN` | empty | Optional token required in `X-Admin-Token` for destructive admin routes; required when `APP_ENV=production`. |
| `DATABASE_URL` | `sqlite:///./data/esg_toolkit.db` | SQLAlchemy database connection string. |
| `ARXIV_MAX_RESULTS` | `20` | Max papers fetched for literature helper tasks. |
| `ARXIV_DOWNLOAD_PDF` | `true` | Whether to download PDFs in literature pipeline. |
| `LOG_LEVEL` | `INFO` | Application logging verbosity. |
| `BATCH_MAX_WORKERS` | `2` | Worker count for batch report processing. |

## 🗄️ Database Initialization (Alembic-first)

Apply database schema changes with Alembic:

```bash
./scripts/db_init.sh
# or
alembic upgrade head
```

For existing production databases that already contain schema/data, follow:

- `docs/runbooks/alembic_cutover.md` (includes `alembic stamp 0001_baseline` + `alembic upgrade head` flow)

Legacy note:

- `scripts/migrate_db.py` is kept as a compatibility shim and prints Alembic guidance only (no schema writes).

## 🤝 Contributing

1. Fork this repository and create a feature branch.
2. Add or update tests for the behavior you change.
3. Run checks locally before opening a pull request.
4. Submit a PR with clear scope, validation evidence, and migration notes if needed.

## 📄 License

MIT

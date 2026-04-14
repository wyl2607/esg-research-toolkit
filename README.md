# ESG Research Toolkit

🌐 [English](README.md) · [中文](README.zh.md) · [Deutsch](README.de.md)

> Open-source platform for corporate ESG report analysis, EU Taxonomy compliance scoring,
> multi-framework comparison (EU Taxonomy · CSRC 2023 · CSRD/ESRS), and renewable energy
> techno-economic analysis (LCOE/NPV/IRR).

![Python](https://img.shields.io/badge/Python-3.12%2B-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688) ![React](https://img.shields.io/badge/React-18%2B-61DAFB) ![License](https://img.shields.io/badge/License-MIT-green) ![Live Demo](https://img.shields.io/badge/Live-Demo-orange)

## ✨ Features

- 📄 Parse ESG reports from uploaded files and extract structured sustainability metrics.
- 🧮 Score EU Taxonomy alignment for revenue, CapEx, and OpEx using backend rules.
- 🧠 Run multi-framework scoring across EU Taxonomy 2020, China CSRC 2023, and EU CSRD/ESRS.
- ⚡ Generate gap analysis and actionable recommendations for compliance improvement.
- 📊 Export company records to CSV/XLSX and generate PDF reports for external review.
- 🔬 Calculate LCOE and perform sensitivity analysis for renewable energy economics.
- 🖥️ Provide a React frontend for upload, dashboard, comparison, and company history views.
- 🐳 Support local Docker deployment with persistent `data/` and `reports/` volumes.

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker (optional)

### Local Development

1. Clone and enter the repository:

```bash
git clone https://github.com/your-org/esg-research-toolkit.git
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

Frontend handles user workflows (upload, scoring, dashboard), while FastAPI exposes computation and reporting APIs. Persistent data is stored in SQLite and generated artifacts are saved under `reports/`.

## 🌍 Multi-Framework ESG

### EU Taxonomy 2020

EU Taxonomy evaluates environmental alignment by activity-level criteria and percentage alignment for revenue/CapEx/OpEx. This project includes DNSH checks and targeted recommendations for gaps.

### China CSRC 2023

CSRC 2023 emphasizes mandatory ESG disclosure for listed companies with practical E/S/G disclosure dimensions. The toolkit maps extracted report data into CSRC-compatible scoring outputs.

### EU CSRD / ESRS

CSRD/ESRS introduces broader sustainability reporting requirements across environmental, social, and governance themes. The platform supports comparison so teams can identify overlap and reporting deltas.

## 📊 Frontend Pages

- `DashboardPage.tsx`: overall KPI dashboard with high-level scoring and trend blocks.
- `UploadPage.tsx`: report upload workflow for single/batch file ingestion.
- `TaxonomyPage.tsx`: EU Taxonomy scoring and report generation workspace.
- `FrameworksPage.tsx`: framework-specific scoring and standards view.
- `ComparePage.tsx`: side-by-side framework comparison results.
- `LcoePage.tsx`: techno-economic calculator with LCOE and sensitivity outputs.
- `CompaniesPage.tsx`: saved company records, lookup, and export actions.

## 🔧 Configuration

Environment variables are loaded from `.env`.

| Variable | Example | Description |
|---|---|---|
| `OPENAI_API_KEY` | `sk-...` | API key for model-backed parsing and enrichment features. |
| `APP_ENV` | `development` | Runtime mode, affects logging and runtime toggles. |
| `APP_HOST` | `0.0.0.0` | Backend bind host. |
| `APP_PORT` | `8000` | Backend bind port. |
| `DATABASE_URL` | `sqlite:///./data/esg_toolkit.db` | SQLAlchemy database connection string. |
| `ARXIV_MAX_RESULTS` | `20` | Max papers fetched for literature helper tasks. |
| `ARXIV_DOWNLOAD_PDF` | `true` | Whether to download PDFs in literature pipeline. |
| `LOG_LEVEL` | `INFO` | Application logging verbosity. |
| `BATCH_MAX_WORKERS` | `2` | Worker count for batch report processing. |

## 🤝 Contributing

1. Fork this repository and create a feature branch.
2. Add or update tests for the behavior you change.
3. Run checks locally before opening a pull request.
4. Submit a PR with clear scope, validation evidence, and migration notes if needed.

## 📄 License

MIT

# ESG Research Toolkit

🌐 [English](README.md) · [中文](README.zh.md) · [Deutsch](README.de.md)

> Open-source platform for corporate ESG report analysis, EU Taxonomy compliance scoring,
> multi-framework comparison (EU Taxonomy · CSRC 2023 · CSRD/ESRS), and renewable energy
> techno-economic analysis (LCOE/NPV/IRR).

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](#) [![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?logo=fastapi&logoColor=white)](#) [![React 19](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](#) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](#) [![Live Demo](https://img.shields.io/badge/Live%20Demo-Coming%20Soon-lightgrey)](#)

## ✨ Features
- 🔍 Parse single and batch ESG PDF reports through FastAPI upload endpoints.
- 🧠 Extract structured ESG metrics with OpenAI-assisted text analysis.
- 🗂 Persist company reports in SQLite via SQLAlchemy models.
- 📏 Score disclosures with EU Taxonomy logic including DNSH/TSC checks.
- 🌍 Compare three frameworks: EU Taxonomy 2020, CSRC 2023, and CSRD/ESRS.
- 📉 Run renewable-project techno-economics (LCOE, NPV, IRR, payback).
- 📊 Explore benchmark and sensitivity charts in the React frontend.
- 📄 Export machine-readable JSON reports and downloadable PDF summaries.

## 🚀 Quick Start

### Prerequisites
- Python 3.12+, Node 18+, Docker (optional)

### Local Development
1. Clone and enter the repository:
   ```bash
   git clone https://github.com/wyl2607/esg-research-toolkit.git
   cd esg-research-toolkit
   ```
2. Start backend API:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```
3. Start frontend dashboard:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

### Docker
```bash
cp .env.example .env
docker compose up --build
```

## 📡 API Reference

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/` | Service metadata and module overview |
| `GET` | `/docs` | Swagger UI documentation |
| `GET` | `/docs/oauth2-redirect` | OAuth2 redirect helper for Swagger |
| `GET` | `/frameworks/compare` | Compare a company across all ESG frameworks |
| `GET` | `/frameworks/list` | List supported ESG frameworks and metadata |
| `GET` | `/frameworks/score` | Score a company against one framework |
| `POST` | `/frameworks/score/upload` | Score uploaded CompanyESGData across all frameworks |
| `GET` | `/health` | Service health check |
| `GET` | `/openapi.json` | OpenAPI schema output |
| `GET` | `/redoc` | ReDoc documentation |
| `GET` | `/report/companies` | List stored company ESG reports |
| `GET` | `/report/companies/{company_name}/{report_year}` | Fetch one stored company report |
| `GET` | `/report/jobs/{batch_id}` | Check async batch upload status |
| `POST` | `/report/upload` | Upload one PDF and extract ESG data |
| `POST` | `/report/upload/batch` | Upload up to 20 PDFs for async extraction |
| `GET` | `/taxonomy/activities` | List supported EU Taxonomy activities |
| `POST` | `/taxonomy/report` | Generate structured taxonomy report (JSON) |
| `GET` | `/taxonomy/report` | Generate taxonomy report from stored company data |
| `GET` | `/taxonomy/report/pdf` | Download taxonomy report as PDF |
| `POST` | `/taxonomy/report/text` | Generate plain-text taxonomy summary |
| `POST` | `/taxonomy/score` | Return EU Taxonomy scoring result |
| `GET` | `/techno/benchmarks` | Return benchmark LCOE ranges |
| `POST` | `/techno/lcoe` | Calculate LCOE, NPV, IRR, and payback |
| `POST` | `/techno/sensitivity` | Run CAPEX/OPEX sensitivity analysis |

## 🏗 Architecture

```text
React Frontend (Vite)
        ↓
Nginx (production reverse proxy)
        ↓
FastAPI Backend
        ↓
SQLite + Local Storage (data/, reports/)
```

The frontend calls FastAPI APIs over HTTP, while backend modules share one database and
filesystem workspace for report files and generated outputs.

## 🌍 Multi-Framework ESG

### EU Taxonomy 2020
Aligned with six environmental objectives and Do No Significant Harm checks.
Use it when you need EU-compliance scoring tied to technical screening criteria.

### China CSRC 2023
Implements the Chinese listed-company sustainability reporting guideline structure.
Use it for E/S/G dimension coverage and local disclosure readiness assessment.

### EU CSRD/ESRS
Extends evaluation to ESRS themes such as E1-E5, S1, and G1.
Use it to benchmark report completeness for broader EU sustainability obligations.

## 📊 Frontend Pages

- `DashboardPage.tsx` — Portfolio-level KPI cards and quick drill-down actions.
- `UploadPage.tsx` — Single and batch ESG PDF upload with processing status.
- `CompaniesPage.tsx` — Search, sort, and manage stored company report records.
- `TaxonomyPage.tsx` — EU Taxonomy radar view, gaps, and PDF export.
- `FrameworksPage.tsx` — Cross-framework comparison for EU Taxonomy, CSRC, and CSRD.
- `ComparePage.tsx` — Side-by-side company metric comparison table.
- `LcoePage.tsx` — LCOE calculator with benchmark and sensitivity charts.

## 🔧 Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `OPENAI_API_KEY` | `Required` | OpenAI API key for ESG metric extraction. |
| `APP_ENV` | `development` | Application environment (development/production). |
| `APP_HOST` | `0.0.0.0` | Backend bind host. |
| `APP_PORT` | `8000` | Backend listen port. |
| `DATABASE_URL` | `sqlite:///./data/esg_toolkit.db` | SQLAlchemy connection string. |
| `ARXIV_MAX_RESULTS` | `20` | Maximum paper records for literature pipeline. |
| `ARXIV_DOWNLOAD_PDF` | `true` | Whether to download arXiv PDFs. |
| `LOG_LEVEL` | `INFO` | Runtime logging level. |
| `BATCH_MAX_WORKERS` | `2` | Max concurrent workers for batch parsing. |

## 🤝 Contributing

1. Fork the repository and create a feature branch.
2. Keep changes focused, with clear reasoning in commits.
3. Run backend tests and frontend lint/build checks before PR.
4. Include verification evidence (commands + outputs) in the PR description.
5. Open a pull request and respond to review feedback promptly.

## 📄 License

MIT

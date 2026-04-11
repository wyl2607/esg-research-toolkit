# ESG Research Toolkit

Open-source toolkit for corporate ESG analysis, combining PDF report parsing, EU Taxonomy compliance scoring, and renewable energy techno-economic modelling in a single FastAPI service.

## Overview

ESG Research Toolkit is designed for one practical outcome: assess a real company's ESG disclosures and evaluate the economics of its renewable energy projects with a reproducible, API-first workflow.

Current release status:

- Version: `v0.1.0`
- Repository: `https://github.com/wyl2607/esg-research-toolkit`
- Snapshot date: `2026-04-12`

## Core Modules

### 1. `report_parser`

Parses corporate PDF reports and converts unstructured disclosures into structured ESG data.

- Extracts text from uploaded PDF reports with `pdfplumber`
- Uses the OpenAI API to identify ESG metrics
- Persists structured results through SQLAlchemy ORM
- Returns normalized `CompanyESGData` objects for downstream scoring

### 2. `taxonomy_scorer`

Scores company data against the EU Taxonomy framework.

- Evaluates alignment across the 6 environmental objectives
- Applies Do No Significant Harm (`DNSH`) logic
- Uses Technical Screening Criteria (`TSC`) thresholds for supported activities
- Produces machine-readable reports and plain-text summaries
- Includes gap analysis with severity levels: `critical`, `high`, `medium`, `low`

### 3. `techno_economics`

Performs renewable energy project economics and scenario analysis.

- Computes Levelized Cost of Energy (`LCOE`)
- Computes Net Present Value (`NPV`), Internal Rate of Return (`IRR`), and payback metrics
- Runs CAPEX and OPEX sensitivity analysis
- Exposes benchmark LCOE ranges for selected technologies

## Quick Start

### Prerequisites

- Python `3.11+`
- An OpenAI API key

### Installation

```bash
git clone https://github.com/wyl2607/esg-research-toolkit.git
cd esg-research-toolkit

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
```

Set at least:

```env
OPENAI_API_KEY=your_openai_api_key_here
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
DATABASE_URL=sqlite:///./data/esg_toolkit.db
```

### Run The Service

```bash
uvicorn main:app --reload
```

Interactive API documentation:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Run Tests

```bash
pytest tests/ -v
```

## API Endpoints

### System

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/` | Service metadata and module list |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc |
| `GET` | `/openapi.json` | OpenAPI schema |

### Report Parser

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/report/upload` | Upload a PDF report and return structured `CompanyESGData` |
| `GET` | `/report/companies` | List stored company reports |
| `GET` | `/report/companies/{company_name}/{report_year}` | Retrieve a specific company report |

### Taxonomy Scorer

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/taxonomy/score` | Score a `CompanyESGData` payload against the EU Taxonomy |
| `POST` | `/taxonomy/report` | Generate a structured taxonomy report with gap analysis |
| `POST` | `/taxonomy/report/text` | Generate a plain-text taxonomy summary |
| `GET` | `/taxonomy/activities` | List supported EU Taxonomy activities |

### Techno Economics

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/techno/lcoe` | Calculate `LCOE`, `NPV`, and `IRR` |
| `POST` | `/techno/sensitivity` | Run CAPEX and OPEX sensitivity analysis |
| `GET` | `/techno/benchmarks` | Return benchmark LCOE ranges for selected technologies |

## Technology Stack

- Backend: FastAPI, Uvicorn
- Data validation: Pydantic v2
- Database: SQLAlchemy 2.0, SQLite
- AI extraction: OpenAI API
- PDF processing: pdfplumber
- Scientific computing: NumPy, SciPy
- Data utilities: pandas, openpyxl
- Reporting: ReportLab, python-docx
- Testing: pytest, pytest-asyncio

## Project Statistics

Project snapshot for `v0.1.0`:

| Metric | Value |
| --- | --- |
| Tracked files | 37 |
| Core modules | 3 |
| API endpoints | 15 |
| Automated tests | 19 |
| Recorded test pass rate | 100% |
| Python version | 3.11+ |

## Design Principles

- First-principles scope: only features that directly support ESG compliance analysis and renewable project evaluation
- API-first delivery: every core capability is exposed through documented HTTP endpoints
- Type safety: Pydantic schemas and explicit Python typing
- Modularity: report parsing, taxonomy scoring, and techno-economics remain separable but interoperable
- Test-backed development: core business logic is covered by automated tests

## Contributing

Contributions are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Keep changes small, testable, and aligned with the toolkit's first-principles scope.
4. Run linting and tests before opening a pull request.
5. Submit a pull request with a clear rationale and verification notes.

When contributing, prefer improvements that strengthen ESG analysis workflows, taxonomy scoring accuracy, or techno-economic modelling quality without adding unnecessary scope.

## License

This project is released under the MIT License.

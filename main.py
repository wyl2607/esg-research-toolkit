"""ESG Research Toolkit — FastAPI main entry point."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from sqlalchemy import text
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from benchmark.api import router as benchmark_router
from core.config import settings
from core.database import SessionLocal, init_db
from core.limiter import limiter
from core.models import health_payload as model_health_payload
from core.models import validate_models_startup
from core.schemas import CompanyESGData, HealthResponse, ModelsHealthResponse
from esg_frameworks.api import _SCORERS, router as frameworks_router
from esg_frameworks.storage import list_framework_results, save_framework_result
from report_parser.api import router as report_router
from report_parser.api import v1_router as report_v1_router
from report_parser.disclosures_api import router as disclosures_router
from report_parser.storage import get_report, save_report
from taxonomy_scorer.api import router as taxonomy_router
from techno_economics.api import router as techno_router

APP_VERSION = "0.3.0"
CONTRACT_TEST_MODE = os.getenv("ESG_CONTRACT_TEST_MODE") == "1"
DEFAULT_OPENAPI_SERVER_URL = os.getenv(
    "ESG_OPENAPI_SERVER_URL",
    "http://127.0.0.1:8001" if CONTRACT_TEST_MODE else "http://127.0.0.1:8000",
)

CONTRACT_TEST_EXCLUDED_OPERATIONS = {
    ("/report/upload", "post"),
    ("/report/upload/batch", "post"),
    ("/report/jobs/{batch_id}", "get"),
    ("/report/manual", "post"),
    ("/report/companies/{company_name}/{report_year}", "delete"),
    ("/report/companies/{company_name}/{report_year}/request-deletion", "post"),
    ("/report/companies/export/csv", "get"),
    ("/report/companies/export/xlsx", "get"),
    ("/taxonomy/report/pdf", "get"),
    ("/taxonomy/report", "get"),
    ("/frameworks/score", "get"),
    ("/frameworks/compare", "get"),
    ("/frameworks/compare/regional", "get"),
    ("/frameworks/results", "get"),
    ("/frameworks/results/{result_id}", "get"),
    ("/benchmarks/{industry_code}", "get"),
    ("/frameworks/cache/clear", "post"),
    ("/benchmarks/recompute", "post"),
}

COMPANY_DATA_EXAMPLE = {
    "company_name": "Contract Demo AG",
    "report_year": 2024,
    "reporting_period_label": "FY2024",
    "reporting_period_type": "annual",
    "source_document_type": "annual_report",
    "industry_code": "D35.11",
    "industry_sector": "Electricity production",
    "scope1_co2e_tonnes": 120.5,
    "scope2_co2e_tonnes": 88.2,
    "scope3_co2e_tonnes": 410.0,
    "energy_consumption_mwh": 15000.0,
    "renewable_energy_pct": 61.0,
    "water_usage_m3": 2400.0,
    "waste_recycled_pct": 76.5,
    "total_revenue_eur": 250000000.0,
    "taxonomy_aligned_revenue_pct": 32.0,
    "total_capex_eur": 90000000.0,
    "taxonomy_aligned_capex_pct": 41.0,
    "total_employees": 2400,
    "female_pct": 38.5,
    "primary_activities": ["solar_pv", "wind_onshore"],
    "evidence_summary": [
        {
            "metric": "taxonomy_aligned_revenue_pct",
            "source": "contract://demo/2024",
            "page": 14,
            "snippet": "Taxonomy-aligned revenue reached 32% in FY2024.",
            "source_type": "annual_report",
        }
    ],
}

MERGE_PREVIEW_EXAMPLE = {
    "documents": [
        {
            **COMPANY_DATA_EXAMPLE,
            "source_id": "contract://demo/2024/annual",
            "source_url": "https://example.com/contract-demo-2024-annual.pdf",
            "downloaded_at": "2026-04-16T00:00:00+00:00",
        },
        {
            **COMPANY_DATA_EXAMPLE,
            "source_id": "contract://demo/2024/sustainability",
            "source_document_type": "sustainability_report",
            "taxonomy_aligned_revenue_pct": 31.5,
            "source_url": "https://example.com/contract-demo-2024-sustainability.pdf",
            "downloaded_at": "2026-04-16T00:00:00+00:00",
        },
    ]
}

LCOE_INPUT_EXAMPLE = {
    "technology": "solar_pv",
    "capacity_mw": 100.0,
    "capex_eur_per_kw": 800.0,
    "opex_eur_per_kw_year": 15.0,
    "capacity_factor": 0.18,
    "lifetime_years": 25,
    "discount_rate": 0.07,
    "electricity_price_eur_per_mwh": 95.0,
    "currency": "EUR",
    "reference_fx_to_eur": 1.0,
}

SAF_INPUT_EXAMPLE = {
    "pathway": "HEFA",
    "region": "EU",
    "production_capacity_tonnes_year": 50000,
    "capex_eur_per_tonne_year": 1800.0,
    "lifetime_years": 20,
    "discount_rate": 0.08,
    "feedstock_cost_eur_per_tonne": 600.0,
    "feedstock_to_saf_ratio": 1.25,
    "opex_eur_per_tonne": 250.0,
    "policy_credit_eur_per_tonne": 0.0,
    "jet_fuel_price_eur_per_litre": 0.60,
    "saf_density_kg_per_litre": 0.800,
    "currency": "EUR",
    "reference_fx_to_eur": 1.0,
}

EXAMPLE_PARAMETERS = {
    "company_name": "Contract Demo AG",
    "report_year": 2024,
    "industry_code": "D35.11",
    "framework": "eu_taxonomy",
    "batch_id": "contract-batch-1",
    "result_id": 1,
    "company_report_id": 1,
}

STANDARD_ERROR_RESPONSES: dict[tuple[str, str, str], dict[str, str]] = {
    ("/report/jobs/{batch_id}", "get", "404"): {"description": "Batch not found."},
    ("/report/companies/{company_name}/{report_year}", "get", "404"): {"description": "Report not found."},
    ("/report/companies/{company_name}/{report_year}", "delete", "404"): {"description": "Report not found."},
    ("/report/{company_report_id}/audit-trail", "get", "404"): {"description": "Report not found."},
    ("/report/companies/{company_name}/history", "get", "404"): {"description": "No reports found for the company."},
    ("/report/companies/{company_name}/profile", "get", "404"): {"description": "No reports found for the company."},
    (
        "/report/companies/{company_name}/{report_year}/request-deletion",
        "post",
        "404",
    ): {"description": "Report not found."},
    ("/taxonomy/report", "get", "404"): {"description": "Stored report not found."},
    ("/taxonomy/report/pdf", "get", "404"): {"description": "Stored report not found."},
    ("/frameworks/score", "get", "400"): {"description": "Unknown framework identifier."},
    ("/frameworks/score", "get", "404"): {"description": "Stored report not found."},
    ("/frameworks/compare", "get", "404"): {"description": "Stored report not found."},
    ("/frameworks/compare/regional", "get", "404"): {"description": "Stored report not found."},
    ("/frameworks/results/{result_id}", "get", "404"): {"description": "Framework analysis result not found."},
    ("/report/upload", "post", "400"): {"description": "Invalid PDF upload."},
    ("/report/upload", "post", "413"): {"description": "Uploaded PDF exceeds the size limit."},
    ("/report/upload", "post", "415"): {"description": "Uploaded file is not recognized as a PDF."},
    ("/report/upload", "post", "429"): {"description": "Upload rate limit exceeded."},
    ("/report/upload/batch", "post", "400"): {"description": "Invalid batch upload request."},
    ("/report/upload/batch", "post", "413"): {"description": "One or more PDFs exceed the size limit."},
    ("/report/upload/batch", "post", "415"): {"description": "One or more uploaded files are not recognized as PDFs."},
    ("/report/upload/batch", "post", "429"): {"description": "Upload rate limit exceeded."},
    ("/report/merge/preview", "post", "400"): {"description": "Merge preview payload is invalid."},
}

REQUEST_BODY_EXAMPLES = {
    ("/taxonomy/score", "post"): COMPANY_DATA_EXAMPLE,
    ("/taxonomy/report", "post"): COMPANY_DATA_EXAMPLE,
    ("/taxonomy/report/text", "post"): COMPANY_DATA_EXAMPLE,
    ("/techno/lcoe", "post"): LCOE_INPUT_EXAMPLE,
    ("/techno/sensitivity", "post"): LCOE_INPUT_EXAMPLE,
    ("/techno/saf", "post"): SAF_INPUT_EXAMPLE,
    ("/frameworks/score/upload", "post"): COMPANY_DATA_EXAMPLE,
    ("/report/merge/preview", "post"): MERGE_PREVIEW_EXAMPLE,
}


def _cors_allowed_origins() -> list[str]:
    configured_origins = os.getenv("CORS_ALLOWED_ORIGINS", settings.cors_allowed_origins)
    return [origin.strip() for origin in configured_origins.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    validate_models_startup()
    if CONTRACT_TEST_MODE:
        _seed_contract_test_data()
    yield


app = FastAPI(
    title="ESG Research Toolkit",
    description=(
        "Open-source toolkit for corporate ESG report analysis, EU Taxonomy "
        "compliance scoring, and renewable energy techno-economic analysis "
        "(LCOE/NPV/IRR)."
    ),
    version=APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allowed_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SlowAPIMiddleware)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def _seed_contract_test_data() -> None:
    """Create deterministic records for OpenAPI examples and contract fuzzing."""
    db = SessionLocal()
    try:
        first_report = save_report(
            db,
            CompanyESGData(**COMPANY_DATA_EXAMPLE),
            pdf_filename="contract-demo-2024.pdf",
            file_hash="contract-demo-2024-hash",
            downloaded_at=datetime.now(timezone.utc),
            reporting_period_label="FY2024",
            reporting_period_type="annual",
            source_document_type="annual_report",
            evidence_summary=COMPANY_DATA_EXAMPLE["evidence_summary"],
        )
        previous_year_payload = {
            **COMPANY_DATA_EXAMPLE,
            "report_year": 2023,
            "reporting_period_label": "FY2023",
            "scope1_co2e_tonnes": 132.0,
            "scope2_co2e_tonnes": 95.0,
            "renewable_energy_pct": 58.0,
            "taxonomy_aligned_revenue_pct": 28.0,
            "taxonomy_aligned_capex_pct": 36.0,
        }
        save_report(
            db,
            CompanyESGData(**previous_year_payload),
            pdf_filename="contract-demo-2023.pdf",
            file_hash="contract-demo-2023-hash",
            downloaded_at=datetime.now(timezone.utc),
            reporting_period_label="FY2023",
            reporting_period_type="annual",
            source_document_type="annual_report",
            evidence_summary=COMPANY_DATA_EXAMPLE["evidence_summary"],
        )

        if not list_framework_results(
            db,
            company_name=COMPANY_DATA_EXAMPLE["company_name"],
            report_year=COMPANY_DATA_EXAMPLE["report_year"],
        ):
            report = get_report(
                db,
                COMPANY_DATA_EXAMPLE["company_name"],
                COMPANY_DATA_EXAMPLE["report_year"],
            )
            if report is not None:
                company_data = CompanyESGData.model_validate(
                    {
                        **COMPANY_DATA_EXAMPLE,
                        "company_name": report.company_name,
                    }
                )
                for scorer in _SCORERS.values():
                    save_framework_result(db, scorer(company_data))

        db.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS extraction_runs (
                id INTEGER PRIMARY KEY,
                company_report_id INTEGER,
                file_hash TEXT,
                run_kind TEXT,
                model TEXT,
                prompt_hash TEXT,
                raw_response TEXT,
                verdict TEXT,
                applied BOOLEAN,
                notes TEXT,
                created_at TEXT
            )
            """
            )
        )
        db.execute(text("DELETE FROM extraction_runs"))
        db.execute(
            text(
                """
            INSERT INTO extraction_runs (
                id, company_report_id, file_hash, run_kind, model, verdict, applied, notes, created_at
            ) VALUES (
                :id, :company_report_id, :file_hash, :run_kind, :model, :verdict, :applied, :notes, :created_at
            )
            """
            ),
            {
                "id": 1,
                "company_report_id": first_report.id,
                "file_hash": first_report.file_hash,
                "run_kind": "contract_seed",
                "model": "gpt-5.4-mini",
                "verdict": "accepted",
                "applied": True,
                "notes": "Seeded for Schemathesis contract testing.",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        db.commit()

        from benchmark.compute import recompute_industry_benchmarks

        recompute_industry_benchmarks(db)
    finally:
        db.close()


def _prune_contract_test_schema(schema: dict[str, Any]) -> None:
    for path, method in CONTRACT_TEST_EXCLUDED_OPERATIONS:
        path_item = schema.get("paths", {}).get(path)
        if not path_item:
            continue
        path_item.pop(method, None)
        if not path_item:
            schema["paths"].pop(path, None)


def _apply_error_responses(schema: dict[str, Any]) -> None:
    for (path, method, status_code), response in STANDARD_ERROR_RESPONSES.items():
        operation = schema.get("paths", {}).get(path, {}).get(method)
        if operation is not None:
            operation.setdefault("responses", {}).setdefault(status_code, response)


def _apply_examples(schema: dict[str, Any]) -> None:
    for path, path_item in schema.get("paths", {}).items():
        for method, operation in path_item.items():
            for parameter in operation.get("parameters", []):
                example_value = EXAMPLE_PARAMETERS.get(parameter.get("name"))
                if example_value is not None:
                    parameter.setdefault("schema", {})["example"] = example_value

            request_example = REQUEST_BODY_EXAMPLES.get((path, method))
            if request_example is not None:
                content = operation.get("requestBody", {}).get("content", {})
                for body in content.values():
                    body.setdefault("schema", {})
                    body.setdefault("examples", {})
                    body["examples"]["contractSeed"] = {
                        "summary": "Seeded contract example",
                        "value": request_example,
                    }


def custom_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["servers"] = [{"url": DEFAULT_OPENAPI_SERVER_URL}]
    schema["info"]["x-contract-test-mode"] = CONTRACT_TEST_MODE

    _apply_error_responses(schema)
    _apply_examples(schema)

    if CONTRACT_TEST_MODE:
        _prune_contract_test_schema(schema)

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


app.include_router(report_router)
app.include_router(report_v1_router)
app.include_router(disclosures_router)
app.include_router(taxonomy_router)
app.include_router(techno_router)
app.include_router(frameworks_router)
app.include_router(benchmark_router)


@app.get("/")
def root() -> dict[str, str | list[str]]:
    return {
        "name": "ESG Research Toolkit",
        "version": APP_VERSION,
        "modules": [
            "report_parser",
            "taxonomy_scorer",
            "techno_economics",
            "esg_frameworks",
            "benchmark",
        ],
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return {"status": "ok"}


@app.get("/health/models", response_model=ModelsHealthResponse)
def health_models() -> dict[str, object]:
    return model_health_payload()

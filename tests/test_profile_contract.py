import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from core.database import Base, get_db
from core.schemas import CompanyESGData
from esg_frameworks.schemas import DimensionScore, FrameworkScoreResult
from esg_frameworks.storage import save_framework_result
from main import app
from report_parser.storage import save_report


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "company_profile_v1"


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def _seed_profile_contract_data(db_session: Session) -> None:
    save_report(
        db_session,
        CompanyESGData(
            company_name="V1 Contract Corp",
            report_year=2023,
            scope1_co2e_tonnes=140.0,
            scope2_co2e_tonnes=88.0,
            energy_consumption_mwh=610.0,
            renewable_energy_pct=31.0,
            total_employees=980,
            female_pct=44.0,
            primary_activities=["solar_pv"],
        ),
        pdf_filename="v1-contract-2023.pdf",
        source_url="https://example.com/v1-contract-2023.pdf",
        file_hash="hash-v1-contract-2023",
        downloaded_at=datetime(2024, 2, 1, 10, 0, tzinfo=timezone.utc),
        reporting_period_label="FY2023",
        reporting_period_type="annual",
        source_document_type="annual_report",
        evidence_summary=[
            {
                "metric": "renewable_energy_pct",
                "source": "V1 Contract Corp Annual Report 2023",
                "source_doc_id": "hash-v1-contract-2023",
                "page": 9,
                "char_range": [120, 136],
                "snippet": "Renewable electricity share reached 31%.",
                "extraction_method": "regex",
                "confidence": 0.9,
                "source_type": "pdf",
                "source_url": "https://example.com/v1-contract-2023.pdf",
                "file_hash": "hash-v1-contract-2023",
            }
        ],
    )
    save_report(
        db_session,
        CompanyESGData(
            company_name="V1 Contract Corp",
            report_year=2024,
            scope1_co2e_tonnes=120.0,
            scope2_co2e_tonnes=74.0,
            scope3_co2e_tonnes=980.0,
            energy_consumption_mwh=540.0,
            renewable_energy_pct=45.0,
            water_usage_m3=12000.0,
            waste_recycled_pct=62.0,
            taxonomy_aligned_revenue_pct=28.0,
            taxonomy_aligned_capex_pct=35.0,
            total_employees=1020,
            female_pct=48.0,
            primary_activities=["solar_pv", "battery_storage"],
        ),
        pdf_filename="v1-contract-2024.pdf",
        source_url="https://example.com/v1-contract-2024.pdf",
        file_hash="hash-v1-contract-2024",
        downloaded_at=datetime(2025, 2, 1, 10, 0, tzinfo=timezone.utc),
        reporting_period_label="FY2024",
        reporting_period_type="annual",
        source_document_type="sustainability_report",
        evidence_summary=[
            {
                "metric": "scope1_co2e_tonnes",
                "source": "V1 Contract Corp Sustainability Report 2024",
                "source_doc_id": "hash-v1-contract-2024",
                "page": 7,
                "char_range": [120, 138],
                "snippet": "Scope 1 emissions decreased to 120 tCO2e.",
                "extraction_method": "llm",
                "confidence": 0.88,
                "source_type": "pdf",
                "source_url": "https://example.com/v1-contract-2024.pdf",
                "file_hash": "hash-v1-contract-2024",
            },
            {
                "metric": "renewable_energy_pct",
                "source": "V1 Contract Corp Sustainability Report 2024",
                "source_doc_id": "hash-v1-contract-2024",
                "page": 12,
                "char_range": [420, 441],
                "snippet": "Renewable electricity share increased to 45%.",
                "extraction_method": "regex",
                "confidence": 0.91,
                "source_type": "pdf",
                "source_url": "https://example.com/v1-contract-2024.pdf",
                "file_hash": "hash-v1-contract-2024",
            },
            {
                "metric": "female_pct",
                "source": "V1 Contract Corp Sustainability Report 2024",
                "source_doc_id": "hash-v1-contract-2024",
                "page": 18,
                "char_range": [88, 104],
                "snippet": "Female representation reached 48%.",
                "extraction_method": "llm",
                "confidence": 0.8,
                "source_type": "pdf",
                "source_url": "https://example.com/v1-contract-2024.pdf",
                "file_hash": "hash-v1-contract-2024",
            },
        ],
    )

    framework_result = save_framework_result(
        db_session,
        FrameworkScoreResult(
            framework="EU Taxonomy 2020",
            framework_id="eu_taxonomy",
            framework_version="2020/852",
            company_name="V1 Contract Corp",
            report_year=2024,
            total_score=0.78,
            grade="B",
            dimensions=[
                DimensionScore(name="Climate", score=0.78, weight=1.0, disclosed=8, total=10)
            ],
            gaps=[],
            recommendations=["Increase renewable energy share beyond 50%."],
            coverage_pct=80.0,
        ),
        framework_version="2020/852",
    )
    framework_result.created_at = datetime(2025, 2, 1, 11, 0, tzinfo=timezone.utc)
    db_session.commit()
    db_session.refresh(framework_result)


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text())


def test_company_profile_v1_matches_golden_fixture_and_legacy_alias_has_deprecation_header(
    client: TestClient,
    db_session: Session,
) -> None:
    _seed_profile_contract_data(db_session)

    v1_response = client.get("/api/v1/companies/V1%20Contract%20Corp/profile")
    assert v1_response.status_code == 200
    assert "Deprecation" not in v1_response.headers

    payload = v1_response.json()
    assert payload == _load_fixture("profile_response.json")

    legacy_response = client.get("/report/companies/V1%20Contract%20Corp/profile")
    assert legacy_response.status_code == 200
    assert legacy_response.headers["Deprecation"] == "true"
    assert "/api/v1/companies/V1 Contract Corp/profile" in legacy_response.headers["Link"]
    assert legacy_response.json() == payload


def test_company_profile_v1_openapi_exposes_typed_contract(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    assert "/api/v1/companies/{company_name}/profile" in schema["paths"]
    responses = schema["paths"]["/api/v1/companies/{company_name}/profile"]["get"]["responses"]
    response_schema = responses["200"]
    assert response_schema["content"]["application/json"]["schema"]["$ref"].endswith("CompanyProfileV1Response")
    assert "404" in responses
    evidence_schema = schema["components"]["schemas"]["Evidence"]
    assert set(evidence_schema["properties"]) >= {
        "source_doc_id",
        "page",
        "char_range",
        "snippet",
        "extraction_method",
        "confidence",
    }


def test_company_profile_v1_scored_metrics_carry_evidence_and_normalized_period(
    client: TestClient,
    db_session: Session,
) -> None:
    _seed_profile_contract_data(db_session)

    payload = client.get("/api/v1/companies/V1%20Contract%20Corp/profile").json()
    renewable_metric = payload["scored_metrics"]["renewable_energy_pct"]

    assert renewable_metric["value"] == 45.0
    assert renewable_metric["evidence"]["source_doc_id"] == "hash-v1-contract-2024"
    assert renewable_metric["evidence"]["page"] == 12
    assert renewable_metric["period"] == {
        "fiscal_year": 2024,
        "reporting_standard": "sustainability_report",
        "period_start": "2024-01-01",
        "period_end": "2024-12-31",
    }
    assert any(
        mapping["framework_id"] == "eu_taxonomy"
        for mapping in renewable_metric["framework_mappings"]
    )

    for metric_name, metric_payload in payload["scored_metrics"].items():
        if metric_payload["value"] in (None, []):
            continue
        assert metric_payload["evidence"] is not None, metric_name

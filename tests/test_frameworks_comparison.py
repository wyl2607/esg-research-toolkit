from __future__ import annotations

from collections.abc import Generator
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from core.database import get_db
from core.schemas import CompanyESGData
from esg_frameworks.comparison import build_comparison
from esg_frameworks.schemas import DimensionScore, FrameworkScoreResult
from esg_frameworks.storage import list_framework_results
from main import app
from report_parser.storage import save_report


def _make_result(framework_id: str, framework: str, total_score: float, grade: str) -> FrameworkScoreResult:
    return FrameworkScoreResult(
        framework=framework,
        framework_id=framework_id,
        company_name="Example Corp",
        report_year=2024,
        total_score=total_score,
        grade=grade,
        dimensions=[
            DimensionScore(name="Emissions", score=total_score, weight=1.0, disclosed=1, total=1, gaps=[]),
        ],
        gaps=[],
        recommendations=[],
        coverage_pct=80.0,
    )


@pytest.fixture
def framework_db_session_factory() -> Generator[sessionmaker, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    try:
        yield testing_session_local
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def _seed_company_report(session: Session) -> None:
    save_report(
        session,
        CompanyESGData(
            company_name="CATL",
            report_year=2024,
            scope1_co2e_tonnes=100,
            scope2_co2e_tonnes=80,
            renewable_energy_pct=60,
            total_employees=1000,
            female_pct=37.5,
            primary_activities=["solar_pv"],
        ),
        pdf_filename="catl-2024.pdf",
    )


def test_build_comparison_keeps_eu_cn_us_groups() -> None:
    data = CompanyESGData(
        company_name="Example Corp",
        report_year=2024,
        scope1_co2e_tonnes=10,
        scope2_co2e_tonnes=5,
        scope3_co2e_tonnes=None,
        total_employees=100,
        female_pct=45,
    )
    results = [
        _make_result("eu_taxonomy", "EU Taxonomy", 0.72, "B"),
        _make_result("csrc_2023", "China CSRC 2023", 0.61, "B"),
    ]

    report = build_comparison(data, results)

    assert {group.region for group in report.regional_groups} == {"EU", "CN", "US"}
    assert len(report.cross_matrix) == 3
    assert report.company_name == "Example Corp"


def test_compare_regional_endpoint_returns_expected_shape(monkeypatch) -> None:
    import esg_frameworks.api as frameworks_api

    sample = CompanyESGData(
        company_name="CATL",
        report_year=2024,
        scope1_co2e_tonnes=100,
        scope2_co2e_tonnes=80,
        scope3_co2e_tonnes=None,
        renewable_energy_pct=60,
        total_employees=1000,
        female_pct=37.5,
        primary_activities=["solar_pv"],
    )

    monkeypatch.setattr(frameworks_api, "_load_company", lambda db, company_name, report_year: sample)
    monkeypatch.setattr(frameworks_api, "save_framework_result", lambda *args, **kwargs: None)
    app.dependency_overrides[get_db] = lambda: None

    client = TestClient(app)
    response = client.get(
        "/frameworks/compare/regional",
        params={"company_name": "CATL", "report_year": 2024},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["company_name"] == "CATL"
    assert len(body["cross_matrix"]) == 3
    assert {group["region"] for group in body["regional_groups"]} == {"EU", "CN", "US"}

    app.dependency_overrides.clear()


def test_compare_endpoint_uses_cache_and_can_clear(monkeypatch) -> None:
    import esg_frameworks.api as frameworks_api

    sample = CompanyESGData(
        company_name="CATL",
        report_year=2024,
        scope1_co2e_tonnes=100,
        scope2_co2e_tonnes=80,
        scope3_co2e_tonnes=None,
        renewable_energy_pct=60,
        total_employees=1000,
        female_pct=37.5,
        primary_activities=["solar_pv"],
    )
    call_count = {"count": 0}

    def fake_scorer(data: CompanyESGData) -> FrameworkScoreResult:
        call_count["count"] += 1
        return _make_result("eu_taxonomy", "EU Taxonomy", 0.72, "B")

    monkeypatch.setattr(frameworks_api, "_load_company", lambda db, company_name, report_year: sample)
    monkeypatch.setattr(frameworks_api, "save_framework_result", lambda *args, **kwargs: None)
    monkeypatch.setattr(frameworks_api, "_SCORERS", {"eu_taxonomy": fake_scorer})
    frameworks_api._score_cache.clear()
    app.dependency_overrides[get_db] = lambda: None
    client = TestClient(app)

    params = {"company_name": "CATL", "report_year": 2024}
    first = client.get("/frameworks/compare", params=params)
    second = client.get("/frameworks/compare", params=params)
    assert first.status_code == 200
    assert second.status_code == 200
    assert call_count["count"] == 1

    clear_response = client.post("/frameworks/cache/clear")
    assert clear_response.status_code == 200
    assert clear_response.json()["status"] == "cache cleared"

    third = client.get("/frameworks/compare", params=params)
    assert third.status_code == 200
    assert call_count["count"] == 2

    app.dependency_overrides.clear()


def test_score_endpoint_persists_idempotently_for_identical_payloads(
    framework_db_session_factory: sessionmaker,
    monkeypatch,
) -> None:
    import esg_frameworks.api as frameworks_api

    with framework_db_session_factory() as session:
        _seed_company_report(session)

    def override_get_db():
        db = framework_db_session_factory()
        try:
            yield db
        finally:
            db.close()

    def fake_scorer(data: CompanyESGData) -> FrameworkScoreResult:
        return _make_result("eu_taxonomy", "EU Taxonomy", 0.72, "B").model_copy(
            update={
                "company_name": data.company_name,
                "report_year": data.report_year,
                "framework_version": "2020/852",
            }
        )

    monkeypatch.setattr(frameworks_api, "_SCORERS", {"eu_taxonomy": fake_scorer})
    frameworks_api._score_cache.clear()
    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    params = {"company_name": "CATL", "report_year": 2024, "framework": "eu_taxonomy"}
    first = client.get("/frameworks/score", params=params)
    second = client.get("/frameworks/score", params=params)

    assert first.status_code == 200
    assert second.status_code == 200

    with framework_db_session_factory() as session:
        rows = list_framework_results(session, company_name="CATL", report_year=2024)

    assert len(rows) == 1
    assert rows[0].framework_id == "eu_taxonomy"
    assert rows[0].framework_version == "2020/852"


def test_compare_endpoint_allows_new_row_when_payload_changes(
    framework_db_session_factory: sessionmaker,
    monkeypatch,
) -> None:
    import esg_frameworks.api as frameworks_api

    with framework_db_session_factory() as session:
        _seed_company_report(session)

    def override_get_db():
        db = framework_db_session_factory()
        try:
            yield db
        finally:
            db.close()

    score_state = {"score": 0.72, "grade": "B"}

    def fake_scorer(data: CompanyESGData) -> FrameworkScoreResult:
        return _make_result("eu_taxonomy", "EU Taxonomy", score_state["score"], score_state["grade"]).model_copy(
            update={
                "company_name": data.company_name,
                "report_year": data.report_year,
                "framework_version": "2020/852",
            }
        )

    monkeypatch.setattr(frameworks_api, "_SCORERS", {"eu_taxonomy": fake_scorer})
    frameworks_api._score_cache.clear()
    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    params = {"company_name": "CATL", "report_year": 2024}
    first = client.get("/frameworks/compare", params=params)
    assert first.status_code == 200

    clear_response = client.post("/frameworks/cache/clear")
    assert clear_response.status_code == 200

    score_state["score"] = 0.81
    score_state["grade"] = "A"
    second = client.get("/frameworks/compare", params=params)
    assert second.status_code == 200

    with framework_db_session_factory() as session:
        rows = list_framework_results(session, company_name="CATL", report_year=2024)

    assert len(rows) == 2
    assert {row.grade for row in rows} == {"A", "B"}
    assert {row.framework_version for row in rows} == {"2020/852"}


def test_taxonomy_report_get_uses_cache(monkeypatch) -> None:
    import core.database as core_database
    import report_parser.storage as report_storage
    import taxonomy_scorer.api as taxonomy_api

    class _DummyDb:
        pass

    sample_record = SimpleNamespace(
        company_name="CATL",
        report_year=2024,
        primary_activities='["solar_pv"]',
    )
    score_calls = {"count": 0}

    def fake_get_db():
        yield _DummyDb()

    def fake_score_company(data: CompanyESGData):
        score_calls["count"] += 1
        return SimpleNamespace()

    monkeypatch.setattr(core_database, "get_db", fake_get_db)
    monkeypatch.setattr(report_storage, "get_report", lambda db, company_name, report_year: sample_record)
    monkeypatch.setattr(taxonomy_api, "score_company", fake_score_company)
    monkeypatch.setattr(taxonomy_api, "analyze_gaps", lambda data, result: [])
    monkeypatch.setattr(
        taxonomy_api,
        "generate_json_report",
        lambda data, result, gaps: {"company_name": data.company_name, "report_year": data.report_year},
    )
    taxonomy_api._report_cache.clear()

    client = TestClient(app)
    params = {"company_name": "CATL", "report_year": 2024}
    first = client.get("/taxonomy/report", params=params)
    second = client.get("/taxonomy/report", params=params)

    assert first.status_code == 200
    assert second.status_code == 200
    assert score_calls["count"] == 1


def test_taxonomy_report_rejects_invalid_query_bounds() -> None:
    client = TestClient(app)

    response = client.get(
        "/taxonomy/report",
        params={"company_name": "", "report_year": 9223372036854775808},
    )

    assert response.status_code == 422


def test_framework_results_endpoints_reject_out_of_range_identifiers() -> None:
    client = TestClient(app)

    list_response = client.get(
        "/frameworks/results",
        params={"company_name": "", "report_year": 9223372036854775808},
    )
    by_id_response = client.get("/frameworks/results/9223372036854775808")
    regional_response = client.get(
        "/frameworks/compare/regional",
        params={"company_name": "", "report_year": 9223372036854775808},
    )

    assert list_response.status_code == 422
    assert by_id_response.status_code == 422
    assert regional_response.status_code == 422

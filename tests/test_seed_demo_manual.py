from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base, get_db
from core.schemas import ManualReportInput
from esg_frameworks.api import _score_cache, router as frameworks_router
from esg_frameworks.storage import list_framework_results
from report_parser.api import router as report_router
from scripts.seed_demo_manual import demo_records, filter_demo_records, main, seed_demo_manual


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def _demo_app(db_session: Session) -> FastAPI:
    app = FastAPI()
    app.include_router(report_router)
    app.include_router(frameworks_router)
    app.dependency_overrides[get_db] = lambda: db_session
    return app


def test_demo_records_validate_as_manual_report_inputs() -> None:
    records = demo_records()

    assert len(records) == 5
    assert {
        (record.payload.company_name, record.payload.report_year)
        for record in records
    } == {
        ("Demo Utility Grid AG", 2022),
        ("Demo Utility Grid AG", 2023),
        ("Demo Utility Grid AG", 2024),
        ("Demo Battery Materials SE", 2023),
        ("Demo Battery Materials SE", 2024),
    }

    for record in records:
        payload = ManualReportInput.model_validate(record.payload.model_dump())
        assert payload.reporting_period_label == f"FY {payload.report_year}"
        assert payload.reporting_period_type == "annual"
        assert payload.source_url and payload.source_url.startswith("https://demo.local/disclosures/")
        assert payload.source_document_type in {
            "sustainability_report",
            "annual_sustainability_report",
        }
        assert {item["metric"] for item in payload.evidence_summary} >= {
            "scope1_co2e_tonnes",
            "renewable_energy_pct",
            "taxonomy_aligned_revenue_pct",
            "total_employees",
        }
        assert all(item["extraction_method"] == "demo_manual_seed" for item in payload.evidence_summary)


def test_filter_demo_records_supports_slug_company_and_only_filters() -> None:
    records = demo_records()

    assert [record.slug for record in filter_demo_records(records, slugs=["demo-utility-grid-ag-2024"])] == [
        "demo-utility-grid-ag-2024"
    ]
    assert [
        record.payload.report_year
        for record in filter_demo_records(records, company_names=["Demo Utility Grid AG"])
    ] == [2022, 2023, 2024]
    assert {
        record.slug
        for record in filter_demo_records(
            records,
            only_filters=["demo-utility-grid-ag-2024, Demo Battery Materials SE"],
        )
    } == {
        "demo-utility-grid-ag-2024",
        "demo-battery-materials-se-2023",
        "demo-battery-materials-se-2024",
    }


def test_main_dry_run_does_not_call_network(monkeypatch: pytest.MonkeyPatch) -> None:
    class _NoNetworkClient:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            raise AssertionError("httpx.Client should not be used in --dry-run")

    monkeypatch.setattr("scripts.seed_demo_manual.httpx.Client", _NoNetworkClient)

    exit_code = main(["--dry-run", "--only", "demo-utility-grid-ag-2024"])

    assert exit_code == 0


def test_seed_demo_manual_posts_records_and_profile_exposes_evidence_and_frameworks(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _demo_app(db_session)
    _score_cache.clear()

    class _ApiClient:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            self.client = TestClient(app)

        def __enter__(self):
            self.client.__enter__()
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
            self.client.__exit__(exc_type, exc, tb)

        def post(self, url: str, *, json: dict):
            assert url == "http://testserver/report/manual"
            return self.client.post("/report/manual", json=json)

        def get(self, url: str):
            assert url.startswith("http://testserver/frameworks/compare?")
            path_and_query = url.removeprefix("http://testserver")
            return self.client.get(path_and_query)

    monkeypatch.setattr("scripts.seed_demo_manual.httpx.Client", _ApiClient)

    summary = seed_demo_manual(
        api_base="http://testserver",
        only_filters=["Demo Utility Grid AG"],
        score_frameworks=True,
    )

    assert summary["selected"] == 3
    assert summary["posted"] == 3
    assert summary["framework_compares"] == 1

    with TestClient(app) as client:
        profile_response = client.get("/report/companies/Demo Utility Grid AG/profile")

    assert profile_response.status_code == 200
    profile = profile_response.json()
    assert profile["years_available"] == [2022, 2023, 2024]
    assert [period["period"]["label"] for period in profile["periods"]] == ["FY 2022", "FY 2023", "FY 2024"]
    assert profile["latest_period"]["source_document_type"] == "sustainability_report"
    assert profile["latest_sources"][0]["source_url"].startswith(
        "https://demo.local/disclosures/demo-utility-grid-ag/2024"
    )
    assert {item["metric"] for item in profile["evidence_anchors"]} >= {
        "scope1_co2e_tonnes",
        "renewable_energy_pct",
        "taxonomy_aligned_revenue_pct",
        "total_employees",
    }
    assert len(profile["latest_period"]["framework_metadata"]) >= 1

    rows = list_framework_results(
        db_session,
        company_name="Demo Utility Grid AG",
        report_year=2024,
    )
    assert {row.framework_id for row in rows} >= {"eu_taxonomy", "csrc_2023", "csrd"}

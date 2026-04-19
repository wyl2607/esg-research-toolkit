from __future__ import annotations

from collections.abc import Generator
from urllib.parse import quote

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base, get_db
from core.schemas import CompanyESGData
from esg_frameworks.storage import FrameworkAnalysisResult  # noqa: F401 - register table on Base metadata
from report_parser import disclosures_api
from report_parser.api import router as report_router
from report_parser.disclosures_api import router as disclosures_router
from report_parser.storage import save_report, update_pending_disclosure_payload
from scripts.seed_data.backfill_via_disclosures import BACKFILL_TARGETS, run_backfill


@pytest.fixture
def seeded_backfill_client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db_session: Session = testing_session_local()

    app = FastAPI()
    app.include_router(report_router)
    app.include_router(disclosures_router)
    app.dependency_overrides[get_db] = lambda: db_session

    distinct_companies = sorted({company_name for company_name, _ in BACKFILL_TARGETS})
    for company_name in distinct_companies:
        save_report(
            db_session,
            CompanyESGData(
                company_name=company_name,
                report_year=2024,
                source_document_type="sustainability_report",
                scope1_co2e_tonnes=100.0,
                scope2_co2e_tonnes=80.0,
                renewable_energy_pct=35.0,
                total_employees=1000,
                primary_activities=["manufacturing"],
            ),
            source_url=f"https://example.com/{quote(company_name, safe='').lower()}-2024.pdf",
        )

    monkeypatch.setattr(disclosures_api, "_is_pytest_mode", lambda: False)

    def _fake_run_fetch_pipeline(
        *,
        pending_id: int,
        company_name: str,
        report_year: int,
        source_type: str,
        source_hint: str,
        source_hints: list[str],
        source_url: str,
    ) -> None:
        payload = CompanyESGData(
            company_name=company_name,
            report_year=report_year,
            source_document_type="sustainability_report",
            scope1_co2e_tonnes=float(report_year),
            scope2_co2e_tonnes=float(report_year) / 2.0,
            renewable_energy_pct=40.0 + float(report_year % 10),
            total_employees=900 + (report_year % 100),
            primary_activities=["renewables"],
            evidence_summary=[
                {
                    "metric": "auto_disclosure_fetch",
                    "source_url": source_url,
                    "source_type": source_type,
                    "source_hint": source_hint,
                    "source_hints": source_hints,
                    "snippet": "test-ready",
                }
            ],
        ).model_dump(mode="json")
        update_pending_disclosure_payload(
            db_session,
            pending_id=pending_id,
            extracted_payload=payload,
            review_note="fetch_succeeded",
        )

    monkeypatch.setattr(disclosures_api, "_run_fetch_pipeline", _fake_run_fetch_pipeline)

    try:
        with TestClient(app) as client:
            yield client
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


def test_backfill_via_disclosures_reaches_three_year_history_for_at_least_five_companies(
    seeded_backfill_client: TestClient,
) -> None:
    results, coverage = run_backfill(
        seeded_backfill_client,
        targets=BACKFILL_TARGETS,
        source_hints=["company_site"],
        poll_timeout_seconds=2.0,
        poll_interval_seconds=0.0,
    )

    statuses = {row.status for row in results}
    assert statuses.issubset({"approved", "exists"})

    qualified = [company_name for company_name, years in coverage.items() if years >= 3]
    assert len(qualified) >= 5

    for company_name in qualified[:5]:
        history_response = seeded_backfill_client.get(f"/report/companies/{quote(company_name, safe='')}/history")
        assert history_response.status_code == 200
        trend = history_response.json().get("trend", [])
        assert isinstance(trend, list)
        assert len(trend) >= 3

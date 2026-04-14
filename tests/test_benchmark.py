from collections.abc import Generator

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from benchmark.compute import recompute_industry_benchmarks
from benchmark.models import IndustryBenchmark
from benchmark.percentiles import five_point_summary, percentile
from core.database import Base, get_db
from main import app
from report_parser.storage import CompanyReport


@pytest.fixture
def benchmark_db_session_factory() -> Generator[sessionmaker, None, None]:
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


def test_percentile_basic() -> None:
    assert percentile([], 0.5) is None
    assert percentile([5.0], 0.5) == 5.0
    assert percentile([1.0, 2.0, 3.0, 4.0, 5.0], 0.5) == 3.0
    summary = five_point_summary([10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
    assert summary["p50"] == 55.0
    assert summary["p10"] < summary["p50"] < summary["p90"]


def test_percentile_skips_none() -> None:
    summary = five_point_summary([1.0, None, 2.0, float("nan"), 3.0])
    assert summary["p50"] == 2.0


def test_recompute_industry_benchmarks_end_to_end(benchmark_db_session_factory: sessionmaker) -> None:
    with benchmark_db_session_factory() as db:
        db.add_all(
            [
                CompanyReport(
                    company_name=f"Utility {i}",
                    report_year=2024,
                    industry_code="D35.11",
                    scope1_co2e_tonnes=float(value),
                )
                for i, value in enumerate([100, 200, 300, 400, 500], start=1)
            ]
        )
        db.commit()

        summary = recompute_industry_benchmarks(db)
        row = (
            db.query(IndustryBenchmark)
            .filter(
                IndustryBenchmark.industry_code == "D35.11",
                IndustryBenchmark.period_year == 2024,
                IndustryBenchmark.metric_name == "scope1_co2e_tonnes",
            )
            .one()
        )

    assert summary["industries"] == 1
    assert summary["metric_rows"] >= 1
    assert row.sample_size == 5
    assert row.p50 is not None
    assert 200 < row.p50 < 400


def test_get_benchmark_endpoint_returns_rows(benchmark_db_session_factory: sessionmaker) -> None:
    with benchmark_db_session_factory() as db:
        db.add_all(
            [
                CompanyReport(
                    company_name=f"Benchmark Utility {i}",
                    report_year=2024,
                    industry_code="D35.11",
                    scope1_co2e_tonnes=float(value),
                )
                for i, value in enumerate([100, 200, 300, 400, 500], start=1)
            ]
        )
        db.commit()

    def override_get_db() -> Generator[Session, None, None]:
        db = benchmark_db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        recompute_response = client.post("/benchmarks/recompute")
        assert recompute_response.status_code == 200

        response = client.get("/benchmarks/D35.11")
        assert response.status_code == 200
        payload = response.json()

    assert payload["industry_code"] == "D35.11"
    assert isinstance(payload["metrics"], list)
    assert len(payload["metrics"]) >= 1


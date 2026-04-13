from __future__ import annotations

from fastapi.testclient import TestClient

from core.database import get_db
from core.schemas import CompanyESGData
from esg_frameworks.comparison import build_comparison
from esg_frameworks.schemas import DimensionScore, FrameworkScoreResult
from main import app


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

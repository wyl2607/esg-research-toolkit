from collections.abc import Callable
from typing import Any

import pytest

from core.schemas import CompanyESGData
from taxonomy_scorer.framework import OBJECTIVES
from taxonomy_scorer.gap_analyzer import analyze_gaps
from taxonomy_scorer import scorer


@pytest.fixture
def make_company_data() -> Callable[..., CompanyESGData]:
    def _make_company_data(**overrides: Any) -> CompanyESGData:
        data = {
            "company_name": "Test Energy Co",
            "report_year": 2024,
            "scope1_co2e_tonnes": 0.0,
            "scope2_co2e_tonnes": 0.0,
            "scope3_co2e_tonnes": 0.0,
            "energy_consumption_mwh": 1_000.0,
            "renewable_energy_pct": 0.0,
            "water_usage_m3": 100.0,
            "waste_recycled_pct": 60.0,
            "primary_activities": [],
        }
        data.update(overrides)
        return CompanyESGData(**data)

    return _make_company_data


def test_solar_pv_alignment_high(
    make_company_data: Callable[..., CompanyESGData],
) -> None:
    data = make_company_data(
        primary_activities=["solar_pv"],
        renewable_energy_pct=95.0,
        taxonomy_aligned_revenue_pct=80.0,
    )

    result = scorer.score_company(data)

    assert result.revenue_aligned_pct >= 70.0
    assert result.revenue_aligned_pct == pytest.approx(80.0, abs=0.01)
    assert result.objective_scores["climate_mitigation"] > 0.8
    assert result.dnsh_pass is True


def test_wind_onshore_alignment_medium(
    make_company_data: Callable[..., CompanyESGData],
) -> None:
    data = make_company_data(
        primary_activities=["wind_onshore"],
        renewable_energy_pct=60.0,
        energy_consumption_mwh=None,
        taxonomy_aligned_capex_pct=50.0,
    )

    result = scorer.score_company(data)

    assert result.capex_aligned_pct >= 40.0
    assert result.capex_aligned_pct == pytest.approx(50.0, abs=0.01)
    assert result.objective_scores["climate_mitigation"] > 0.5


def test_battery_storage_alignment(
    make_company_data: Callable[..., CompanyESGData],
) -> None:
    data = make_company_data(
        primary_activities=["battery_storage"],
        renewable_energy_pct=100.0,
    )

    result = scorer.score_company(data)

    assert result.objective_scores["climate_mitigation"] > 0.7
    assert result.dnsh_pass is True


def test_dnsh_failure_high_emissions(
    make_company_data: Callable[..., CompanyESGData],
) -> None:
    data = make_company_data(
        primary_activities=["solar_pv"],
        scope1_co2e_tonnes=100_000.0,
        scope2_co2e_tonnes=0.0,
        energy_consumption_mwh=1_000.0,
        renewable_energy_pct=0.0,
        water_usage_m3=None,
        waste_recycled_pct=None,
    )

    result = scorer.score_company(data)
    detailed_gaps = analyze_gaps(data, result)

    assert result.dnsh_pass is False
    assert result.objective_scores["climate_mitigation"] == pytest.approx(0.5, abs=0.01)
    assert any("water usage" in gap.lower() for gap in result.gaps)
    assert any("waste recycling rate" in gap.lower() for gap in result.gaps)
    assert any(gap.description.startswith("DNSH check failed") for gap in detailed_gaps)


def test_multiple_activities(
    make_company_data: Callable[..., CompanyESGData],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen_activities: list[str] = []
    per_activity_scores = {"solar_pv": 0.6, "wind_onshore": 0.9}

    def fake_score_activity_alignment(data: CompanyESGData, activity_id: str) -> float:
        seen_activities.append(activity_id)
        return per_activity_scores[activity_id]

    monkeypatch.setattr(
        scorer,
        "_score_activity_alignment",
        fake_score_activity_alignment,
    )
    monkeypatch.setattr(scorer, "_check_dnsh", lambda data, activity_id: True)

    data = make_company_data(
        primary_activities=["solar_pv", "wind_onshore"],
        renewable_energy_pct=80.0,
    )

    result = scorer.score_company(data)

    assert seen_activities == ["solar_pv", "wind_onshore"]
    assert result.objective_scores["climate_mitigation"] == pytest.approx(0.75, abs=0.01)
    assert result.revenue_aligned_pct == pytest.approx(75.0, abs=0.01)
    assert result.dnsh_pass is True


def test_no_activities(
    make_company_data: Callable[..., CompanyESGData],
) -> None:
    data = make_company_data(
        primary_activities=[],
        scope1_co2e_tonnes=None,
        scope2_co2e_tonnes=None,
        scope3_co2e_tonnes=None,
        energy_consumption_mwh=None,
        water_usage_m3=None,
        waste_recycled_pct=None,
    )

    result = scorer.score_company(data)

    assert set(result.objective_scores) == set(OBJECTIVES)
    assert all(score == 0.0 for score in result.objective_scores.values())
    assert "No taxonomy-eligible activities identified" in result.gaps
    assert result.dnsh_pass is False

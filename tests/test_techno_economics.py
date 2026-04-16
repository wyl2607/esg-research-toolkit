import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from core.schemas import LCOEInput
from main import app
from techno_economics.lcoe import calculate_lcoe
from techno_economics.npv_irr import calculate_irr, calculate_npv, calculate_payback
from techno_economics.sensitivity import run_sensitivity


def make_lcoe_input(**overrides: float | int | str) -> LCOEInput:
    # electricity_price_eur_per_mwh is pinned to 60 so IRR/NPV/payback assertions
    # remain stable regardless of changes to the schema default (currently 95 EUR/MWh).
    data: dict[str, float | int | str] = {
        "technology": "solar_pv",
        "capex_eur_per_kw": 800,
        "opex_eur_per_kw_year": 15,
        "capacity_factor": 0.18,
        "lifetime_years": 25,
        "discount_rate": 0.07,
        "electricity_price_eur_per_mwh": 60.0,
    }
    data.update(overrides)
    return LCOEInput(**data)


def test_solar_pv_lcoe_realistic() -> None:
    result = calculate_lcoe(make_lcoe_input())

    assert result.lcoe_eur_per_mwh == pytest.approx(53.05, abs=0.01)
    assert result.irr == pytest.approx(0.09, abs=0.01)
    assert result.payback_years == pytest.approx(10.05, abs=0.01)


def test_wind_onshore_lcoe() -> None:
    result = calculate_lcoe(
        make_lcoe_input(
            technology="wind_onshore",
            capex_eur_per_kw=1200,
            opex_eur_per_kw_year=30,
            capacity_factor=0.35,
        )
    )

    assert result.lcoe_eur_per_mwh < 60
    assert result.irr > 0.05
    assert result.lcoe_eur_per_mwh == pytest.approx(43.37, abs=0.01)
    assert result.irr == pytest.approx(0.12, abs=0.01)


def test_battery_storage_lcoe() -> None:
    result = calculate_lcoe(
        make_lcoe_input(
            technology="battery_storage",
            capex_eur_per_kw=500,
            opex_eur_per_kw_year=10,
            capacity_factor=0.9,
            lifetime_years=15,
        )
    )

    assert result.lcoe_eur_per_mwh > 0
    assert result.lcoe_eur_per_mwh == pytest.approx(8.23, abs=0.01)
    assert result.npv_eur == pytest.approx(3717.33, abs=0.01)


def test_npv_positive_project() -> None:
    annual_cash_flow = 15000 - 3000
    cash_flows = [-100000] + [annual_cash_flow] * 20

    npv = calculate_npv(cash_flows, 0.07)

    assert npv > 0
    assert npv == pytest.approx(27128.17, abs=0.01)


def test_irr_calculation() -> None:
    cash_flows = [-100000] + [12000] * 15

    irr = calculate_irr(cash_flows)
    payback = calculate_payback(100000, 12000)

    assert irr == pytest.approx(0.08, abs=0.01)
    assert payback == pytest.approx(8.33, abs=0.01)


def test_sensitivity_analysis() -> None:
    results = run_sensitivity(make_lcoe_input(), variation_range=0.2, steps=5)

    assert len(results) == 2

    by_parameter = {result.parameter: result for result in results}
    assert set(by_parameter) == {"capex_eur_per_kw", "opex_eur_per_kw_year"}

    capex_result = by_parameter["capex_eur_per_kw"]
    opex_result = by_parameter["opex_eur_per_kw_year"]

    assert capex_result.variations == pytest.approx([-0.2, -0.1, 0.0, 0.1, 0.2], abs=1e-12)
    assert opex_result.variations == pytest.approx([-0.2, -0.1, 0.0, 0.1, 0.2], abs=1e-12)
    assert capex_result.lcoe_values[2] == pytest.approx(53.05, abs=0.01)
    assert opex_result.lcoe_values[2] == pytest.approx(53.05, abs=0.01)
    assert capex_result.lcoe_values[-1] > capex_result.lcoe_values[2]


def test_zero_capacity_factor() -> None:
    with pytest.raises(ValidationError):
        make_lcoe_input(capacity_factor=0.0)


def test_sensitivity_endpoint_returns_openapi_aligned_fields() -> None:
    with TestClient(app) as client:
        response = client.post("/techno/sensitivity", json=make_lcoe_input().model_dump())

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["parameter"] == "capex_eur_per_kw"
    assert payload[0]["values"][2] == pytest.approx(0.0, abs=1e-12)
    assert "lcoe_results" in payload[0]
    assert "lcoe_values" not in payload[0]


def test_benchmark_presets_return_full_lcoe_inputs() -> None:
    with TestClient(app) as client:
        response = client.get("/techno/benchmarks")

    assert response.status_code == 200
    payload = response.json()
    assert payload["solar_pv"]["technology"] == "solar_pv"
    assert payload["solar_pv"]["capacity_mw"] == pytest.approx(100.0)
    assert payload["wind_onshore"]["capacity_factor"] == pytest.approx(0.35)

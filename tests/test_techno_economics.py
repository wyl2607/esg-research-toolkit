import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from core.schemas import LCOEInput, SAFInput
from main import app
from techno_economics.lcoe import calculate_lcoe
from techno_economics.npv_irr import calculate_irr, calculate_npv, calculate_payback
from techno_economics.saf import calculate_saf_cost
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
    with pytest.raises(ValidationError):
        make_lcoe_input(capacity_factor=1e-6)


def test_sensitivity_endpoint_returns_openapi_aligned_fields() -> None:
    with TestClient(app) as client:
        response = client.post("/techno/sensitivity", json=make_lcoe_input().model_dump())

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["parameter"] == "capex_eur_per_kw"
    assert payload[0]["values"][2] == pytest.approx(0.0, abs=1e-12)
    assert "lcoe_results" in payload[0]
    assert "lcoe_values" not in payload[0]


def test_sensitivity_endpoint_handles_zero_base_lcoe_without_500() -> None:
    payload = make_lcoe_input(
        capex_eur_per_kw=0.5,
        opex_eur_per_kw_year=0.0,
        capacity_factor=1.0,
        electricity_price_eur_per_mwh=0.0,
    ).model_dump()

    with TestClient(app) as client:
        response = client.post("/techno/sensitivity", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert all(change == 0.0 for change in body[0]["lcoe_change_pct"])


def test_techno_endpoints_reject_subminimum_capacity_factor() -> None:
    payload = make_lcoe_input().model_dump()
    payload["capacity_factor"] = 1e-6

    with TestClient(app) as client:
        lcoe_response = client.post("/techno/lcoe", json=payload)
        sensitivity_response = client.post("/techno/sensitivity", json=payload)

    assert lcoe_response.status_code == 422
    assert sensitivity_response.status_code == 422


def test_benchmark_presets_return_full_lcoe_inputs() -> None:
    with TestClient(app) as client:
        response = client.get("/techno/benchmarks")

    assert response.status_code == 200
    payload = response.json()
    assert payload["solar_pv"]["technology"] == "solar_pv"
    assert payload["solar_pv"]["capacity_mw"] == pytest.approx(100.0)
    assert payload["wind_onshore"]["capacity_factor"] == pytest.approx(0.35)


# ---------------------------------------------------------------------------
# SAF calculator tests
# ---------------------------------------------------------------------------

def make_saf_input(**overrides) -> SAFInput:
    data = {
        "pathway": "HEFA",
        "region": "EU",
        "production_capacity_tonnes_year": 50_000,
        "capex_eur_per_tonne_year": 1_800,
        "lifetime_years": 20,
        "discount_rate": 0.08,
        "feedstock_cost_eur_per_tonne": 600,
        "feedstock_to_saf_ratio": 1.25,
        "opex_eur_per_tonne": 250,
        "policy_credit_eur_per_tonne": 0.0,
        "jet_fuel_price_eur_per_litre": 0.60,
    }
    data.update(overrides)
    return SAFInput(**data)


def test_saf_hefa_cost_in_expected_range() -> None:
    """HEFA-SAF should cost between €0.80–€2.00/L at market parameters."""
    result = calculate_saf_cost(make_saf_input())

    assert 0.80 <= result.levelized_cost_eur_per_litre <= 2.00
    assert result.pathway == "HEFA"
    assert result.region == "EU"


def test_saf_hefa_not_cost_competitive_vs_kerosene_2025() -> None:
    """At 2025 market params, HEFA-SAF costs more than Jet A-1 (€0.60/L)."""
    result = calculate_saf_cost(make_saf_input(jet_fuel_price_eur_per_litre=0.60))

    assert not result.is_cost_competitive
    assert result.premium_vs_conventional_pct > 0


def test_saf_breakeven_price_equals_levelized_cost() -> None:
    """Breakeven jet fuel price should equal levelized SAF cost."""
    result = calculate_saf_cost(make_saf_input())

    assert result.breakeven_jet_fuel_price_eur_per_litre == pytest.approx(
        result.levelized_cost_eur_per_litre, abs=0.0001
    )


def test_saf_policy_credit_reduces_cost() -> None:
    """A subsidy (negative policy_credit) should lower the levelized cost."""
    base = calculate_saf_cost(make_saf_input(policy_credit_eur_per_tonne=0.0))
    subsidised = calculate_saf_cost(make_saf_input(policy_credit_eur_per_tonne=-500.0))

    assert subsidised.levelized_cost_eur_per_litre < base.levelized_cost_eur_per_litre


def test_saf_ptl_more_expensive_than_hefa() -> None:
    """PtL should cost significantly more than HEFA at current params."""
    hefa = calculate_saf_cost(make_saf_input(pathway="HEFA"))
    ptl = calculate_saf_cost(
        make_saf_input(
            pathway="PtL",
            capex_eur_per_tonne_year=12_000,
            feedstock_cost_eur_per_tonne=800,
            feedstock_to_saf_ratio=5.5,
            opex_eur_per_tonne=400,
        )
    )

    assert ptl.levelized_cost_eur_per_litre > hefa.levelized_cost_eur_per_litre * 1.5


def test_saf_cost_breakdown_sums_to_total() -> None:
    """CAPEX + feedstock + OPEX - credit ≈ total (at annualized level)."""
    result = calculate_saf_cost(make_saf_input())

    component_total = (
        result.capex_component_eur_per_tonne
        + result.feedstock_component_eur_per_tonne
        + result.opex_component_eur_per_tonne
        - result.policy_credit_eur_per_tonne
    )
    # Levelized cost differs slightly from annualized sum due to discounting
    assert component_total > 0
    assert abs(component_total - result.levelized_cost_eur_per_tonne) / result.levelized_cost_eur_per_tonne < 0.25


def test_saf_litres_per_tonne_conversion() -> None:
    """At density 0.800 kg/L: 1 tonne = 1250 L → €/L = €/tonne / 1250."""
    result = calculate_saf_cost(make_saf_input(saf_density_kg_per_litre=0.800))

    expected = result.levelized_cost_eur_per_tonne / 1250.0
    assert result.levelized_cost_eur_per_litre == pytest.approx(expected, abs=0.0001)


def test_saf_endpoint_returns_200() -> None:
    with TestClient(app) as client:
        response = client.post("/techno/saf", json=make_saf_input().model_dump())

    assert response.status_code == 200
    body = response.json()
    assert body["pathway"] == "HEFA"
    assert body["levelized_cost_eur_per_litre"] > 0
    assert "premium_vs_conventional_pct" in body
    assert "breakeven_jet_fuel_price_eur_per_litre" in body


def test_saf_benchmarks_endpoint_returns_all_pathways() -> None:
    with TestClient(app) as client:
        response = client.get("/techno/saf-benchmarks")

    assert response.status_code == 200
    payload = response.json()
    assert "HEFA_EU" in payload
    assert "ATJ_Brazil" in payload
    assert "ATJ_US_IRA" in payload
    assert "FT_biomass_DE" in payload
    assert "PtL_EU_2025" in payload
    assert "PtL_EU_2035_projected" in payload

    # IRA credit must be negative (subsidy)
    assert payload["ATJ_US_IRA"]["policy_credit_eur_per_tonne"] < 0


def test_saf_validation_rejects_positive_policy_credit() -> None:
    """policy_credit_eur_per_tonne must be ≤ 0 (it's a cost reduction)."""
    with pytest.raises(ValidationError):
        SAFInput(
            pathway="HEFA",
            region="EU",
            production_capacity_tonnes_year=50_000,
            capex_eur_per_tonne_year=1_800,
            feedstock_cost_eur_per_tonne=600,
            feedstock_to_saf_ratio=1.25,
            opex_eur_per_tonne=250,
            policy_credit_eur_per_tonne=100.0,  # invalid: positive
            jet_fuel_price_eur_per_litre=0.60,
        )

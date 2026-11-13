import pytest

from core.schemas import LCOEInput
from techno_economics.lcoe import calculate_lcoe
from techno_economics.npv_irr import calculate_irr, calculate_npv


def _npv_ref(flows: list[float], discount_rate: float) -> float:
    return sum(
        cash_flow / (1.0 + discount_rate) ** period
        for period, cash_flow in enumerate(flows)
    )


def _lcoe_ref(inp: LCOEInput) -> float:
    annual_energy_kwh = inp.capacity_factor * 8760.0
    discounted_opex = sum(
        inp.opex_eur_per_kw_year * inp.reference_fx_to_eur
        / (1.0 + inp.discount_rate) ** year
        for year in range(1, inp.lifetime_years + 1)
    )
    discounted_energy_kwh = sum(
        annual_energy_kwh / (1.0 + inp.discount_rate) ** year
        for year in range(1, inp.lifetime_years + 1)
    )
    return (
        (inp.capex_eur_per_kw * inp.reference_fx_to_eur + discounted_opex)
        / discounted_energy_kwh
        * 1000.0
    )


def _lcoe_input(**overrides: float | int | str) -> LCOEInput:
    values: dict[str, float | int | str] = {
        "technology": "solar_pv",
        "capacity_mw": 100.0,
        "capex_eur_per_kw": 800.0,
        "opex_eur_per_kw_year": 15.0,
        "capacity_factor": 0.18,
        "lifetime_years": 25,
        "discount_rate": 0.07,
        "electricity_price_eur_per_mwh": 60.0,
        "currency": "EUR",
        "reference_fx_to_eur": 1.0,
    }
    values.update(overrides)
    return LCOEInput(**values)


def test_npv_zero_discount_rate_equals_cash_flow_sum() -> None:
    flows = [-100_000.0, 12_000.0, 12_000.0, 12_000.0]

    assert calculate_npv(flows, 0.0) == sum(flows)


def test_npv_matches_closed_form_reference_at_seven_percent() -> None:
    flows = [-100_000.0] + [12_000.0] * 20

    assert calculate_npv(flows, 0.07) == pytest.approx(_npv_ref(flows, 0.07), abs=0.01)


def test_npv_matches_reference_for_fractional_cash_flows() -> None:
    flows = [-125_000.25, 18_222.5, 19_100.75, 20_001.25]

    assert calculate_npv(flows, 0.035) == pytest.approx(_npv_ref(flows, 0.035), abs=0.01)


def test_irr_for_one_period_return_is_ten_percent() -> None:
    assert calculate_irr([-100.0, 110.0]) == 0.1


def test_irr_without_sign_change_returns_zero_current_behavior() -> None:
    # Current behavior: a cash-flow series without a sign change returns 0.0.
    assert calculate_irr([100.0, 100.0]) == 0.0


def test_lcoe_matches_discounted_cash_flow_reference() -> None:
    inp = _lcoe_input()

    assert calculate_lcoe(inp).lcoe_eur_per_mwh == pytest.approx(_lcoe_ref(inp), abs=0.01)


def test_lcoe_at_zero_discount_rate_matches_closed_form_reference() -> None:
    inp = _lcoe_input(discount_rate=0.0, lifetime_years=20)

    assert calculate_lcoe(inp).lcoe_eur_per_mwh == pytest.approx(_lcoe_ref(inp), abs=0.01)


def test_lcoe_with_short_lifetime_matches_closed_form_reference() -> None:
    inp = _lcoe_input(lifetime_years=3, discount_rate=0.12)

    assert calculate_lcoe(inp).lcoe_eur_per_mwh == pytest.approx(_lcoe_ref(inp), abs=0.01)


def test_lcoe_fx_conversion_preserves_local_to_eur_relation() -> None:
    result = calculate_lcoe(_lcoe_input(currency="USD", reference_fx_to_eur=2.0))

    assert result.lcoe_local_per_mwh * 2.0 == pytest.approx(result.lcoe_eur_per_mwh, abs=0.01)

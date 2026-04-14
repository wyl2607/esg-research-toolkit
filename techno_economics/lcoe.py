import numpy as np

from core.schemas import LCOEInput, LCOEResult
from techno_economics.npv_irr import calculate_irr, calculate_npv, calculate_payback

HOURS_PER_YEAR = 8760.0
KWH_PER_MWH = 1000.0


def calculate_lcoe(inp: LCOEInput) -> LCOEResult:
    """
    计算 LCOE（平准化能源成本）。

    所有输入值（capex / opex / electricity_price）均以 inp.currency 计价。
    计算前先乘以 reference_fx_to_eur 折算为 EUR，保证跨地区可比性。
    结果 lcoe_eur_per_mwh 为 EUR 基准，lcoe_local_per_mwh 为原始货币。

    公式：
      LCOE = (CAPEX_eur + Σ OPEX_eur_t/(1+r)^t) / Σ E_t/(1+r)^t
    """
    fx = inp.reference_fx_to_eur

    # Normalize all monetary inputs to EUR
    capex_eur = inp.capex_eur_per_kw * fx
    opex_eur = inp.opex_eur_per_kw_year * fx
    price_eur = inp.electricity_price_eur_per_mwh * fx

    years = np.arange(1, inp.lifetime_years + 1, dtype=float)
    discount_factors = np.power(1.0 + inp.discount_rate, years)

    annual_opex = np.full(inp.lifetime_years, opex_eur, dtype=float)
    annual_energy_kwh = np.full(
        inp.lifetime_years,
        inp.capacity_factor * HOURS_PER_YEAR,
        dtype=float,
    )

    discounted_opex = float(np.sum(annual_opex / discount_factors))
    discounted_energy_kwh = float(np.sum(annual_energy_kwh / discount_factors))
    lcoe_eur_per_mwh = ((capex_eur + discounted_opex) / discounted_energy_kwh) * KWH_PER_MWH

    annual_revenue = (annual_energy_kwh[0] / KWH_PER_MWH) * price_eur
    annual_net_cash_flow = annual_revenue - opex_eur
    cash_flows = [-capex_eur] + [annual_net_cash_flow] * inp.lifetime_years

    npv_eur = calculate_npv(cash_flows, inp.discount_rate)
    irr = calculate_irr(cash_flows)
    payback_years = calculate_payback(capex_eur, annual_net_cash_flow)

    lcoe_local = lcoe_eur_per_mwh / fx if fx > 0 else lcoe_eur_per_mwh

    return LCOEResult(
        technology=inp.technology,
        lcoe_eur_per_mwh=round(float(lcoe_eur_per_mwh), 2),
        lcoe_local_per_mwh=round(float(lcoe_local), 2),
        npv_eur=npv_eur,
        irr=irr,
        payback_years=payback_years if np.isinf(payback_years) else round(float(payback_years), 2),
        lifetime_years=inp.lifetime_years,
        electricity_price_eur_per_mwh=round(price_eur, 2),
        currency=inp.currency,
        reference_fx_to_eur=fx,
    )

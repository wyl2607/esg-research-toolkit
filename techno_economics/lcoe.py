import numpy as np

from core.schemas import LCOEInput, LCOEResult
from techno_economics.npv_irr import calculate_irr, calculate_npv, calculate_payback

HOURS_PER_YEAR = 8760.0
KWH_PER_MWH = 1000.0


def calculate_lcoe(inp: LCOEInput) -> LCOEResult:
    """
    计算 LCOE（平准化能源成本）。

    公式：
      LCOE = (CAPEX + Σ OPEX_t/(1+r)^t) / Σ E_t/(1+r)^t

    其中：
      - CAPEX = capex_eur_per_kw（假设装机容量 1 kW，便于单位化）
      - OPEX_t = opex_eur_per_kw_year（每年固定）
      - E_t = capacity_factor * 8760 kWh/year（每年发电量，1 kW 装机）
      - r = discount_rate
      - t = 1..lifetime_years

    返回 LCOEResult，其中：
      - lcoe_eur_per_mwh：LCOE（€/MWh）
      - npv_eur：假设电价 60 €/MWh 的 NPV
      - irr：IRR
      - payback_years：简单回收期（CAPEX / 年净收益）
      - lifetime_years：生命周期年数
    """
    years = np.arange(1, inp.lifetime_years + 1, dtype=float)
    discount_factors = np.power(1.0 + inp.discount_rate, years)

    annual_opex = np.full(inp.lifetime_years, inp.opex_eur_per_kw_year, dtype=float)
    annual_energy_kwh = np.full(
        inp.lifetime_years,
        inp.capacity_factor * HOURS_PER_YEAR,
        dtype=float,
    )

    discounted_opex = float(np.sum(annual_opex / discount_factors))
    discounted_energy_kwh = float(np.sum(annual_energy_kwh / discount_factors))
    lcoe_eur_per_mwh = ((inp.capex_eur_per_kw + discounted_opex) / discounted_energy_kwh) * KWH_PER_MWH

    annual_revenue = (annual_energy_kwh[0] / KWH_PER_MWH) * inp.electricity_price_eur_per_mwh
    annual_net_cash_flow = annual_revenue - inp.opex_eur_per_kw_year
    cash_flows = [-inp.capex_eur_per_kw] + [annual_net_cash_flow] * inp.lifetime_years

    npv_eur = calculate_npv(cash_flows, inp.discount_rate)
    irr = calculate_irr(cash_flows)
    payback_years = calculate_payback(inp.capex_eur_per_kw, annual_net_cash_flow)

    return LCOEResult(
        technology=inp.technology,
        lcoe_eur_per_mwh=round(float(lcoe_eur_per_mwh), 2),
        npv_eur=npv_eur,
        irr=irr,
        payback_years=payback_years if np.isinf(payback_years) else round(float(payback_years), 2),
        lifetime_years=inp.lifetime_years,
        electricity_price_eur_per_mwh=inp.electricity_price_eur_per_mwh,
    )

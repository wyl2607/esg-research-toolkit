from fastapi import APIRouter, Query

from core.schemas import LCOEInput, LCOEResult, SensitivityResult
from techno_economics.lcoe import calculate_lcoe
from techno_economics.sensitivity import run_sensitivity

router = APIRouter(prefix="/techno", tags=["techno_economics"])


@router.post("/lcoe", response_model=LCOEResult)
def lcoe(inp: LCOEInput) -> LCOEResult:
    """计算 LCOE / NPV / IRR。"""
    return calculate_lcoe(inp)


@router.post("/sensitivity", response_model=list[SensitivityResult])
def sensitivity(
    inp: LCOEInput,
    variation_range: float = Query(default=0.2, gt=0.0, le=1.0),
    steps: int = Query(default=5, ge=2, le=25),
) -> list[SensitivityResult]:
    """对 CAPEX 和 OPEX 做敏感性分析，返回 ±variation_range 范围内的 LCOE 变化。"""
    results = run_sensitivity(inp, variation_range, steps)
    return [
        SensitivityResult(
            parameter=result.parameter,
            base_value=result.base_value,
            values=result.variations,
            lcoe_results=result.lcoe_values,
            lcoe_change_pct=result.lcoe_change_pct,
        )
        for result in results
    ]


@router.get("/benchmarks", response_model=dict[str, LCOEInput])
def benchmarks() -> dict[str, LCOEInput]:
    """返回典型可再生能源技术的参考输入参数预设。"""
    return {
        "solar_pv": LCOEInput(
            technology="solar_pv",
            capacity_mw=100,
            capacity_factor=0.18,
            capex_eur_per_kw=800,
            opex_eur_per_kw_year=15,
            lifetime_years=25,
            discount_rate=0.07,
            electricity_price_eur_per_mwh=95,
            currency="EUR",
            reference_fx_to_eur=1.0,
        ),
        "wind_onshore": LCOEInput(
            technology="wind_onshore",
            capacity_mw=120,
            capacity_factor=0.35,
            capex_eur_per_kw=1200,
            opex_eur_per_kw_year=30,
            lifetime_years=25,
            discount_rate=0.07,
            electricity_price_eur_per_mwh=95,
            currency="EUR",
            reference_fx_to_eur=1.0,
        ),
        "wind_offshore": LCOEInput(
            technology="wind_offshore",
            capacity_mw=300,
            capacity_factor=0.5,
            capex_eur_per_kw=2800,
            opex_eur_per_kw_year=90,
            lifetime_years=25,
            discount_rate=0.07,
            electricity_price_eur_per_mwh=95,
            currency="EUR",
            reference_fx_to_eur=1.0,
        ),
        "battery_storage": LCOEInput(
            technology="battery_storage",
            capacity_mw=50,
            capacity_factor=0.9,
            capex_eur_per_kw=500,
            opex_eur_per_kw_year=10,
            lifetime_years=15,
            discount_rate=0.07,
            electricity_price_eur_per_mwh=95,
            currency="EUR",
            reference_fx_to_eur=1.0,
        ),
    }

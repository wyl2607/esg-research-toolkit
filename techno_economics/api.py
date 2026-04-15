from fastapi import APIRouter

from core.schemas import LCOEInput, LCOEResult
from techno_economics.lcoe import calculate_lcoe
from techno_economics.sensitivity import SensitivityResult, run_sensitivity

router = APIRouter(prefix="/techno", tags=["techno_economics"])


@router.post("/lcoe", response_model=LCOEResult)
def lcoe(inp: LCOEInput) -> LCOEResult:
    """计算 LCOE / NPV / IRR。"""
    return calculate_lcoe(inp)


@router.post("/sensitivity")
def sensitivity(
    inp: LCOEInput,
    variation_range: float = 0.2,
    steps: int = 5,
) -> list[dict[str, str | float | list[float]]]:
    """对 CAPEX 和 OPEX 做敏感性分析，返回 ±variation_range 范围内的 LCOE 变化。"""
    results: list[SensitivityResult] = run_sensitivity(inp, variation_range, steps)
    return [
        {
            "parameter": result.parameter,
            "base_value": result.base_value,
            "variations": result.variations,
            "lcoe_values": result.lcoe_values,
            "lcoe_change_pct": result.lcoe_change_pct,
        }
        for result in results
    ]


@router.get("/benchmarks")
def benchmarks() -> dict[str, dict[str, int | str]]:
    """返回典型可再生能源技术的参考 LCOE 范围（2024 年欧洲市场数据）。"""
    return {
        "solar_pv": {
            "lcoe_min_eur_per_mwh": 35,
            "lcoe_max_eur_per_mwh": 65,
            "source": "IRENA 2024",
        },
        "wind_onshore": {
            "lcoe_min_eur_per_mwh": 30,
            "lcoe_max_eur_per_mwh": 60,
            "source": "IRENA 2024",
        },
        "wind_offshore": {
            "lcoe_min_eur_per_mwh": 60,
            "lcoe_max_eur_per_mwh": 110,
            "source": "IRENA 2024",
        },
        "battery_storage": {
            "lcoe_min_eur_per_mwh": 100,
            "lcoe_max_eur_per_mwh": 200,
            "source": "BloombergNEF 2024",
        },
    }

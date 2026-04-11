from dataclasses import dataclass

from core.schemas import LCOEInput, LCOEResult
from techno_economics.lcoe import calculate_lcoe


@dataclass
class SensitivityResult:
    parameter: str
    base_value: float
    variations: list[float]
    lcoe_values: list[float]
    lcoe_change_pct: list[float]


def run_sensitivity(
    inp: LCOEInput,
    variation_range: float = 0.2,
    steps: int = 5,
) -> list[SensitivityResult]:
    """
    对 capex_eur_per_kw 和 opex_eur_per_kw_year 做敏感性分析。
    variation_range=0.2 表示 ±20%，steps=5 表示 5 个点（-20%, -10%, 0%, +10%, +20%）。
    返回两个 SensitivityResult（capex 和 opex）。
    """
    base_result: LCOEResult = calculate_lcoe(inp)
    base_lcoe = base_result.lcoe_eur_per_mwh
    results: list[SensitivityResult] = []

    variations = [
        round(-variation_range + i * (2 * variation_range / (steps - 1)), 2)
        for i in range(steps)
    ]

    for param in ("capex_eur_per_kw", "opex_eur_per_kw_year"):
        base_val = getattr(inp, param)
        lcoe_vals: list[float] = []
        for variation in variations:
            modified = inp.model_copy(update={param: base_val * (1 + variation)})
            lcoe_vals.append(calculate_lcoe(modified).lcoe_eur_per_mwh)
        results.append(
            SensitivityResult(
                parameter=param,
                base_value=base_val,
                variations=variations,
                lcoe_values=lcoe_vals,
                lcoe_change_pct=[
                    round((lcoe - base_lcoe) / base_lcoe * 100, 1) for lcoe in lcoe_vals
                ],
            )
        )

    return results

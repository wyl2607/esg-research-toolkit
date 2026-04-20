from fastapi import APIRouter, Query

from core.schemas import LCOEInput, LCOEResult, SAFCostResult, SAFInput, SensitivityResult
from techno_economics.lcoe import calculate_lcoe
from techno_economics.saf import calculate_saf_cost
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


@router.post("/saf", response_model=SAFCostResult)
def saf_cost(inp: SAFInput) -> SAFCostResult:
    """计算 SAF（可持续航空燃料）平准化生产成本及盈亏平衡分析。"""
    return calculate_saf_cost(inp)


@router.get("/saf-benchmarks", response_model=dict[str, SAFInput])
def saf_benchmarks() -> dict[str, SAFInput]:
    """返回主要 SAF 生产路线的参考输入参数（2025 年市场数据）。

    数据来源：
    - IATA SAF Report 2024
    - ICAO CORSIA SAF Eligibility Criteria
    - EU ReFuelEU Aviation mandate (EU 2023/2405)
    - IEA Aviation Technology Perspectives 2024
    - BloombergNEF SAF Market Outlook 2025
    """
    return {
        # -------------------------------------------------------------------
        # HEFA: Hydroprocessed Esters and Fatty Acids
        # Feedstock: Used cooking oil (UCO), tallow, palm fatty acid distillate
        # Most commercially mature pathway; ~80% of current SAF supply
        # -------------------------------------------------------------------
        "HEFA_EU": SAFInput(
            pathway="HEFA",
            region="EU",
            production_capacity_tonnes_year=50_000,
            capex_eur_per_tonne_year=1_800,
            lifetime_years=20,
            discount_rate=0.08,
            feedstock_cost_eur_per_tonne=600,   # UCO spot price EU 2025
            feedstock_to_saf_ratio=1.25,         # ~80% conversion yield
            opex_eur_per_tonne=250,
            policy_credit_eur_per_tonne=0,
            jet_fuel_price_eur_per_litre=0.60,
        ),
        # -------------------------------------------------------------------
        # ATJ: Alcohol-to-Jet (sugarcane ethanol)
        # Feedstock: Brazilian sugarcane → ethanol → SAF
        # Competitive feedstock cost; export to Germany viable post-2027
        # -------------------------------------------------------------------
        "ATJ_Brazil": SAFInput(
            pathway="ATJ",
            region="BR",
            production_capacity_tonnes_year=100_000,
            capex_eur_per_tonne_year=2_200,
            lifetime_years=20,
            discount_rate=0.09,
            feedstock_cost_eur_per_tonne=180,   # Brazilian sugarcane ethanol equivalent
            feedstock_to_saf_ratio=2.1,          # ethanol → SAF conversion ratio
            opex_eur_per_tonne=280,
            policy_credit_eur_per_tonne=0,
            jet_fuel_price_eur_per_litre=0.60,
        ),
        # -------------------------------------------------------------------
        # ATJ: Alcohol-to-Jet (US corn ethanol)
        # IRA Section 45Z clean fuel production credit: ~$1.75/gal → ~€420/tonne
        # Makes US ATJ-SAF cost-competitive for German import 2024-2032
        # -------------------------------------------------------------------
        "ATJ_US_IRA": SAFInput(
            pathway="ATJ",
            region="US",
            production_capacity_tonnes_year=200_000,
            capex_eur_per_tonne_year=2_000,
            lifetime_years=20,
            discount_rate=0.075,
            feedstock_cost_eur_per_tonne=220,
            feedstock_to_saf_ratio=2.1,
            opex_eur_per_tonne=260,
            policy_credit_eur_per_tonne=-390,   # IRA 45Z credit ~€390/tonne SAF
            jet_fuel_price_eur_per_litre=0.60,
            currency="USD",
            reference_fx_to_eur=0.93,
        ),
        # -------------------------------------------------------------------
        # FT-biomass: Fischer-Tropsch from biomass gasification
        # Feedstock: agricultural residues, forestry waste
        # Higher CAPEX, good lifecycle emissions; Germany has strong feedstock base
        # -------------------------------------------------------------------
        "FT_biomass_DE": SAFInput(
            pathway="FT-biomass",
            region="DE",
            production_capacity_tonnes_year=30_000,
            capex_eur_per_tonne_year=5_500,
            lifetime_years=20,
            discount_rate=0.08,
            feedstock_cost_eur_per_tonne=90,    # straw / wood chips EU 2025
            feedstock_to_saf_ratio=4.5,          # biomass gasification yield
            opex_eur_per_tonne=350,
            policy_credit_eur_per_tonne=0,
            jet_fuel_price_eur_per_litre=0.60,
        ),
        # -------------------------------------------------------------------
        # PtL: Power-to-Liquid (electrofuels / e-kerosene)
        # Green H2 + DAC CO2 → Fischer-Tropsch → SAF
        # Currently most expensive; EU mandate 1.2% PtL by 2030, 35% by 2050
        # Projected cost decline to €1.00-1.50/L by 2035-2040
        # -------------------------------------------------------------------
        "PtL_EU_2025": SAFInput(
            pathway="PtL",
            region="EU",
            production_capacity_tonnes_year=10_000,
            capex_eur_per_tonne_year=12_000,
            lifetime_years=20,
            discount_rate=0.09,
            feedstock_cost_eur_per_tonne=800,   # green H2 equivalent cost
            feedstock_to_saf_ratio=5.5,          # H2 + CO2 → FT → SAF
            opex_eur_per_tonne=400,
            policy_credit_eur_per_tonne=0,
            jet_fuel_price_eur_per_litre=0.60,
        ),
        # -------------------------------------------------------------------
        # PtL 2035 scenario: projected cost after scale-up + green H2 cost decline
        # Assumes electrolyzer CAPEX halved, renewable power at €30/MWh
        # -------------------------------------------------------------------
        "PtL_EU_2035_projected": SAFInput(
            pathway="PtL",
            region="EU",
            production_capacity_tonnes_year=100_000,
            capex_eur_per_tonne_year=5_000,
            lifetime_years=20,
            discount_rate=0.07,
            feedstock_cost_eur_per_tonne=300,   # projected 2035 green H2
            feedstock_to_saf_ratio=5.5,
            opex_eur_per_tonne=200,
            policy_credit_eur_per_tonne=0,
            jet_fuel_price_eur_per_litre=0.65,
        ),
    }

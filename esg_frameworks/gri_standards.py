"""
GRI 通用标准 2021（GRI Universal Standards）
覆盖：GRI 2（一般披露）+ GRI 300（环境）+ GRI 400（社会）+ GRI 200（经济）

评分逻辑（4 维度）：
  - 环境披露（GRI 300）：30%
  - 社会披露（GRI 400）：35%
  - 治理披露（GRI 2）：20%
  - 经济影响（GRI 200）：15%
"""
from __future__ import annotations

from core.schemas import CompanyESGData
from esg_frameworks.schemas import DimensionScore, FrameworkScoreResult


def _grade(score: float) -> str:
    if score >= 0.85:
        return "A"
    if score >= 0.70:
        return "B"
    if score >= 0.55:
        return "C"
    if score >= 0.40:
        return "D"
    return "F"


def score_gri(data: CompanyESGData) -> FrameworkScoreResult:
    """GRI Universal Standards scoring."""
    # GRI 300 环境
    env_items = [
        data.energy_consumption_mwh,
        data.renewable_energy_pct,
        data.scope1_co2e_tonnes,
        data.scope2_co2e_tonnes,
        data.water_usage_m3,
        data.waste_recycled_pct,
    ]
    env_disclosed = sum(1 for x in env_items if x is not None)
    env_score = env_disclosed / len(env_items)

    # GRI 400 社会
    soc_items = [data.total_employees, data.female_pct]
    soc_disclosed = sum(1 for x in soc_items if x is not None)
    soc_score = soc_disclosed / len(soc_items)

    # GRI 2 治理（基于披露完整度代理）
    gov_score = min(1.0, (env_score * 0.5 + soc_score * 0.5) * 0.9 + 0.1)
    gov_disclosed = int(round(gov_score * 2))

    # GRI 200 经济
    econ_items = [data.total_revenue_eur, data.total_capex_eur]
    econ_disclosed = sum(1 for x in econ_items if x is not None)
    econ_score = econ_disclosed / len(econ_items)

    total = env_score * 0.30 + soc_score * 0.35 + gov_score * 0.20 + econ_score * 0.15

    dimensions = [
        DimensionScore(
            name="GRI 300 Environment",
            score=round(env_score, 3),
            weight=0.30,
            disclosed=env_disclosed,
            total=len(env_items),
            gaps=[],
        ),
        DimensionScore(
            name="GRI 400 Social",
            score=round(soc_score, 3),
            weight=0.35,
            disclosed=soc_disclosed,
            total=len(soc_items),
            gaps=[],
        ),
        DimensionScore(
            name="GRI 2 Governance",
            score=round(gov_score, 3),
            weight=0.20,
            disclosed=gov_disclosed,
            total=2,
            gaps=[],
        ),
        DimensionScore(
            name="GRI 200 Economic",
            score=round(econ_score, 3),
            weight=0.15,
            disclosed=econ_disclosed,
            total=len(econ_items),
            gaps=[],
        ),
    ]

    gaps: list[str] = []
    recs: list[str] = []
    if data.water_usage_m3 is None:
        gaps.append("Water usage (GRI 303) not disclosed")
        recs.append("Disclose water consumption under GRI 303")
    if data.waste_recycled_pct is None:
        gaps.append("Waste recycling rate (GRI 306) missing")
        recs.append("Report waste-to-landfill and recycling rates")
    if data.female_pct is None:
        gaps.append("Gender diversity ratio (GRI 405) missing")
        recs.append("Disclose gender distribution across employee levels")

    coverage_fields = env_items + soc_items + econ_items
    coverage_pct = sum(1 for f in coverage_fields if f is not None) / len(coverage_fields) * 100

    return FrameworkScoreResult(
        framework_id="gri_universal",
        framework="GRI Universal Standards 2021",
        framework_region="US",
        company_name=data.company_name,
        report_year=data.report_year,
        total_score=round(total, 3),
        grade=_grade(total),
        dimensions=dimensions,
        gaps=gaps,
        recommendations=recs,
        coverage_pct=round(coverage_pct, 1),
    )

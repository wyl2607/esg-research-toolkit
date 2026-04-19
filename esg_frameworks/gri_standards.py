"""
GRI Universal Standards 2021 评分器。
"""
from __future__ import annotations

from core.schemas import CompanyESGData
from .schemas import FRAMEWORK_VERSIONS
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


def score(data: CompanyESGData) -> FrameworkScoreResult:
    # GRI 300 Environment
    env_items = [
        ("Energy consumption", data.energy_consumption_mwh is not None),
        ("Renewable energy ratio", data.renewable_energy_pct is not None),
        ("Scope 1 emissions", data.scope1_co2e_tonnes is not None),
        ("Scope 2 emissions", data.scope2_co2e_tonnes is not None),
        ("Water usage", data.water_usage_m3 is not None),
        ("Waste recycled ratio", data.waste_recycled_pct is not None),
    ]
    env_disclosed = sum(1 for _, ok in env_items if ok)
    env_score = env_disclosed / len(env_items)

    # GRI 400 Social
    soc_items = [
        ("Total employees", data.total_employees is not None),
        ("Female workforce ratio", data.female_pct is not None),
    ]
    soc_disclosed = sum(1 for _, ok in soc_items if ok)
    soc_score = soc_disclosed / len(soc_items)

    # GRI 2 Governance（披露完整度代理）
    gov_score = min(1.0, (env_score * 0.5 + soc_score * 0.5) * 0.9 + 0.1)

    # GRI 200 Economic
    econ_items = [
        ("Total revenue", data.total_revenue_eur is not None),
        ("Total CapEx", data.total_capex_eur is not None),
    ]
    econ_disclosed = sum(1 for _, ok in econ_items if ok)
    econ_score = econ_disclosed / len(econ_items)

    weights = {"env": 0.30, "soc": 0.35, "gov": 0.20, "econ": 0.15}
    total = (
        env_score * weights["env"]
        + soc_score * weights["soc"]
        + gov_score * weights["gov"]
        + econ_score * weights["econ"]
    )

    gaps: list[str] = []
    recommendations: list[str] = []
    if data.water_usage_m3 is None:
        gaps.append("Water usage (GRI 303) not disclosed")
        recommendations.append("Disclose water consumption under GRI 303")
    if data.waste_recycled_pct is None:
        gaps.append("Waste recycling rate (GRI 306) missing")
        recommendations.append("Disclose recycling and landfill metrics")
    if data.female_pct is None:
        gaps.append("Gender diversity ratio (GRI 405) missing")
        recommendations.append("Disclose workforce diversity by level")

    dimensions = [
        DimensionScore(
            name="GRI 300 Environment",
            score=round(env_score, 3),
            weight=weights["env"],
            disclosed=env_disclosed,
            total=len(env_items),
            gaps=[g for g in gaps if "GRI 3" in g or "Water" in g or "Waste" in g],
        ),
        DimensionScore(
            name="GRI 400 Social",
            score=round(soc_score, 3),
            weight=weights["soc"],
            disclosed=soc_disclosed,
            total=len(soc_items),
            gaps=[g for g in gaps if "Gender" in g],
        ),
        DimensionScore(
            name="GRI 2 Governance",
            score=round(gov_score, 3),
            weight=weights["gov"],
            disclosed=1 if gov_score > 0 else 0,
            total=1,
            gaps=[],
        ),
        DimensionScore(
            name="GRI 200 Economic",
            score=round(econ_score, 3),
            weight=weights["econ"],
            disclosed=econ_disclosed,
            total=len(econ_items),
            gaps=[],
        ),
    ]

    coverage_items = env_items + soc_items + econ_items
    coverage_pct = sum(1 for _, ok in coverage_items if ok) / len(coverage_items) * 100

    return FrameworkScoreResult(
        framework="GRI Universal Standards 2021",
        framework_id="gri_universal",
        framework_region="US",
        framework_version=FRAMEWORK_VERSIONS["gri_universal"],
        company_name=data.company_name,
        report_year=data.report_year,
        total_score=round(total, 3),
        grade=_grade(total),
        dimensions=dimensions,
        gaps=gaps,
        recommendations=recommendations,
        coverage_pct=round(coverage_pct, 1),
    )


def score_gri(data: CompanyESGData) -> FrameworkScoreResult:
    return score(data)

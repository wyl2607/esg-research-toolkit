"""
SASB 行业标准评分器（简化通用版本）。
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
    env_items = [
        ("Scope 1 emissions", data.scope1_co2e_tonnes is not None),
        ("Scope 2 emissions", data.scope2_co2e_tonnes is not None),
        ("Energy consumption", data.energy_consumption_mwh is not None),
        ("Renewable energy ratio", data.renewable_energy_pct is not None),
    ]
    env_disclosed = sum(1 for _, ok in env_items if ok)
    env_score = env_disclosed / len(env_items)

    soc_items = [
        ("Total employees", data.total_employees is not None),
        ("Female workforce ratio", data.female_pct is not None),
    ]
    soc_disclosed = sum(1 for _, ok in soc_items if ok)
    soc_score = soc_disclosed / len(soc_items)
    if data.renewable_energy_pct is not None and data.renewable_energy_pct > 50:
        soc_score = min(1.0, soc_score + 0.1)

    biz_items = [
        ("Total revenue", data.total_revenue_eur is not None),
        ("Total CapEx", data.total_capex_eur is not None),
        ("Sustainable CapEx ratio", data.taxonomy_aligned_capex_pct is not None),
    ]
    biz_disclosed = sum(1 for _, ok in biz_items if ok)
    biz_score = biz_disclosed / len(biz_items)
    if data.taxonomy_aligned_capex_pct is not None and data.taxonomy_aligned_capex_pct > 20:
        biz_score = min(1.0, biz_score + 0.1)

    weights = {"env": 0.35, "soc": 0.40, "biz": 0.25}
    total = env_score * weights["env"] + soc_score * weights["soc"] + biz_score * weights["biz"]

    gaps: list[str] = []
    recommendations: list[str] = []
    if data.scope1_co2e_tonnes is None or data.scope2_co2e_tonnes is None:
        gaps.append("SASB requires Scope 1 & Scope 2 emissions disclosure")
        recommendations.append("Report Scope 1/2 absolute emissions under SASB metrics")
    if data.female_pct is None:
        gaps.append("SASB workforce diversity metrics missing")
        recommendations.append("Disclose gender and diversity metrics")
    if data.taxonomy_aligned_capex_pct is None:
        gaps.append("Sustainable CapEx ratio not quantified")
        recommendations.append("Quantify sustainable investment ratio in capital allocation")

    dimensions = [
        DimensionScore(
            name="Environmental Footprint",
            score=round(env_score, 3),
            weight=weights["env"],
            disclosed=env_disclosed,
            total=len(env_items),
            gaps=[g for g in gaps if "Scope" in g],
        ),
        DimensionScore(
            name="Social Capital",
            score=round(soc_score, 3),
            weight=weights["soc"],
            disclosed=soc_disclosed,
            total=len(soc_items),
            gaps=[g for g in gaps if "workforce" in g.lower()],
        ),
        DimensionScore(
            name="Business Model Resilience",
            score=round(biz_score, 3),
            weight=weights["biz"],
            disclosed=biz_disclosed,
            total=len(biz_items),
            gaps=[g for g in gaps if "CapEx" in g],
        ),
    ]

    coverage_items = env_items + soc_items + biz_items
    coverage_pct = sum(1 for _, ok in coverage_items if ok) / len(coverage_items) * 100

    return FrameworkScoreResult(
        framework="SASB Industry Standards",
        framework_id="sasb_standards",
        framework_region="US",
        framework_version=FRAMEWORK_VERSIONS["sasb_standards"],
        company_name=data.company_name,
        report_year=data.report_year,
        total_score=round(total, 3),
        grade=_grade(total),
        dimensions=dimensions,
        gaps=gaps,
        recommendations=recommendations,
        coverage_pct=round(coverage_pct, 1),
    )


def score_sasb(data: CompanyESGData) -> FrameworkScoreResult:
    return score(data)

"""
美国 SEC 气候信息披露规则（2024 最终版）评分器。
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


def score(data: CompanyESGData) -> FrameworkScoreResult:
    # 维度 1：气候风险披露（Scope 1/2/3）
    risk_items = [
        ("Scope 1 disclosed", data.scope1_co2e_tonnes is not None),
        ("Scope 2 disclosed", data.scope2_co2e_tonnes is not None),
        ("Scope 3 disclosed or materiality evaluated", data.scope3_co2e_tonnes is not None),
    ]
    risk_disclosed = sum(1 for _, ok in risk_items if ok)
    risk_score = risk_disclosed / len(risk_items)

    # 维度 2：GHG 披露完整度（Scope 1/2 为核心，Scope 3 为补充）
    ghg_score = 0.0
    ghg_disclosed = 0
    if data.scope1_co2e_tonnes is not None:
        ghg_score += 0.5
        ghg_disclosed += 1
    if data.scope2_co2e_tonnes is not None:
        ghg_score += 0.3
        ghg_disclosed += 1
    if data.scope3_co2e_tonnes is not None:
        ghg_score += 0.2
        ghg_disclosed += 1

    # 维度 3：财务影响披露
    fin_items = [
        ("Climate-related CapEx ratio", data.taxonomy_aligned_capex_pct is not None and data.taxonomy_aligned_capex_pct > 0),
        ("Total CapEx disclosed", data.total_capex_eur is not None),
    ]
    fin_disclosed = sum(1 for _, ok in fin_items if ok)
    fin_score = fin_disclosed / len(fin_items)

    weights = {"risk": 0.40, "ghg": 0.35, "fin": 0.25}
    total = risk_score * weights["risk"] + ghg_score * weights["ghg"] + fin_score * weights["fin"]

    gaps: list[str] = []
    recommendations: list[str] = []
    if data.scope1_co2e_tonnes is None:
        gaps.append("Scope 1 emissions not disclosed (SEC baseline requirement)")
        recommendations.append("Quantify and disclose Scope 1 emissions")
    if data.scope2_co2e_tonnes is None:
        gaps.append("Scope 2 emissions not disclosed (SEC baseline requirement)")
        recommendations.append("Quantify and disclose Scope 2 emissions")
    if data.scope3_co2e_tonnes is None:
        gaps.append("Scope 3 materiality assessment/disclosure missing")
        recommendations.append("Assess Scope 3 materiality and disclose when material")
    if data.taxonomy_aligned_capex_pct is None or data.taxonomy_aligned_capex_pct <= 0:
        gaps.append("Climate-related CapEx ratio not disclosed")
        recommendations.append("Disclose transition-related CapEx ratio")

    dimensions = [
        DimensionScore(
            name="Climate Risk Disclosure",
            score=round(risk_score, 3),
            weight=weights["risk"],
            disclosed=risk_disclosed,
            total=len(risk_items),
            gaps=[g for g in gaps if "Scope" in g],
        ),
        DimensionScore(
            name="GHG Reporting",
            score=round(ghg_score, 3),
            weight=weights["ghg"],
            disclosed=ghg_disclosed,
            total=3,
            gaps=[g for g in gaps if "Scope" in g],
        ),
        DimensionScore(
            name="Financial Impact",
            score=round(fin_score, 3),
            weight=weights["fin"],
            disclosed=fin_disclosed,
            total=len(fin_items),
            gaps=[g for g in gaps if "CapEx" in g],
        ),
    ]

    coverage_items = [
        data.scope1_co2e_tonnes,
        data.scope2_co2e_tonnes,
        data.scope3_co2e_tonnes,
        data.taxonomy_aligned_capex_pct if data.taxonomy_aligned_capex_pct and data.taxonomy_aligned_capex_pct > 0 else None,
        data.total_capex_eur,
    ]
    coverage_pct = sum(1 for item in coverage_items if item is not None) / len(coverage_items) * 100

    return FrameworkScoreResult(
        framework="SEC Climate Disclosure",
        framework_id="sec_climate",
        framework_region="US",
        framework_version="SEC-2024",
        company_name=data.company_name,
        report_year=data.report_year,
        total_score=round(total, 3),
        grade=_grade(total),
        dimensions=dimensions,
        gaps=gaps,
        recommendations=recommendations,
        coverage_pct=round(coverage_pct, 1),
    )


def score_sec_climate(data: CompanyESGData) -> FrameworkScoreResult:
    return score(data)

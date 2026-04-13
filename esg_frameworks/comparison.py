"""
三地 ESG 框架横向对比引擎
输出：RegionalComparisonReport（按 EU/CN/US 区域分组 + 维度交叉矩阵 + 合规优先级）
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.schemas import CompanyESGData
from esg_frameworks.schemas import FrameworkScoreResult


@dataclass
class RegionalGroup:
    region: str  # "EU" | "CN" | "US" | "Global"
    frameworks: list[FrameworkScoreResult]
    avg_score: float
    avg_grade: str
    strongest_area: str  # 最高维度名称
    weakest_area: str  # 最低维度名称


@dataclass
class DimensionCrossMatrix:
    """同一指标在不同地区框架中的要求对比"""

    dimension_name: str  # "Carbon Emissions" / "Social" / "Governance"
    eu_requirement: str  # 描述 EU 要求
    cn_requirement: str
    us_requirement: str
    eu_score: Optional[float]  # 公司当前得分（该维度）
    cn_score: Optional[float]
    us_score: Optional[float]
    gap_analysis: str  # 综合差距描述


@dataclass
class RegionalComparisonReport:
    company_name: str
    report_year: int
    regional_groups: list[RegionalGroup]
    cross_matrix: list[DimensionCrossMatrix]
    compliance_priority: list[str]  # 有序列表，最紧迫在前
    overall_readiness: str  # "Low" / "Medium" / "High" / "Leading"
    key_insights: list[str]  # 3–5 条核心洞察


def _avg_grade(avg: float) -> str:
    if avg >= 0.85:
        return "A"
    if avg >= 0.70:
        return "B"
    if avg >= 0.55:
        return "C"
    if avg >= 0.40:
        return "D"
    return "F"


def _find_extremes(frameworks: list[FrameworkScoreResult]) -> tuple[str, str]:
    """返回最高/最低维度名称"""
    all_dims = [d for f in frameworks for d in f.dimensions]
    if not all_dims:
        return ("N/A", "N/A")
    best = max(all_dims, key=lambda d: d.score * d.weight)
    worst = min(all_dims, key=lambda d: d.score * d.weight)
    return best.name, worst.name


def build_comparison(
    data: CompanyESGData,
    results: list[FrameworkScoreResult],
) -> RegionalComparisonReport:
    # 按区域分组
    region_map: dict[str, list[FrameworkScoreResult]] = {}
    for r in results:
        region_map.setdefault(r.framework_region, []).append(r)

    groups = []
    for region, frameworks in region_map.items():
        avg = sum(f.total_score for f in frameworks) / len(frameworks)
        strongest, weakest = _find_extremes(frameworks)
        groups.append(
            RegionalGroup(
                region=region,
                frameworks=frameworks,
                avg_score=round(avg, 3),
                avg_grade=_avg_grade(avg),
                strongest_area=strongest,
                weakest_area=weakest,
            )
        )
    groups.sort(key=lambda g: g.avg_score, reverse=True)

    # 维度交叉矩阵（固定三轴）
    cross_matrix = [
        DimensionCrossMatrix(
            dimension_name="Carbon Emissions",
            eu_requirement="Scope 1/2/3 + DNSH climate thresholds (EU Taxonomy Art.17)",
            cn_requirement="Scope 1/2 mandatory; Scope 3 encouraged (CSRC 2023 §4.3)",
            us_requirement="Scope 1/2 mandatory; Scope 3 if material (SEC 2024)",
            eu_score=_get_dim_score(results, ["eu_taxonomy", "csrd"], "emission"),
            cn_score=_get_dim_score(results, ["csrc_2023"], "emission"),
            us_score=_get_dim_score(results, ["sec_climate"], "GHG"),
            gap_analysis=_emission_gap(data),
        ),
        DimensionCrossMatrix(
            dimension_name="Social & Labor",
            eu_requirement="S1 workforce disclosure, equal pay gap, safety incidents (CSRD ESRS S1)",
            cn_requirement="Employee headcount, female ratio, training hours (CSRC 2023 §5)",
            us_requirement="GRI 400 workforce safety & diversity; SASB sector-specific metrics",
            eu_score=_get_dim_score(results, ["csrd"], "Social"),
            cn_score=_get_dim_score(results, ["csrc_2023"], "社会"),
            us_score=_get_dim_score(results, ["gri_universal", "sasb_standards"], "Social"),
            gap_analysis=_social_gap(data),
        ),
        DimensionCrossMatrix(
            dimension_name="Governance & Transparency",
            eu_requirement="Board composition, remuneration policy, anti-corruption (CSRD ESRS G1)",
            cn_requirement="ESG committee, risk management disclosure (CSRC 2023 §6)",
            us_requirement="GRI 2 general disclosures, SASB business ethics metrics",
            eu_score=_get_dim_score(results, ["csrd"], "Governance"),
            cn_score=_get_dim_score(results, ["csrc_2023"], "治理"),
            us_score=_get_dim_score(results, ["gri_universal"], "Governance"),
            gap_analysis="Governance disclosure completeness varies by market listing requirements.",
        ),
    ]

    # 合规优先级
    priority = []
    for g in sorted(groups, key=lambda x: x.avg_score):
        for f in sorted(g.frameworks, key=lambda x: x.total_score):
            if f.total_score < 0.55:
                priority.append(
                    f"{f.framework} ({f.framework_region}) — current grade {f.grade}"
                )

    # 整体准备度
    all_scores = [r.total_score for r in results]
    overall_avg = sum(all_scores) / len(all_scores) if all_scores else 0
    if overall_avg >= 0.80:
        readiness = "Leading"
    elif overall_avg >= 0.60:
        readiness = "High"
    elif overall_avg >= 0.40:
        readiness = "Medium"
    else:
        readiness = "Low"

    # 核心洞察
    insights = _generate_insights(data, groups, results)

    return RegionalComparisonReport(
        company_name=data.company_name,
        report_year=data.report_year,
        regional_groups=groups,
        cross_matrix=cross_matrix,
        compliance_priority=priority[:5],
        overall_readiness=readiness,
        key_insights=insights,
    )


def _get_dim_score(
    results: list[FrameworkScoreResult],
    framework_ids: list[str],
    keyword: str,
) -> Optional[float]:
    scores = []
    for r in results:
        if r.framework_id in framework_ids:
            for d in r.dimensions:
                if keyword.lower() in d.name.lower():
                    scores.append(d.score * d.weight)
    return round(sum(scores) / len(scores), 3) if scores else None


def _emission_gap(data: CompanyESGData) -> str:
    missing = []
    if data.scope1_co2e_tonnes is None:
        missing.append("Scope 1")
    if data.scope2_co2e_tonnes is None:
        missing.append("Scope 2")
    if data.scope3_co2e_tonnes is None:
        missing.append("Scope 3")
    if not missing:
        return "All three scopes disclosed — meets EU/CN/US baseline emission reporting."
    return f"Missing: {', '.join(missing)}. Required across all three jurisdictions."


def _social_gap(data: CompanyESGData) -> str:
    if data.total_employees and data.female_pct:
        return (
            f"{data.total_employees:,} employees, {data.female_pct:.1f}% female — "
            "baseline social disclosure met."
        )
    return "Workforce size and/or gender diversity not disclosed — gaps across CN/EU/US social standards."


def _generate_insights(
    data: CompanyESGData,
    groups: list[RegionalGroup],
    results: list[FrameworkScoreResult],
) -> list[str]:
    insights = []
    if groups:
        best = groups[0]
        worst = groups[-1]
        if best.region != worst.region:
            insights.append(
                f"Strongest compliance: {best.region} frameworks (avg {best.avg_score:.0%}); "
                f"widest gap: {worst.region} (avg {worst.avg_score:.0%})."
            )
    if data.scope3_co2e_tonnes is None:
        insights.append(
            "Scope 3 disclosure absent — this is becoming mandatory in EU (CSRD) and material under SEC rules."
        )
    if data.renewable_energy_pct and data.renewable_energy_pct > 50:
        insights.append(
            f"Renewable energy share ({data.renewable_energy_pct:.0f}%) exceeds EU Taxonomy climate threshold — strong DNSH positioning."
        )
    if data.taxonomy_aligned_capex_pct and data.taxonomy_aligned_capex_pct > 30:
        insights.append(
            f"Taxonomy-aligned CapEx ({data.taxonomy_aligned_capex_pct:.0f}%) demonstrates credible transition investment."
        )
    if not insights:
        insights.append(
            "Increase structured ESG disclosures to improve cross-jurisdictional compliance scores."
        )
    return insights[:5]

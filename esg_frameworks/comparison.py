"""三地 ESG 框架横向对比引擎。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.schemas import CompanyESGData
from esg_frameworks.schemas import FrameworkScoreResult


EU_FRAMEWORK_IDS = {"eu_taxonomy", "csrd", "esrs", "eu_csrd"}
CN_FRAMEWORK_IDS = {"csrc_2023", "szse", "sse"}
US_FRAMEWORK_IDS = {"sec_climate", "gri_universal", "sasb_standards", "sec"}
CORE_REGIONS = ("EU", "CN", "US")


@dataclass
class RegionalGroup:
    region: str
    frameworks: list[FrameworkScoreResult]
    avg_score: float
    avg_grade: str
    strongest_area: str
    weakest_area: str


@dataclass
class DimensionCrossMatrix:
    """同一指标在不同地区框架中的要求对比。"""

    dimension_name: str
    eu_requirement: str
    cn_requirement: str
    us_requirement: str
    eu_score: Optional[float]
    cn_score: Optional[float]
    us_score: Optional[float]
    gap_analysis: str


@dataclass
class RegionalComparisonReport:
    company_name: str
    report_year: int
    regional_groups: list[RegionalGroup]
    cross_matrix: list[DimensionCrossMatrix]
    compliance_priority: list[str]
    overall_readiness: str
    key_insights: list[str]


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


def _region_for_framework(framework_id: str) -> str:
    if framework_id in EU_FRAMEWORK_IDS:
        return "EU"
    if framework_id in CN_FRAMEWORK_IDS:
        return "CN"
    if framework_id in US_FRAMEWORK_IDS:
        return "US"
    return "Global"


def _find_extremes(frameworks: list[FrameworkScoreResult]) -> tuple[str, str]:
    all_dims = [d for framework in frameworks for d in framework.dimensions]
    if not all_dims:
        return ("N/A", "N/A")
    best = max(all_dims, key=lambda d: d.score * d.weight)
    worst = min(all_dims, key=lambda d: d.score * d.weight)
    return best.name, worst.name


def _get_dim_score(
    results: list[FrameworkScoreResult],
    framework_ids: list[str],
    keyword: str,
) -> Optional[float]:
    scores: list[float] = []
    keyword_lower = keyword.lower()
    for result in results:
        if result.framework_id not in framework_ids:
            continue
        for dimension in result.dimensions:
            if keyword_lower in dimension.name.lower():
                scores.append(dimension.score * dimension.weight)
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
    if data.total_employees and data.female_pct is not None:
        return (
            f"{data.total_employees:,} employees, {data.female_pct:.1f}% female — "
            "baseline social disclosure met."
        )
    return "Workforce size and/or gender diversity not disclosed — gaps across CN/EU/US social standards."


def _generate_insights(
    data: CompanyESGData,
    groups: list[RegionalGroup],
) -> list[str]:
    insights: list[str] = []

    non_empty_groups = [group for group in groups if group.frameworks]
    if non_empty_groups:
        best = max(non_empty_groups, key=lambda group: group.avg_score)
        worst = min(non_empty_groups, key=lambda group: group.avg_score)
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
            f"Renewable energy share ({data.renewable_energy_pct:.0f}%) exceeds key climate thresholds and supports transition narratives."
        )
    if data.taxonomy_aligned_capex_pct and data.taxonomy_aligned_capex_pct > 30:
        insights.append(
            f"Taxonomy-aligned CapEx ({data.taxonomy_aligned_capex_pct:.0f}%) demonstrates credible transition investment."
        )
    if not insights:
        insights.append("Increase structured ESG disclosures to improve cross-jurisdictional compliance scores.")
    return insights[:5]


def build_comparison(
    data: CompanyESGData,
    results: list[FrameworkScoreResult],
) -> RegionalComparisonReport:
    region_map: dict[str, list[FrameworkScoreResult]] = {region: [] for region in CORE_REGIONS}
    for result in results:
        region = _region_for_framework(result.framework_id)
        region_map.setdefault(region, []).append(result)

    groups: list[RegionalGroup] = []
    for region, frameworks in region_map.items():
        avg = sum(item.total_score for item in frameworks) / len(frameworks) if frameworks else 0.0
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

    groups.sort(key=lambda group: group.avg_score, reverse=True)

    cross_matrix = [
        DimensionCrossMatrix(
            dimension_name="Carbon Emissions",
            eu_requirement="Scope 1/2/3 + DNSH climate thresholds (EU Taxonomy Art.17)",
            cn_requirement="Scope 1/2 mandatory; Scope 3 encouraged (CSRC 2023 §4.3)",
            us_requirement="Scope 1/2 mandatory; Scope 3 if material (SEC 2024)",
            eu_score=_get_dim_score(results, ["eu_taxonomy", "csrd"], "emission"),
            cn_score=_get_dim_score(results, ["csrc_2023"], "emission"),
            us_score=_get_dim_score(results, ["sec_climate", "gri_universal", "sasb_standards"], "GHG"),
            gap_analysis=_emission_gap(data),
        ),
        DimensionCrossMatrix(
            dimension_name="Social & Labor",
            eu_requirement="S1 workforce disclosure, equal pay gap, safety incidents (CSRD ESRS S1)",
            cn_requirement="Employee headcount, female ratio, training hours (CSRC 2023 §5)",
            us_requirement="GRI 400 workforce safety & diversity; SASB sector-specific metrics",
            eu_score=_get_dim_score(results, ["csrd"], "social"),
            cn_score=_get_dim_score(results, ["csrc_2023"], "社会"),
            us_score=_get_dim_score(results, ["gri_universal", "sasb_standards"], "social"),
            gap_analysis=_social_gap(data),
        ),
        DimensionCrossMatrix(
            dimension_name="Governance & Transparency",
            eu_requirement="Board composition, remuneration policy, anti-corruption (CSRD ESRS G1)",
            cn_requirement="ESG committee, risk management disclosure (CSRC 2023 §6)",
            us_requirement="GRI 2 general disclosures, SASB business ethics metrics",
            eu_score=_get_dim_score(results, ["csrd"], "governance"),
            cn_score=_get_dim_score(results, ["csrc_2023"], "治理"),
            us_score=_get_dim_score(results, ["gri_universal", "sasb_standards"], "governance"),
            gap_analysis="Governance disclosure completeness varies by market listing requirements.",
        ),
    ]

    compliance_priority: list[str] = []
    for group in sorted(groups, key=lambda item: item.avg_score):
        for framework in sorted(group.frameworks, key=lambda item: item.total_score):
            if framework.total_score < 0.55:
                compliance_priority.append(
                    f"{framework.framework} ({group.region}) — current grade {framework.grade}"
                )

    all_scores = [result.total_score for result in results]
    overall_avg = sum(all_scores) / len(all_scores) if all_scores else 0
    if overall_avg >= 0.80:
        readiness = "Leading"
    elif overall_avg >= 0.60:
        readiness = "High"
    elif overall_avg >= 0.40:
        readiness = "Medium"
    else:
        readiness = "Low"

    return RegionalComparisonReport(
        company_name=data.company_name,
        report_year=data.report_year,
        regional_groups=groups,
        cross_matrix=cross_matrix,
        compliance_priority=compliance_priority[:5],
        overall_readiness=readiness,
        key_insights=_generate_insights(data, groups),
    )

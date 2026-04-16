from core.schemas import CompanyESGData, TaxonomyScoreResult
from taxonomy_scorer.gap_analyzer import GapItem
from taxonomy_scorer.scorer import get_metric_framework_mappings


def generate_json_report(
    data: CompanyESGData,
    result: TaxonomyScoreResult,
    gaps: list[GapItem],
) -> dict:
    return {
        "company": data.company_name,
        "report_year": data.report_year,
        "taxonomy_alignment": {
            "revenue_aligned_pct": result.revenue_aligned_pct,
            "capex_aligned_pct": result.capex_aligned_pct,
            "opex_aligned_pct": result.opex_aligned_pct,
        },
        "objective_scores": result.objective_scores,
        "dnsh_pass": result.dnsh_pass,
        "gaps": [
            {
                "objective": gap.objective,
                "severity": gap.severity,
                "description": gap.description,
                "action": gap.action,
            }
            for gap in gaps
        ],
        "recommendations": result.recommendations,
        "metric_framework_mappings": {
            metric: [
                mapping.model_dump()
                for mapping in get_metric_framework_mappings(metric)
            ]
            for metric in (
                "scope1_co2e_tonnes",
                "scope2_co2e_tonnes",
                "scope3_co2e_tonnes",
                "energy_consumption_mwh",
                "renewable_energy_pct",
                "water_usage_m3",
                "waste_recycled_pct",
                "taxonomy_aligned_revenue_pct",
                "taxonomy_aligned_capex_pct",
                "total_employees",
                "female_pct",
                "primary_activities",
            )
            if getattr(data, metric, None) not in (None, [])
        },
    }


def generate_text_summary(result: TaxonomyScoreResult, gaps: list[GapItem]) -> str:
    lines = [
        f"EU Taxonomy Alignment Report - {result.company_name} ({result.report_year})",
        "=" * 60,
        f"Revenue Aligned:  {result.revenue_aligned_pct:.1f}%",
        f"CapEx Aligned:    {result.capex_aligned_pct:.1f}%",
        f"OpEx Aligned:     {result.opex_aligned_pct:.1f}%",
        f"DNSH Pass:        {'Yes' if result.dnsh_pass else 'No'}",
        "",
        "Objective Scores:",
    ]
    for objective, score in result.objective_scores.items():
        bar = "#" * int(score * 10) + "." * (10 - int(score * 10))
        lines.append(f"  {objective:<25} {bar} {score:.0%}")

    lines += ["", f"Gaps identified: {len(gaps)}", ""]
    critical = [gap for gap in gaps if gap.severity == "critical"]
    if critical:
        lines.append("Critical gaps:")
        for gap in critical:
            lines.append(f"  x {gap.description}")
            lines.append(f"    -> {gap.action}")

    lines += ["", "Recommendations:"]
    for recommendation in result.recommendations:
        lines.append(f"  - {recommendation}")

    return "\n".join(lines)

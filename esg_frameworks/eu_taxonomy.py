"""
EU Taxonomy 2020 框架适配器
将现有 taxonomy_scorer 的结果转换为统一 FrameworkScoreResult 格式。
"""
from __future__ import annotations

from core.schemas import CompanyESGData
from esg_frameworks.schemas import DimensionScore, FrameworkScoreResult
from taxonomy_scorer.gap_analyzer import analyze_gaps
from taxonomy_scorer.reporter import generate_json_report
from taxonomy_scorer.scorer import score_company


def _grade(score: float) -> str:
    if score >= 0.8:
        return "A"
    if score >= 0.6:
        return "B"
    if score >= 0.4:
        return "C"
    if score >= 0.2:
        return "D"
    return "F"


def score(data: CompanyESGData) -> FrameworkScoreResult:
    result = score_company(data)
    gaps = analyze_gaps(data, result)
    report = generate_json_report(data, result, gaps)

    obj_scores = result.objective_scores  # dict[str, float]

    # 六大目标 → DimensionScore
    objective_labels = {
        "climate_mitigation": "气候减缓 (Climate Mitigation)",
        "climate_adaptation": "气候适应 (Climate Adaptation)",
        "water": "水资源 (Water & Marine)",
        "circular_economy": "循环经济 (Circular Economy)",
        "pollution": "污染防治 (Pollution Prevention)",
        "biodiversity": "生物多样性 (Biodiversity)",
    }
    dimensions: list[DimensionScore] = []
    for key, label in objective_labels.items():
        s = obj_scores.get(key, 0.0)
        dimensions.append(DimensionScore(
            name=label,
            score=s,
            weight=1 / 6,
            disclosed=1 if s > 0 else 0,
            total=1,
        ))

    total = sum(d.score * d.weight for d in dimensions)
    coverage_fields = [
        data.scope1_co2e_tonnes, data.scope2_co2e_tonnes,
        data.energy_consumption_mwh, data.renewable_energy_pct,
        data.water_usage_m3, data.waste_recycled_pct,
    ]
    coverage_pct = sum(1 for f in coverage_fields if f is not None) / len(coverage_fields) * 100

    raw_gaps = report.get("gaps", [])
    gap_strs = [
        g.get("description", str(g)) if isinstance(g, dict) else str(g)
        for g in raw_gaps
    ]

    raw_recs = report.get("recommendations", [])
    rec_strs = [
        r.get("action", str(r)) if isinstance(r, dict) else str(r)
        for r in raw_recs
    ]

    return FrameworkScoreResult(
        framework="EU Taxonomy 2020",
        framework_id="eu_taxonomy",
        framework_region="EU",
        company_name=data.company_name,
        report_year=data.report_year,
        total_score=round(total, 3),
        grade=_grade(total),
        dimensions=dimensions,
        gaps=gap_strs,
        recommendations=rec_strs,
        coverage_pct=round(coverage_pct, 1),
    )

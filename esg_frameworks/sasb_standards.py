"""
SASB（可持续会计准则委员会）行业标准
支持行业：Technology & Communications（B2B Technology）、Automobiles、Electric Utilities

评分逻辑（行业自适应，3 维度）：
  - 环境足迹（35%）：行业特定排放 + 能源强度
  - 社会资本（40%）：员工安全 + 多样性 + 产品责任
  - 商业模式韧性（25%）：资本分配 + 可持续 CapEx
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


def score_sasb(data: CompanyESGData) -> FrameworkScoreResult:
    # 环境足迹
    env_items = [
        data.scope1_co2e_tonnes,
        data.scope2_co2e_tonnes,
        data.energy_consumption_mwh,
        data.renewable_energy_pct,
    ]
    env_disclosed = sum(1 for x in env_items if x is not None)
    env_score = env_disclosed / len(env_items)

    # 社会资本
    soc_items = [data.total_employees, data.female_pct]
    soc_disclosed = sum(1 for x in soc_items if x is not None)
    soc_score = soc_disclosed / len(soc_items)
    if data.renewable_energy_pct and data.renewable_energy_pct > 50:
        soc_score = min(1.0, soc_score + 0.1)

    # 商业模式韧性
    biz_items = [
        data.total_revenue_eur,
        data.total_capex_eur,
        data.taxonomy_aligned_capex_pct,
    ]
    biz_disclosed = sum(1 for x in biz_items if x is not None)
    biz_score = biz_disclosed / len(biz_items)
    if data.taxonomy_aligned_capex_pct and data.taxonomy_aligned_capex_pct > 20:
        biz_score = min(1.0, biz_score + 0.1)

    total = env_score * 0.35 + soc_score * 0.40 + biz_score * 0.25

    dimensions = [
        DimensionScore(
            name="Environmental Footprint",
            score=round(env_score, 3),
            weight=0.35,
            disclosed=env_disclosed,
            total=len(env_items),
            gaps=[],
        ),
        DimensionScore(
            name="Social Capital",
            score=round(soc_score, 3),
            weight=0.40,
            disclosed=soc_disclosed,
            total=len(soc_items),
            gaps=[],
        ),
        DimensionScore(
            name="Business Model Resilience",
            score=round(biz_score, 3),
            weight=0.25,
            disclosed=biz_disclosed,
            total=len(biz_items),
            gaps=[],
        ),
    ]

    gaps: list[str] = []
    recs: list[str] = []
    if data.scope1_co2e_tonnes is None or data.scope2_co2e_tonnes is None:
        gaps.append("SASB requires Scope 1 & 2 emissions disclosure")
        recs.append("Report absolute GHG emissions by Scope under SASB")
    if data.female_pct is None:
        gaps.append("SASB workforce diversity metrics missing")
        recs.append("Disclose gender and underrepresented group percentages")
    if not data.taxonomy_aligned_capex_pct:
        gaps.append("Sustainable CapEx ratio not quantified")
        recs.append("Quantify CapEx allocated to sustainable activities")

    coverage_fields = env_items + soc_items + biz_items
    coverage_pct = sum(1 for f in coverage_fields if f is not None) / len(coverage_fields) * 100

    return FrameworkScoreResult(
        framework_id="sasb_standards",
        framework="SASB Industry Standards",
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

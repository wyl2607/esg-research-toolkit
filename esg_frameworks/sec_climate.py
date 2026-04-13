"""
美国 SEC 气候信息披露规则（2024 最终版）
适用范围：在美上市公司（含外国私募发行人）

评分逻辑（3 维度）：
  - 气候风险披露（40%）：转型风险、实物风险、情景分析
  - 温室气体排放（35%）：Scope 1/2 + 重大性 Scope 3、验证等级
  - 财务影响（25%）：气候相关财务影响、碳成本核算

总分 = Σ(维度得分 × 权重)，A/B/C/D/F 五档
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


def score_sec_climate(data: CompanyESGData) -> FrameworkScoreResult:
    """SEC climate disclosure scoring in 3 dimensions."""
    # 维度 1：气候风险披露
    risk_score = 0.0
    risk_disclosed = 0
    if data.scope1_co2e_tonnes is not None:
        risk_score += 1 / 3
        risk_disclosed += 1
    if data.scope2_co2e_tonnes is not None:
        risk_score += 1 / 3
        risk_disclosed += 1
    if data.scope3_co2e_tonnes is not None:
        risk_score += 1 / 3
        risk_disclosed += 1

    # 维度 2：温室气体报告
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

    # 维度 3：财务影响
    fin_score = 0.0
    fin_disclosed = 0
    if data.taxonomy_aligned_capex_pct is not None and data.taxonomy_aligned_capex_pct > 0:
        fin_score += 0.5
        fin_disclosed += 1
    if data.total_capex_eur is not None:
        fin_score += 0.5
        fin_disclosed += 1

    total = risk_score * 0.40 + ghg_score * 0.35 + fin_score * 0.25

    dimensions = [
        DimensionScore(
            name="Climate Risk Disclosure",
            score=round(risk_score, 3),
            weight=0.40,
            disclosed=risk_disclosed,
            total=3,
            gaps=[],
        ),
        DimensionScore(
            name="GHG Reporting",
            score=round(ghg_score, 3),
            weight=0.35,
            disclosed=ghg_disclosed,
            total=3,
            gaps=[],
        ),
        DimensionScore(
            name="Financial Impact",
            score=round(fin_score, 3),
            weight=0.25,
            disclosed=fin_disclosed,
            total=2,
            gaps=[],
        ),
    ]

    gaps: list[str] = []
    recs: list[str] = []
    if data.scope1_co2e_tonnes is None:
        gaps.append("Scope 1 emissions not disclosed (SEC required)")
        recs.append("Quantify and disclose Scope 1 GHG emissions")
    if data.scope3_co2e_tonnes is None:
        gaps.append("Scope 3 materiality assessment missing")
        recs.append("Assess Scope 3 materiality under SEC framework")
    if data.taxonomy_aligned_capex_pct is None or data.taxonomy_aligned_capex_pct == 0:
        gaps.append("No climate-related CapEx disclosed")
        recs.append("Disclose climate transition capital expenditure")

    coverage_fields = [
        data.scope1_co2e_tonnes,
        data.scope2_co2e_tonnes,
        data.scope3_co2e_tonnes,
        data.taxonomy_aligned_capex_pct,
        data.total_capex_eur,
    ]
    coverage_pct = sum(1 for f in coverage_fields if f is not None) / len(coverage_fields) * 100

    return FrameworkScoreResult(
        framework_id="sec_climate",
        framework="SEC Climate Disclosure",
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

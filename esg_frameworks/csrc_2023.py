"""
中国证监会 2023 年《上市公司可持续发展报告指引》
适用范围：沪深 300 指数成分股（2025年起强制）及其他自愿披露上市公司。

评分逻辑：
  - E（环境）：5 项强制披露指标，权重 40%
  - S（社会）：4 项指标（部分建议披露），权重 35%
  - G（治理）：3 项指标，权重 25%
  每维度 = 已披露项 / 总项数（0–1）
  总分 = E×0.4 + S×0.35 + G×0.25
"""
from __future__ import annotations

from core.schemas import CompanyESGData
from esg_frameworks.schemas import DimensionScore, FrameworkScoreResult


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
    gaps: list[str] = []
    recommendations: list[str] = []

    # ── E 维度：环境（5 项强制）───────────────────────────────────────────────
    e_items = [
        ("温室气体排放 Scope 1", data.scope1_co2e_tonnes is not None),
        ("温室气体排放 Scope 2", data.scope2_co2e_tonnes is not None),
        ("能源消耗总量", data.energy_consumption_mwh is not None),
        ("可再生能源比例", data.renewable_energy_pct is not None),
        ("用水总量", data.water_usage_m3 is not None),
    ]
    e_disclosed = sum(1 for _, ok in e_items if ok)
    e_score = e_disclosed / len(e_items)

    for name, ok in e_items:
        if not ok:
            gaps.append(f"[E] 缺失强制披露指标：{name}")
            recommendations.append(f"按 CSRC 2023 要求披露 {name}（A-1/A-2/A-3 章节）")

    if data.scope3_co2e_tonnes is None:
        gaps.append("[E] 建议披露 Scope 3 排放（供应链/产品使用阶段）")

    e_dim = DimensionScore(
        name="环境 (Environment)",
        score=round(e_score, 3),
        weight=0.40,
        disclosed=e_disclosed,
        total=len(e_items),
        gaps=[g for g in gaps if g.startswith("[E]")],
    )

    # ── S 维度：社会（4 项）──────────────────────────────────────────────────
    s_items = [
        ("员工总数", data.total_employees is not None),
        ("女性员工比例", data.female_pct is not None),
        ("工伤事故率（每10万人）", data.safety_incidents_per_100k is not None
         if hasattr(data, "safety_incidents_per_100k") else False),
        ("人均培训时长（小时）", data.training_hours_per_employee is not None
         if hasattr(data, "training_hours_per_employee") else False),
    ]
    s_disclosed = sum(1 for _, ok in s_items if ok)
    s_score = s_disclosed / len(s_items)

    for name, ok in s_items:
        if not ok:
            gaps.append(f"[S] 缺失指标：{name}")
            recommendations.append(f"补充 {name} 数据（CSRC 2023 B 章节）")

    s_dim = DimensionScore(
        name="社会 (Social)",
        score=round(s_score, 3),
        weight=0.35,
        disclosed=s_disclosed,
        total=len(s_items),
        gaps=[g for g in gaps if g.startswith("[S]")],
    )

    # ── G 维度：治理（3 项）──────────────────────────────────────────────────
    g_items = [
        ("董事会独立董事比例", data.board_independence_pct is not None
         if hasattr(data, "board_independence_pct") else False),
        ("反腐败政策披露", False),          # 需要文本字段，当前 schema 未支持
        ("可持续发展委员会设立", False),    # 需要文本字段
    ]
    g_disclosed = sum(1 for _, ok in g_items if ok)
    g_score = g_disclosed / len(g_items)

    for name, ok in g_items:
        if not ok:
            gaps.append(f"[G] 缺失指标：{name}")

    if g_score < 0.5:
        recommendations.append("建议设立董事会可持续发展委员会并披露反腐败政策（CSRC 2023 C 章节）")

    g_dim = DimensionScore(
        name="治理 (Governance)",
        score=round(g_score, 3),
        weight=0.25,
        disclosed=g_disclosed,
        total=len(g_items),
        gaps=[g for g in gaps if g.startswith("[G]")],
    )

    total = e_score * 0.40 + s_score * 0.35 + g_score * 0.25

    # 覆盖率：E 维度强制项
    coverage_pct = e_disclosed / len(e_items) * 100

    return FrameworkScoreResult(
        framework="中国证监会 CSRC 2023",
        framework_id="csrc_2023",
        framework_region="CN",
        framework_version="2023",
        company_name=data.company_name,
        report_year=data.report_year,
        total_score=round(total, 3),
        grade=_grade(total),
        dimensions=[e_dim, s_dim, g_dim],
        gaps=gaps,
        recommendations=recommendations,
        coverage_pct=round(coverage_pct, 1),
    )

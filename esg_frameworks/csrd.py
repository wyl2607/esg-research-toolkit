"""
欧盟 CSRD / ESRS（Corporate Sustainability Reporting Directive）
生效时间：大型上市公司 2024 年报起强制，中型企业 2026 年起。

评分维度（基于 ESRS 披露主题）：
  E1 气候变化   → Scope 1/2/3 + 能源
  E2 污染        → 废弃物回收率
  E3 水资源      → 用水量
  E4 生物多样性  → 暂无直接字段（标记为 N/A）
  E5 循环经济    → 废弃物回收率（与 E2 共用）
  S1 自有员工    → 员工数 + 性别比例
  G1 商业行为    → 治理字段（当前有限支持）
"""
from __future__ import annotations

from core.schemas import CompanyESGData
from .schemas import FRAMEWORK_VERSIONS
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

    # ── E1：气候变化（权重 20%）───────────────────────────────────────────────
    e1_items = [
        ("Scope 1 GHG emissions", data.scope1_co2e_tonnes is not None),
        ("Scope 2 GHG emissions", data.scope2_co2e_tonnes is not None),
        ("Scope 3 GHG emissions", data.scope3_co2e_tonnes is not None),
        ("Energy consumption (MWh)", data.energy_consumption_mwh is not None),
        ("Renewable energy share", data.renewable_energy_pct is not None),
    ]
    e1_score = sum(1 for _, ok in e1_items if ok) / len(e1_items)
    for name, ok in e1_items:
        if not ok:
            gaps.append(f"[E1] Missing: {name} (ESRS E1-6)")
    if e1_score < 0.8:
        recommendations.append("Disclose complete GHG inventory under ESRS E1 (Scope 1, 2 & 3)")

    # ── E2/E5：污染 + 循环经济（权重 10%）───────────────────────────────────
    e2_items = [
        ("Waste recycling rate", data.waste_recycled_pct is not None),
    ]
    e2_score = sum(1 for _, ok in e2_items if ok) / len(e2_items)
    for name, ok in e2_items:
        if not ok:
            gaps.append(f"[E2/E5] Missing: {name} (ESRS E2-4 / E5-5)")

    # ── E3：水资源（权重 10%）─────────────────────────────────────────────────
    e3_items = [
        ("Water consumption (m³)", data.water_usage_m3 is not None),
    ]
    e3_score = sum(1 for _, ok in e3_items if ok) / len(e3_items)
    for name, ok in e3_items:
        if not ok:
            gaps.append(f"[E3] Missing: {name} (ESRS E3-1)")

    # ── E4：生物多样性（权重 10%）─────────────────────────────────────────────
    # 当前无字段支持，固定 0 分并提示
    e4_score = 0.0
    gaps.append("[E4] Biodiversity impact disclosure not yet supported — add site-level data")

    # ── S1：自有员工（权重 25%）──────────────────────────────────────────────
    s1_items = [
        ("Total headcount", data.total_employees is not None),
        ("Gender ratio (female %)", data.female_pct is not None),
        ("Work-related injury rate", data.safety_incidents_per_100k is not None
         if hasattr(data, "safety_incidents_per_100k") else False),
        ("Training hours per employee", data.training_hours_per_employee is not None
         if hasattr(data, "training_hours_per_employee") else False),
    ]
    s1_score = sum(1 for _, ok in s1_items if ok) / len(s1_items)
    for name, ok in s1_items:
        if not ok:
            gaps.append(f"[S1] Missing: {name} (ESRS S1-9/S1-14)")
    if s1_score < 0.75:
        recommendations.append("Expand workforce disclosure: safety incidents + training hours (ESRS S1)")

    # ── G1：商业行为（权重 25%）──────────────────────────────────────────────
    g1_items = [
        ("Board independence %", data.board_independence_pct is not None
         if hasattr(data, "board_independence_pct") else False),
        ("Anti-corruption policy", False),   # 需文本字段
        ("Sustainability governance body", False),
    ]
    g1_score = sum(1 for _, ok in g1_items if ok) / len(g1_items)
    for name, ok in g1_items:
        if not ok:
            gaps.append(f"[G1] Missing: {name} (ESRS G1-1)")
    if g1_score < 0.5:
        recommendations.append("Publish anti-corruption policy and disclose governance body (ESRS G1)")

    # ── 加权总分 ──────────────────────────────────────────────────────────────
    weights = {"e1": 0.20, "e2": 0.10, "e3": 0.10, "e4": 0.10, "s1": 0.25, "g1": 0.25}
    total = (
        e1_score * weights["e1"]
        + e2_score * weights["e2"]
        + e3_score * weights["e3"]
        + e4_score * weights["e4"]
        + s1_score * weights["s1"]
        + g1_score * weights["g1"]
    )

    dimensions = [
        DimensionScore(name="e1_climate", score=round(e1_score, 3),
                       weight=weights["e1"], disclosed=sum(1 for _, ok in e1_items if ok),
                       total=len(e1_items)),
        DimensionScore(name="e2_e5_pollution_circular", score=round(e2_score, 3),
                       weight=weights["e2"], disclosed=sum(1 for _, ok in e2_items if ok),
                       total=len(e2_items)),
        DimensionScore(name="e3_water", score=round(e3_score, 3),
                       weight=weights["e3"], disclosed=sum(1 for _, ok in e3_items if ok),
                       total=len(e3_items)),
        DimensionScore(name="e4_biodiversity", score=0.0,
                       weight=weights["e4"], disclosed=0, total=1),
        DimensionScore(name="s1_workforce", score=round(s1_score, 3),
                       weight=weights["s1"], disclosed=sum(1 for _, ok in s1_items if ok),
                       total=len(s1_items)),
        DimensionScore(name="g1_governance", score=round(g1_score, 3),
                       weight=weights["g1"], disclosed=sum(1 for _, ok in g1_items if ok),
                       total=len(g1_items)),
    ]

    all_items = e1_items + e2_items + e3_items + s1_items + g1_items
    coverage_pct = sum(1 for _, ok in all_items if ok) / len(all_items) * 100

    return FrameworkScoreResult(
        framework="EU CSRD / ESRS",
        framework_id="csrd",
        framework_region="EU",
        framework_version=FRAMEWORK_VERSIONS["csrd"],
        company_name=data.company_name,
        report_year=data.report_year,
        total_score=round(total, 3),
        grade=_grade(total),
        dimensions=dimensions,
        gaps=gaps,
        recommendations=recommendations,
        coverage_pct=round(coverage_pct, 1),
    )

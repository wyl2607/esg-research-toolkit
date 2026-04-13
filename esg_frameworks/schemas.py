from __future__ import annotations

from pydantic import BaseModel


class DimensionScore(BaseModel):
    """单维度得分（E/S/G 或子目标）"""
    name: str
    score: float          # 0.0 – 1.0
    weight: float         # 在总分中的权重
    disclosed: int        # 已披露指标数
    total: int            # 该维度总指标数
    gaps: list[str] = []


class FrameworkScoreResult(BaseModel):
    framework: str            # "EU Taxonomy" | "China CSRC 2023" | "CSRD/ESRS"
    framework_id: str         # "eu_taxonomy" | "csrc_2023" | "csrd"
    company_name: str
    report_year: int
    framework_version: str = "v1"
    analyzed_at: str | None = None
    total_score: float        # 0.0 – 1.0（加权综合）
    grade: str                # A/B/C/D/F
    dimensions: list[DimensionScore]
    gaps: list[str]
    recommendations: list[str]
    coverage_pct: float       # 已披露字段占所有必填字段的百分比


class MultiFrameworkReport(BaseModel):
    company_name: str
    report_year: int
    frameworks: list[FrameworkScoreResult]
    summary: str              # 一段人读的综合判断

from __future__ import annotations

from pydantic import BaseModel, model_validator

LEGACY_FRAMEWORK_VERSION = "v1"

_FRAMEWORK_VERSION_CATALOG: dict[str, tuple[str, str]] = {
    "eu_taxonomy": ("2020/852", "EU Taxonomy"),
    "csrc_2023": ("2023", "China CSRC 2023"),
    "csrd": ("ESRS-2024", "CSRD/ESRS"),
    "sec_climate": ("SEC-2024", "SEC Climate"),
    "gri_universal": ("GRI-2021", "GRI Universal"),
    "sasb_standards": ("SASB-2023", "SASB Standards"),
}

FRAMEWORK_VERSIONS: dict[str, str] = {
    framework_id: framework_version
    for framework_id, (framework_version, _) in _FRAMEWORK_VERSION_CATALOG.items()
}

FRAMEWORK_DISPLAY_NAMES: dict[str, str] = {
    framework_id: display_name
    for framework_id, (_, display_name) in _FRAMEWORK_VERSION_CATALOG.items()
}


def normalize_framework_version(framework_id: str, framework_version: str | None) -> str:
    if framework_version is None:
        return FRAMEWORK_VERSIONS.get(framework_id, LEGACY_FRAMEWORK_VERSION)

    normalized_version = framework_version.strip()
    if normalized_version.lower() == LEGACY_FRAMEWORK_VERSION:
        return FRAMEWORK_VERSIONS.get(framework_id, normalized_version)

    if not normalized_version:
        return FRAMEWORK_VERSIONS.get(framework_id, LEGACY_FRAMEWORK_VERSION)

    return normalized_version


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
    framework_region: str = "Global"  # "EU" | "CN" | "US" | "Global"
    company_name: str
    report_year: int
    framework_version: str = LEGACY_FRAMEWORK_VERSION
    analyzed_at: str | None = None
    total_score: float        # 0.0 – 1.0（加权综合）
    grade: str                # A/B/C/D/F
    dimensions: list[DimensionScore]
    gaps: list[str]
    recommendations: list[str]
    coverage_pct: float       # 已披露字段占所有必填字段的百分比

    @model_validator(mode="after")
    def apply_canonical_framework_version(self) -> FrameworkScoreResult:
        self.framework_version = normalize_framework_version(
            framework_id=self.framework_id,
            framework_version=self.framework_version,
        )
        return self


class FrameworkVersionInfo(BaseModel):
    framework_id: str
    framework_version: str
    display_name: str


class MultiFrameworkReport(BaseModel):
    company_name: str
    report_year: int
    frameworks: list[FrameworkScoreResult]
    summary: str              # 一段人读的综合判断

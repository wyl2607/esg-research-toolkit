from __future__ import annotations

from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, Field

from core.evidence import Evidence
from core.normalization.period import NormalizedPeriod


SourceDocumentType: TypeAlias = Literal[
    "annual_report",
    "sustainability_report",
    "annual_sustainability_report",
    "filing",
    "announcement",
    "manual_case",
    "event",
]


class CompanyESGData(BaseModel):
    company_name: str
    report_year: int
    reporting_period_label: str | None = None
    reporting_period_type: str | None = None
    source_document_type: SourceDocumentType | str | None = None
    industry_code: str | None = None
    industry_sector: str | None = None
    scope1_co2e_tonnes: float | None = None
    scope2_co2e_tonnes: float | None = None
    scope3_co2e_tonnes: float | None = None
    energy_consumption_mwh: float | None = None
    renewable_energy_pct: float | None = None
    water_usage_m3: float | None = None
    waste_recycled_pct: float | None = None
    total_revenue_eur: float | None = None
    taxonomy_aligned_revenue_pct: float | None = None
    total_capex_eur: float | None = None
    taxonomy_aligned_capex_pct: float | None = None
    total_employees: int | None = None
    female_pct: float | None = None
    primary_activities: list[str] = Field(default_factory=list)
    evidence_summary: list[dict[str, Any]] = Field(default_factory=list)


class ManualReportInput(CompanyESGData):
    source_url: str | None = None


class MergeSourceInput(ManualReportInput):
    source_id: str | None = None
    downloaded_at: str | None = None


class MergePreviewRequest(BaseModel):
    documents: list[MergeSourceInput]


class AuditTrailRow(BaseModel):
    id: int
    run_kind: str | None = None
    model: str | None = None
    verdict: str | None = None
    applied: bool | None = None
    notes: str | None = None
    created_at: str | None = None


class MergeMetricCandidate(BaseModel):
    source_id: str
    source_document_type: str | None = None
    source_url: str | None = None
    reporting_period_label: str | None = None
    priority_rank: int
    value: str | int | float | list[str] | None = None


class MergeMetricDecision(BaseModel):
    metric: str
    selected_value: str | int | float | list[str] | None = None
    selected_source_id: str | None = None
    selected_source_document_type: str | None = None
    merge_reason: str
    candidates: list[MergeMetricCandidate] = Field(default_factory=list)
    conflict_detected: bool = False


class MergedMetricResult(BaseModel):
    metric: str
    chosen_value: str | int | float | list[str] | None = None
    candidate_values: list[MergeMetricCandidate] = Field(default_factory=list)
    chosen_source: str | None = None
    chosen_source_document_type: str | None = None
    merge_reason: str
    conflict_detected: bool = False


class MergedResult(BaseModel):
    company_name: str
    report_year: int
    merged_metrics: CompanyESGData
    metrics: dict[str, MergedMetricResult]
    source_count: int


class MergePreviewResponse(BaseModel):
    company_name: str
    report_year: int
    merged_metrics: CompanyESGData
    decisions: list[MergeMetricDecision]
    document_priority: list[str]
    unresolved_metrics: list[str] = Field(default_factory=list)


class BatchJobItem(BaseModel):
    job_id: str
    filename: str
    status: Literal["queued", "processing", "completed", "failed"]
    error: str | None = None
    result: CompanyESGData | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    duration_seconds: float | None = None


class BatchStatusResponse(BaseModel):
    batch_id: str
    total_jobs: int
    queued_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    progress_pct: float
    jobs: list[BatchJobItem]


class TaxonomyScoreResult(BaseModel):
    company_name: str
    report_year: int
    revenue_aligned_pct: float
    capex_aligned_pct: float
    opex_aligned_pct: float
    objective_scores: dict[str, float]
    dnsh_pass: bool
    gaps: list[str]
    recommendations: list[str]


class FrameworkMetricMapping(BaseModel):
    framework_id: str
    framework_name: str
    dimension: str | None = None
    rationale: str | None = None


class CompanyProfileMetric(BaseModel):
    metric: str
    value: str | int | float | list[str] | None = None
    unit: str | None = None
    period: NormalizedPeriod
    source_document_type: str | None = None
    evidence: Evidence | None = None
    framework_mappings: list[FrameworkMetricMapping] = Field(default_factory=list)


class CompanyProfilePeriodMetadata(BaseModel):
    period_id: str
    label: str
    type: str
    source_document_type: str | None = None
    legacy_report_year: int
    fiscal_year: int
    reporting_standard: str
    period_start: str | None = None
    period_end: str | None = None


class CompanyProfileLatestPeriod(BaseModel):
    report_year: int
    reporting_period_label: str | None = None
    reporting_period_type: str | None = None
    source_document_type: str | None = None
    industry_code: str | None = None
    industry_sector: str | None = None
    period: CompanyProfilePeriodMetadata
    framework_metadata: list[dict[str, Any]] = Field(default_factory=list)


class CompanyProfilePeriodRecord(BaseModel):
    report_year: int
    reporting_period_label: str | None = None
    reporting_period_type: str | None = None
    source_document_type: str | None = None
    industry_code: str | None = None
    industry_sector: str | None = None
    period: CompanyProfilePeriodMetadata
    source_url: str | None = None
    downloaded_at: str | None = None
    evidence_anchors: list[dict[str, Any]] = Field(default_factory=list)
    framework_metadata: list[dict[str, Any]] = Field(default_factory=list)
    source_documents: list[dict[str, Any]] = Field(default_factory=list)
    merged_result: dict[str, Any]


class CompanyProfileV1Response(BaseModel):
    api_version: Literal["v1"] = "v1"
    company_name: str
    industry_code: str | None = None
    industry_sector: str | None = None
    years_available: list[int] = Field(default_factory=list)
    latest_year: int
    latest_period: CompanyProfileLatestPeriod
    latest_metrics: CompanyESGData
    scored_metrics: dict[str, CompanyProfileMetric]
    trend: list[dict[str, Any]] = Field(default_factory=list)
    periods: list[CompanyProfilePeriodRecord] = Field(default_factory=list)
    framework_metadata: list[dict[str, Any]] = Field(default_factory=list)
    framework_scores: list[dict[str, Any]] = Field(default_factory=list)
    framework_results: list[dict[str, Any]] = Field(default_factory=list)
    evidence_summary: list[dict[str, Any]] = Field(default_factory=list)
    evidence_anchors: list[dict[str, Any]] = Field(default_factory=list)
    data_quality_summary: dict[str, Any]
    narrative_summary: dict[str, Any]
    identity_provenance_summary: dict[str, Any]
    latest_sources: list[dict[str, Any]] = Field(default_factory=list)
    latest_merged_result: dict[str, Any]


class LCOEInput(BaseModel):
    technology: Literal["solar_pv", "wind_onshore", "wind_offshore", "battery_storage"]
    capacity_mw: float = Field(default=100.0, gt=0.0, le=1_000_000.0)
    capex_eur_per_kw: float = Field(gt=0.0, le=1_000_000.0)
    opex_eur_per_kw_year: float = Field(ge=0.0, le=1_000_000.0)
    capacity_factor: float = Field(gt=0.0, le=1.0)
    lifetime_years: int = Field(default=25, gt=0, le=100)
    discount_rate: float = Field(default=0.07, ge=0.0, lt=1.0)
    electricity_price_eur_per_mwh: float = Field(default=95.0, ge=0.0, le=1_000_000.0)
    currency: Literal["EUR", "USD", "CNY"] = "EUR"
    reference_fx_to_eur: float = Field(default=1.0, gt=0.0, le=1_000.0)


class LCOEResult(BaseModel):
    technology: str
    lcoe_eur_per_mwh: float
    lcoe_local_per_mwh: float
    npv_eur: float
    irr: float
    payback_years: float | None
    lifetime_years: int
    electricity_price_eur_per_mwh: float
    currency: str
    reference_fx_to_eur: float


class SensitivityResult(BaseModel):
    parameter: str
    base_value: float
    values: list[float]
    lcoe_results: list[float]
    lcoe_change_pct: list[float]

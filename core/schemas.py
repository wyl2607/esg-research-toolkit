from typing import Literal

from pydantic import BaseModel, Field


class CompanyESGData(BaseModel):
    company_name: str
    report_year: int
    reporting_period_label: str | None = None
    reporting_period_type: str | None = None
    source_document_type: str | None = None
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
    primary_activities: list[str] = []
    evidence_summary: list[dict[str, str | int | float | None]] = []


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


class LCOEInput(BaseModel):
    technology: Literal["solar_pv", "wind_onshore", "wind_offshore", "battery_storage"]
    capex_eur_per_kw: float
    opex_eur_per_kw_year: float
    capacity_factor: float = Field(ge=0.0, le=1.0)
    lifetime_years: int = 25
    discount_rate: float = 0.07


class LCOEResult(BaseModel):
    technology: str
    lcoe_eur_per_mwh: float
    npv_eur: float
    irr: float
    payback_years: float
    lifetime_years: int

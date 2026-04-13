// TypeScript mirrors of backend Pydantic schemas

export interface CompanyESGData {
  company_name: string
  report_year: number
  reporting_period_label?: string | null
  reporting_period_type?: string | null
  source_document_type?: string | null
  scope1_co2e_tonnes: number | null
  scope2_co2e_tonnes: number | null
  scope3_co2e_tonnes: number | null
  energy_consumption_mwh: number | null
  renewable_energy_pct: number | null
  water_usage_m3: number | null
  waste_recycled_pct: number | null
  total_revenue_eur: number | null
  taxonomy_aligned_revenue_pct: number | null
  total_capex_eur: number | null
  taxonomy_aligned_capex_pct: number | null
  total_employees: number | null
  female_pct: number | null
  primary_activities: string[]
  evidence_summary?: Array<Record<string, string | number | null>>
}

export interface BatchJobItem {
  job_id: string
  filename: string
  status: 'queued' | 'processing' | 'completed' | 'failed'
  error: string | null
  result: CompanyESGData | null
  created_at: string
  started_at: string | null
  finished_at: string | null
  duration_seconds: number | null
}

export interface BatchStatusResponse {
  batch_id: string
  total_jobs: number
  queued_jobs: number
  running_jobs: number
  completed_jobs: number
  failed_jobs: number
  progress_pct: number
  jobs: BatchJobItem[]
}

export interface TaxonomyScoreResult {
  company_name: string
  report_year: number
  revenue_aligned_pct: number
  capex_aligned_pct: number
  opex_aligned_pct: number
  objective_scores: Record<string, number>
  dnsh_pass: boolean
  gaps: string[]
  recommendations: string[]
}

export interface LCOEInput {
  technology: string
  capacity_mw: number
  capacity_factor: number
  capex_eur_per_kw: number
  opex_eur_per_kw_year: number
  lifetime_years: number
  discount_rate: number
}

export interface LCOEResult {
  technology: string
  lcoe_eur_per_mwh: number
  npv_eur: number
  irr: number
  payback_years: number
  lifetime_years: number
}

export interface SensitivityResult {
  parameter: string
  values: number[]
  lcoe_results: number[]
}

export interface DimensionScore {
  name: string
  score: number
  weight: number
  disclosed: number
  total: number
  gaps: string[]
}

export interface FrameworkScoreResult {
  framework: string
  framework_id: string
  company_name: string
  report_year: number
  framework_version?: string
  analyzed_at?: string | null
  total_score: number
  grade: string
  dimensions: DimensionScore[]
  gaps: string[]
  recommendations: string[]
  coverage_pct: number
}

export interface MultiFrameworkReport {
  company_name: string
  report_year: number
  frameworks: FrameworkScoreResult[]
  summary: string
}

export interface TaxonomyActivity {
  activity_id: string
  name: string
  sector: string
  ghg_threshold_gco2e_per_kwh: number | null
}

export interface CompanyHistoryPeriod {
  report_year: number
  reporting_period_label: string
  reporting_period_type: string
  source_document_type: string | null
  source_url: string | null
  downloaded_at: string | null
}

export interface CompanyTrendPoint {
  year: number
  scope1: number | null
  scope2: number | null
  scope3: number | null
  renewable_pct: number | null
  taxonomy_aligned_revenue_pct: number | null
  taxonomy_aligned_capex_pct: number | null
  female_pct: number | null
}

export interface CompanyProfile {
  company_name: string
  years_available: number[]
  latest_year: number
  latest_period: {
    report_year: number
    reporting_period_label: string
    reporting_period_type: string
    source_document_type: string | null
  }
  latest_metrics: CompanyESGData
  trend: CompanyTrendPoint[]
  periods: CompanyHistoryPeriod[]
  framework_results: Array<FrameworkScoreResult & { analysis_result_id?: number; stored_at?: string | null }>
  evidence_summary: Array<Record<string, string | number | null>>
}

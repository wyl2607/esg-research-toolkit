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
  evidence_summary?: EvidenceAnchor[]
}

export interface ManualReportInput extends CompanyESGData {
  source_url?: string | null
}

export interface EvidenceAnchor {
  metric: string | null
  source: string | null
  page: string | number | null
  snippet: string | null
  source_type?: string | null
  source_url?: string | null
  file_hash?: string | null
}

export interface FrameworkMetadata {
  analysis_result_id: number
  framework_id: string
  framework: string
  framework_version: string
  report_year: number
  stored_at: string | null
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
  electricity_price_eur_per_mwh: number
}

export interface LCOEResult {
  technology: string
  lcoe_eur_per_mwh: number
  npv_eur: number
  irr: number
  payback_years: number
  lifetime_years: number
  electricity_price_eur_per_mwh: number
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
  framework_region?: string
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
  period: CompanyNormalizedPeriod
  source_url: string | null
  downloaded_at: string | null
  evidence_anchors: EvidenceAnchor[]
  framework_metadata: FrameworkMetadata[]
  source_documents: CompanySourceDocument[]
  merged_result: CompanyMergedResult
}

export interface CompanyNormalizedPeriod {
  period_id: string
  label: string
  type: string
  source_document_type: string | null
  legacy_report_year: number
}

export interface CompanySourceDocument {
  source_id: string
  source_document_type: string | null
  reporting_period_label: string | null
  reporting_period_type: string | null
  source_url: string | null
  file_hash: string | null
  pdf_filename: string | null
  downloaded_at: string | null
  evidence_anchors: EvidenceAnchor[]
}

export interface MergeMetricCandidate {
  source_id: string
  source_document_type: string | null
  source_url: string | null
  reporting_period_label: string | null
  priority_rank: number
  value: string | number | string[] | null
}

export interface MergedMetricResult {
  metric: string
  chosen_value: string | number | string[] | null
  candidate_values: MergeMetricCandidate[]
  chosen_source: string | null
  chosen_source_document_type: string | null
  merge_reason: string
  conflict_detected: boolean
}

export interface CompanyMergedResult {
  company_name: string
  report_year: number
  merged_metrics: CompanyESGData
  metrics: Record<string, MergedMetricResult>
  source_count: number
}

export interface CompanyProfileLatestPeriod {
  report_year: number
  reporting_period_label: string
  reporting_period_type: string
  source_document_type: string | null
  period: CompanyNormalizedPeriod
  framework_metadata: FrameworkMetadata[]
}

export interface CompanyHistoryResponse {
  company_name: string
  periods: CompanyHistoryPeriod[]
  trend: CompanyTrendPoint[]
  framework_metadata: FrameworkMetadata[]
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
  latest_period: CompanyProfileLatestPeriod
  latest_metrics: CompanyESGData
  trend: CompanyTrendPoint[]
  periods: CompanyHistoryPeriod[]
  framework_metadata?: FrameworkMetadata[]
  framework_scores?: FrameworkScoreResult[]
  framework_results: Array<FrameworkScoreResult & { analysis_result_id?: number; stored_at?: string | null }>
  evidence_summary: EvidenceAnchor[]
  evidence_anchors?: EvidenceAnchor[]
  data_quality_summary: CompanyDataQualitySummary
  narrative_summary?: CompanyNarrativeSummary
  identity_provenance_summary?: CompanyIdentityProvenanceSummary
  latest_sources: CompanySourceDocument[]
  latest_merged_result: CompanyMergedResult
}

export interface CompanyDataQualitySummary {
  total_key_metrics_count: number
  present_metrics_count: number
  present_metrics: string[]
  missing_metrics: string[]
  completion_percentage: number
  readiness_label: 'draft' | 'usable' | 'showcase-ready'
}

export interface CompanyIdentityProvenanceSummary {
  canonical_company_name: string
  requested_company_name: string
  has_alias_consolidation: boolean
  consolidated_aliases: string[]
  latest_source_document_type: string | null
  source_priority_preview: string | null
  merge_priority_preview: string | null
}

export interface CompanyNarrativeSummary {
  snapshot: {
    periods_count: number
    years_count: number
    latest_year: number
    framework_count: number
    readiness_label: 'draft' | 'usable' | 'showcase-ready'
  }
  has_previous_period: boolean
  previous_year: number | null
  improved_metrics: string[]
  weakened_metrics: string[]
  stable_metrics: string[]
  disclosure_strength_metrics: string[]
  disclosure_gap_metrics: string[]
}

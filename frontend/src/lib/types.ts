// TypeScript mirrors of backend Pydantic schemas

export interface CompanyESGData {
  company_name: string
  report_year: number
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

export interface TaxonomyActivity {
  activity_id: string
  name: string
  sector: string
  ghg_threshold_gco2e_per_kwh: number | null
}

// Typed fetch wrappers for all 15 backend endpoints
import type {
  AuditTrailRow,
  BenchmarkRecomputeResponse,
  BatchStatusResponse,
  CompaniesByIndustryResponse,
  CompanyProfile,
  CompanyESGData,
  FrameworkScoreResult,
  IndustryBenchmarksResponse,
  LCOEInput,
  LCOEResult,
  MultiFrameworkReport,
  SensitivityResult,
  TaxonomyActivity,
  TaxonomyScoreResult,
  ManualReportInput,
} from './types'

const BASE = '/api'

export interface IndustryMetadataInput {
  industryCode?: string
  industrySector?: string
}

export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail || `HTTP ${status}`)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

async function toApiError(res: Response): Promise<ApiError> {
  const detail = (await res.text()).trim()
  return new ApiError(res.status, detail)
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) throw await toApiError(res)
  return res.json() as Promise<T>
}

// ── Report Parser ──────────────────────────────────────────────────────────

const appendIndustryFields = (
  form: FormData,
  industry?: IndustryMetadataInput
) => {
  if (industry?.industryCode) form.append('industry_code', industry.industryCode)
  if (industry?.industrySector) form.append('industry_sector', industry.industrySector)
}

export const uploadReport = (
  file: File,
  industry?: IndustryMetadataInput
): Promise<CompanyESGData> => {
  const form = new FormData()
  form.append('file', file)
  appendIndustryFields(form, industry)
  return fetch(BASE + '/report/upload', { method: 'POST', body: form }).then(
    async (r) => {
      if (!r.ok) throw await toApiError(r)
      return r.json() as Promise<CompanyESGData>
    }
  )
}

export const uploadReportsBatch = (
  files: File[],
  industry?: IndustryMetadataInput
): Promise<BatchStatusResponse> => {
  const form = new FormData()
  files.forEach((file) => form.append('files', file))
  appendIndustryFields(form, industry)
  return fetch(BASE + '/report/upload/batch', { method: 'POST', body: form }).then(
    async (r) => {
      if (!r.ok) throw await toApiError(r)
      return r.json() as Promise<BatchStatusResponse>
    }
  )
}

export const getBatchStatus = (batchId: string): Promise<BatchStatusResponse> =>
  req(`/report/jobs/${encodeURIComponent(batchId)}`)

export const listCompanies = (): Promise<CompanyESGData[]> =>
  req('/report/companies')

export interface CompanyYearCoverage {
  company_name: string
  industry_sector: string | null
  industry_code: string | null
  imported_years: number[]
  suggested_years: number[]
}

export const listCompaniesWithYearCoverage = (): Promise<CompanyYearCoverage[]> =>
  req('/report/companies/v2')

export interface DashboardStats {
  total_companies: number
  avg_taxonomy_aligned: number
  avg_renewable_pct: number
  yearly_trend: Array<{ year: number; count: number }>
  top_emitters: Array<{ company: string; year: number; scope1: number }>
  bottom_emitters: Array<{ company: string; year: number; scope1: number }>
  coverage_rates: Record<string, number>
}

export const getDashboardStats = (): Promise<DashboardStats> =>
  req('/report/dashboard/stats')

export const getCompany = (
  name: string,
  year: number
): Promise<CompanyESGData> =>
  req(`/report/companies/${encodeURIComponent(name)}/${year}`)

export const getCompanyProfile = (name: string): Promise<CompanyProfile> =>
  req(`/report/companies/${encodeURIComponent(name)}/profile`)

export const getAuditTrail = (
  companyReportId: number
): Promise<AuditTrailRow[]> =>
  req(`/report/${companyReportId}/audit-trail`)

export const getIndustryBenchmarks = (
  industryCode: string
): Promise<IndustryBenchmarksResponse> =>
  req(`/benchmarks/${encodeURIComponent(industryCode)}`)

export const getCompaniesByIndustry = (
  industryCode: string
): Promise<CompaniesByIndustryResponse> =>
  req(`/report/companies/by-industry/${encodeURIComponent(industryCode)}`)

export const recomputeIndustryBenchmarks =
  (): Promise<BenchmarkRecomputeResponse> =>
    req('/benchmarks/recompute', { method: 'POST' })

export const createManualReport = (
  data: ManualReportInput,
  industry?: IndustryMetadataInput
): Promise<CompanyESGData> =>
  req('/report/manual', {
    method: 'POST',
    body: JSON.stringify({
      ...data,
      ...(industry?.industryCode ? { industry_code: industry.industryCode } : {}),
      ...(industry?.industrySector ? { industry_sector: industry.industrySector } : {}),
    }),
  })

export const updateCompany = (
  name: string,
  year: number,
  data: Partial<CompanyESGData>
): Promise<CompanyESGData> =>
  req(`/report/companies/${encodeURIComponent(name)}/${year}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })

export const deleteCompany = (name: string, year: number): Promise<void> =>
  req(`/report/companies/${encodeURIComponent(name)}/${year}`, {
    method: 'DELETE',
  })

// ── Taxonomy ───────────────────────────────────────────────────────────────

export const scoreCompany = (
  data: CompanyESGData
): Promise<TaxonomyScoreResult> =>
  req('/taxonomy/score', { method: 'POST', body: JSON.stringify(data) })

export const getTaxonomyReport = (
  name: string,
  year: number
): Promise<TaxonomyScoreResult> =>
  req(
    `/taxonomy/report?company_name=${encodeURIComponent(name)}&report_year=${year}`
  )

export const listActivities = (): Promise<TaxonomyActivity[]> =>
  req('/taxonomy/activities')

export const downloadTaxonomyPdf = async (
  name: string,
  year: number
): Promise<void> => {
  const res = await fetch(
    `${BASE}/taxonomy/report/pdf?company_name=${encodeURIComponent(name)}&report_year=${year}`
  )
  if (!res.ok) throw await toApiError(res)
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${name.replace(/ /g, '_')}_${year}_taxonomy.pdf`
  a.click()
  URL.revokeObjectURL(url)
}

// ── Techno-Economics ───────────────────────────────────────────────────────

export const calcLcoe = (input: LCOEInput): Promise<LCOEResult> =>
  req('/techno/lcoe', { method: 'POST', body: JSON.stringify(input) })

export const calcSensitivity = (
  input: LCOEInput
): Promise<SensitivityResult[]> =>
  req('/techno/sensitivity', { method: 'POST', body: JSON.stringify(input) })

export const getBenchmarks = (): Promise<Record<string, LCOEInput>> =>
  req('/techno/benchmarks')

export const listLcoeResults = (): Promise<LCOEResult[]> =>
  req('/techno/results')

export const compareLcoe = (inputs: LCOEInput[]): Promise<LCOEResult[]> =>
  req('/techno/compare', { method: 'POST', body: JSON.stringify(inputs) })

// ── Multi-Framework ESG ────────────────────────────────────────────────────

export const getFrameworkComparison = (
  name: string,
  year: number
): Promise<MultiFrameworkReport> =>
  req(`/frameworks/compare?company_name=${encodeURIComponent(name)}&report_year=${year}`)


export interface RegionalGroup {
  region: string
  avg_score: number
  avg_grade: string
  strongest_area: string
  weakest_area: string
  frameworks: FrameworkScoreResult[]
}

export interface DimensionCrossMatrix {
  dimension_name: string
  eu_requirement: string
  cn_requirement: string
  us_requirement: string
  eu_score: number | null
  cn_score: number | null
  us_score: number | null
  gap_analysis: string
}

export interface RegionalComparisonReport {
  company_name: string
  report_year: number
  regional_groups: RegionalGroup[]
  cross_matrix: DimensionCrossMatrix[]
  compliance_priority: string[]
  overall_readiness: string
  key_insights: string[]
}

export const getRegionalComparison = (
  name: string,
  year: number
): Promise<RegionalComparisonReport> =>
  req(`/frameworks/compare/regional?company_name=${encodeURIComponent(name)}&report_year=${year}`)

export const getFrameworkScore = (
  name: string,
  year: number,
  framework: string
): Promise<FrameworkScoreResult> =>
  req(
    `/frameworks/score?company_name=${encodeURIComponent(name)}&report_year=${year}&framework=${framework}`
  )

export const listFrameworks = (): Promise<
  { id: string; name: string; region: string; mandatory_from: string; description: string }[]
> => req('/frameworks/list')

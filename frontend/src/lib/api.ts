// Typed fetch wrappers for all 15 backend endpoints
import type {
  BatchStatusResponse,
  CompanyProfile,
  CompanyESGData,
  FrameworkScoreResult,
  LCOEInput,
  LCOEResult,
  MultiFrameworkReport,
  SensitivityResult,
  TaxonomyActivity,
  TaxonomyScoreResult,
} from './types'

const BASE = '/api'

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

export const uploadReport = (file: File): Promise<CompanyESGData> => {
  const form = new FormData()
  form.append('file', file)
  return fetch(BASE + '/report/upload', { method: 'POST', body: form }).then(
    async (r) => {
      if (!r.ok) throw await toApiError(r)
      return r.json() as Promise<CompanyESGData>
    }
  )
}

export const uploadReportsBatch = (files: File[]): Promise<BatchStatusResponse> => {
  const form = new FormData()
  files.forEach((file) => form.append('files', file))
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

export const getCompany = (
  name: string,
  year: number
): Promise<CompanyESGData> =>
  req(`/report/companies/${encodeURIComponent(name)}/${year}`)

export const getCompanyProfile = (name: string): Promise<CompanyProfile> =>
  req(`/report/companies/${encodeURIComponent(name)}/profile`)

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

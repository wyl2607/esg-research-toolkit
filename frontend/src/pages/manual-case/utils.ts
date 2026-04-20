import type { ManualReportInput } from '@/lib/types'

export type ManualFormState = {
  company_name: string
  report_year: string
  reporting_period_label: string
  reporting_period_type: string
  source_document_type: string
  source_url: string
  scope1_co2e_tonnes: string
  scope2_co2e_tonnes: string
  scope3_co2e_tonnes: string
  renewable_energy_pct: string
  taxonomy_aligned_revenue_pct: string
  taxonomy_aligned_capex_pct: string
  total_employees: string
  female_pct: string
  energy_consumption_mwh: string
  water_usage_m3: string
  waste_recycled_pct: string
  primary_activities: string
}

export const EMPTY_FORM: ManualFormState = {
  company_name: '',
  report_year: '',
  reporting_period_label: '',
  reporting_period_type: 'annual',
  source_document_type: 'manual_case',
  source_url: '',
  scope1_co2e_tonnes: '',
  scope2_co2e_tonnes: '',
  scope3_co2e_tonnes: '',
  renewable_energy_pct: '',
  taxonomy_aligned_revenue_pct: '',
  taxonomy_aligned_capex_pct: '',
  total_employees: '',
  female_pct: '',
  energy_consumption_mwh: '',
  water_usage_m3: '',
  waste_recycled_pct: '',
  primary_activities: '',
}

function parseOptionalNumber(value: string) {
  const trimmed = value.trim()
  if (!trimmed) return null
  const normalized = trimmed.replace(/,/g, '')
  const parsed = Number(normalized)
  return Number.isFinite(parsed) ? parsed : null
}

export function buildPayload(form: ManualFormState): ManualReportInput {
  const reportYear = Number(form.report_year)

  return {
    company_name: form.company_name.trim(),
    report_year: Number.isFinite(reportYear) ? reportYear : new Date().getFullYear(),
    reporting_period_label: form.reporting_period_label.trim() || null,
    reporting_period_type: form.reporting_period_type || 'annual',
    source_document_type: form.source_document_type || 'manual_case',
    source_url: form.source_url.trim() || null,
    scope1_co2e_tonnes: parseOptionalNumber(form.scope1_co2e_tonnes),
    scope2_co2e_tonnes: parseOptionalNumber(form.scope2_co2e_tonnes),
    scope3_co2e_tonnes: parseOptionalNumber(form.scope3_co2e_tonnes),
    energy_consumption_mwh: parseOptionalNumber(form.energy_consumption_mwh),
    renewable_energy_pct: parseOptionalNumber(form.renewable_energy_pct),
    water_usage_m3: parseOptionalNumber(form.water_usage_m3),
    waste_recycled_pct: parseOptionalNumber(form.waste_recycled_pct),
    total_revenue_eur: null,
    taxonomy_aligned_revenue_pct: parseOptionalNumber(form.taxonomy_aligned_revenue_pct),
    total_capex_eur: null,
    taxonomy_aligned_capex_pct: parseOptionalNumber(form.taxonomy_aligned_capex_pct),
    total_employees: parseOptionalNumber(form.total_employees),
    female_pct: parseOptionalNumber(form.female_pct),
    primary_activities: form.primary_activities
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean),
    evidence_summary: [],
  }
}

export function payloadToForm(payload: Partial<ManualReportInput>): ManualFormState {
  return {
    company_name: payload.company_name ?? '',
    report_year: payload.report_year != null ? String(payload.report_year) : '',
    reporting_period_label: payload.reporting_period_label ?? '',
    reporting_period_type: payload.reporting_period_type ?? 'annual',
    source_document_type: payload.source_document_type ?? 'manual_case',
    source_url: payload.source_url ?? '',
    scope1_co2e_tonnes:
      payload.scope1_co2e_tonnes != null ? String(payload.scope1_co2e_tonnes) : '',
    scope2_co2e_tonnes:
      payload.scope2_co2e_tonnes != null ? String(payload.scope2_co2e_tonnes) : '',
    scope3_co2e_tonnes:
      payload.scope3_co2e_tonnes != null ? String(payload.scope3_co2e_tonnes) : '',
    renewable_energy_pct:
      payload.renewable_energy_pct != null ? String(payload.renewable_energy_pct) : '',
    taxonomy_aligned_revenue_pct:
      payload.taxonomy_aligned_revenue_pct != null
        ? String(payload.taxonomy_aligned_revenue_pct)
        : '',
    taxonomy_aligned_capex_pct:
      payload.taxonomy_aligned_capex_pct != null ? String(payload.taxonomy_aligned_capex_pct) : '',
    total_employees: payload.total_employees != null ? String(payload.total_employees) : '',
    female_pct: payload.female_pct != null ? String(payload.female_pct) : '',
    energy_consumption_mwh:
      payload.energy_consumption_mwh != null ? String(payload.energy_consumption_mwh) : '',
    water_usage_m3: payload.water_usage_m3 != null ? String(payload.water_usage_m3) : '',
    waste_recycled_pct:
      payload.waste_recycled_pct != null ? String(payload.waste_recycled_pct) : '',
    primary_activities: payload.primary_activities?.join(', ') ?? '',
  }
}

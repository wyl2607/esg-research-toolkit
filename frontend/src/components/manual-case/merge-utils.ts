import type { CompanyESGData, ManualReportInput, MergeSourceInput } from '@/lib/types'

export function buildMergeSourceId(
  companyName: string,
  reportYear: number,
  sourceDocumentType?: string | null
) {
  return `${companyName}:${reportYear}:${sourceDocumentType ?? 'unknown'}`
}

export function toMergeSourceInput(
  doc: ManualReportInput | CompanyESGData,
  sourceId?: string
): MergeSourceInput {
  const resolvedSourceId =
    sourceId ??
    buildMergeSourceId(doc.company_name, doc.report_year, doc.source_document_type)

  return {
    company_name: doc.company_name,
    report_year: doc.report_year,
    reporting_period_label: doc.reporting_period_label ?? null,
    reporting_period_type: doc.reporting_period_type ?? null,
    source_document_type: doc.source_document_type ?? null,
    industry_code: doc.industry_code ?? null,
    industry_sector: doc.industry_sector ?? null,
    scope1_co2e_tonnes: doc.scope1_co2e_tonnes ?? null,
    scope2_co2e_tonnes: doc.scope2_co2e_tonnes ?? null,
    scope2_basis: doc.scope2_basis ?? null,
    scope3_co2e_tonnes: doc.scope3_co2e_tonnes ?? null,
    energy_consumption_mwh: doc.energy_consumption_mwh ?? null,
    renewable_energy_pct: doc.renewable_energy_pct ?? null,
    water_usage_m3: doc.water_usage_m3 ?? null,
    waste_recycled_pct: doc.waste_recycled_pct ?? null,
    total_revenue_eur: doc.total_revenue_eur ?? null,
    taxonomy_aligned_revenue_pct: doc.taxonomy_aligned_revenue_pct ?? null,
    total_capex_eur: doc.total_capex_eur ?? null,
    taxonomy_aligned_capex_pct: doc.taxonomy_aligned_capex_pct ?? null,
    total_employees: doc.total_employees ?? null,
    female_pct: doc.female_pct ?? null,
    primary_activities: doc.primary_activities ?? [],
    source_url: 'source_url' in doc ? doc.source_url ?? null : null,
    source_id: resolvedSourceId,
  }
}

export function formatMergeValue(
  value: string | number | string[] | null | undefined,
  locale: string
) {
  if (value == null) return '—'
  if (Array.isArray(value)) {
    return value.length > 0 ? value.join(', ') : '—'
  }
  if (typeof value === 'number') {
    return value.toLocaleString(locale)
  }
  return value
}
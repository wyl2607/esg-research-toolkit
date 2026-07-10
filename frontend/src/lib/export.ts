/**
 * Client-side export utilities — no server resources required.
 * All serialization happens in the browser using data already in memory.
 */

import type {
  CompanyESGData,
  CompanyProfile,
  CompanyTrendPoint,
  FrameworkScoreResult,
} from '@/lib/types'
import { formatFrameworkMappingLabel } from '@/lib/profile-scored-metrics'

// ── Internal helpers ────────────────────────────────────────────────────────

function triggerDownload(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

// Exported for unit tests: pure serialization helpers.
export function escapeCSVCell(value: unknown): string {
  if (value === null || value === undefined) return ''
  const str = String(value)
  // Wrap in quotes if the value contains commas, quotes, or newlines
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return `"${str.replace(/"/g, '""')}"`
  }
  return str
}

function rowToCSV(row: Record<string, unknown>): string {
  return Object.values(row).map(escapeCSVCell).join(',')
}

export function buildCSV(headers: string[], rows: Record<string, unknown>[]): string {
  const headerLine = headers.map(escapeCSVCell).join(',')
  const dataLines = rows.map(rowToCSV)
  return [headerLine, ...dataLines].join('\n')
}

// ── Company ESG data → flat CSV row ────────────────────────────────────────

const COMPANY_CSV_HEADERS = [
  'Company',
  'Year',
  'Reporting Period',
  'Document Type',
  'Scope 1 (tCO₂e)',
  'Scope 2 (tCO₂e)',
  'Scope 3 (tCO₂e)',
  'Energy Consumption (MWh)',
  'Renewable Energy (%)',
  'Water Usage (m³)',
  'Waste Recycled (%)',
  'Total Revenue (EUR)',
  'Taxonomy Aligned Revenue (%)',
  'Total CapEx (EUR)',
  'Taxonomy Aligned CapEx (%)',
  'Total Employees',
  'Female Employees (%)',
  'Primary Activities',
]

function companyToCSVRow(c: CompanyESGData): Record<string, unknown> {
  return {
    Company: c.company_name,
    Year: c.report_year,
    'Reporting Period': c.reporting_period_label ?? '',
    'Document Type': c.source_document_type ?? '',
    'Scope 1 (tCO₂e)': c.scope1_co2e_tonnes ?? '',
    'Scope 2 (tCO₂e)': c.scope2_co2e_tonnes ?? '',
    'Scope 3 (tCO₂e)': c.scope3_co2e_tonnes ?? '',
    'Energy Consumption (MWh)': c.energy_consumption_mwh ?? '',
    'Renewable Energy (%)': c.renewable_energy_pct ?? '',
    'Water Usage (m³)': c.water_usage_m3 ?? '',
    'Waste Recycled (%)': c.waste_recycled_pct ?? '',
    'Total Revenue (EUR)': c.total_revenue_eur ?? '',
    'Taxonomy Aligned Revenue (%)': c.taxonomy_aligned_revenue_pct ?? '',
    'Total CapEx (EUR)': c.total_capex_eur ?? '',
    'Taxonomy Aligned CapEx (%)': c.taxonomy_aligned_capex_pct ?? '',
    'Total Employees': c.total_employees ?? '',
    'Female Employees (%)': c.female_pct ?? '',
    'Primary Activities': c.primary_activities.join('; '),
  }
}

// ── Public API ───────────────────────────────────────────────────────────────

/**
 * Export an array of CompanyESGData as a CSV file.
 * Uses the currently filtered/visible data — zero server calls.
 */
export function exportCompaniesCSV(companies: CompanyESGData[], filename?: string): void {
  const rows = companies.map(companyToCSVRow)
  const csv = buildCSV(COMPANY_CSV_HEADERS, rows)
  const defaultName = `esg-companies-${new Date().toISOString().slice(0, 10)}.csv`
  const name = filename ?? defaultName
  triggerDownload(csv, name, 'text/csv;charset=utf-8;')
}

export function collectFrameworkScoreRows(
  profile: CompanyProfile
): Record<string, unknown>[] {
  const scores: FrameworkScoreResult[] = [
    ...(profile.framework_scores ?? []),
    ...(profile.framework_results ?? []),
  ]
  const seen = new Set<string>()
  const rows: Record<string, unknown>[] = []
  for (const fw of scores) {
    const key = `${fw.framework_id}|${fw.framework_version ?? ''}|${(fw as FrameworkScoreResult & { stored_at?: string | null }).stored_at ?? fw.analyzed_at ?? ''}`
    if (seen.has(key)) continue
    seen.add(key)
    rows.push({
      Framework: fw.framework,
      'Framework ID': fw.framework_id,
      Version: fw.framework_version ?? '',
      Score: fw.total_score,
      Grade: fw.grade,
      'Coverage %': fw.coverage_pct,
      Gaps: (fw.gaps ?? []).join('; '),
      Analyzed:
        fw.analyzed_at ??
        (fw as FrameworkScoreResult & { stored_at?: string | null }).stored_at ??
        '',
    })
  }
  return rows
}

export function collectScoredMetricEvidenceRows(
  profile: CompanyProfile
): Record<string, unknown>[] {
  const scored = profile.scored_metrics ?? {}
  return Object.entries(scored).map(([metricKey, metric]) => {
    const evidence = metric.evidence
    const mappings = (metric.framework_mappings ?? [])
      .map(formatFrameworkMappingLabel)
      .join('; ')
    return {
      Metric: metricKey,
      Value: metric.value ?? '',
      Unit: metric.unit ?? '',
      Period: metric.period?.label ?? '',
      'Source Document Type': metric.source_document_type ?? '',
      Page: evidence?.page ?? '',
      Snippet: evidence?.snippet ?? '',
      'Extraction Method': evidence?.extraction_method ?? '',
      Confidence: evidence?.confidence ?? '',
      'Source Doc ID': evidence?.source_doc_id ?? '',
      'Framework Mappings': mappings,
    }
  })
}

/**
 * Export a single company profile (latest metrics + historical trend) as CSV.
 * Generates sections: metadata, latest metrics, historical trend, framework scores,
 * and scored_metrics evidence (v1) when present.
 */
export function exportCompanyProfileCSV(profile: CompanyProfile, filename?: string): void {
  // Section 0: Metadata
  const exportDate = new Date().toISOString().slice(0, 19)
  const metadataCSV = buildCSV(
    ['Metadata', 'Value'],
    [
      { Metadata: 'Company', Value: profile.company_name },
      { Metadata: 'Latest Year', Value: profile.latest_year },
      { Metadata: 'Export Date', Value: exportDate },
      { Metadata: 'Data Years', Value: profile.years_available.join(', ') },
      {
        Metadata: 'API Version',
        Value: profile.scored_metrics ? 'v1 (scored_metrics)' : 'legacy',
      },
    ]
  )

  // Section 1: latest metrics as a single flat row
  const latestRows = [companyToCSVRow(profile.latest_metrics)]
  const metricsCSV = buildCSV(COMPANY_CSV_HEADERS, latestRows)

  // Section 2: historical trend
  const TREND_HEADERS = [
    'Year',
    'Scope 1 (tCO₂e)',
    'Scope 2 (tCO₂e)',
    'Scope 3 (tCO₂e)',
    'Renewable Energy (%)',
    'Taxonomy Aligned Revenue (%)',
    'Taxonomy Aligned CapEx (%)',
    'Female Employees (%)',
  ]
  const trendRows = (profile.trend ?? []).map((d: CompanyTrendPoint) => ({
    Year: d.year,
    'Scope 1 (tCO₂e)': d.scope1 ?? '',
    'Scope 2 (tCO₂e)': d.scope2 ?? '',
    'Scope 3 (tCO₂e)': d.scope3 ?? '',
    'Renewable Energy (%)': d.renewable_pct ?? '',
    'Taxonomy Aligned Revenue (%)': d.taxonomy_aligned_revenue_pct ?? '',
    'Taxonomy Aligned CapEx (%)': d.taxonomy_aligned_capex_pct ?? '',
    'Female Employees (%)': d.female_pct ?? '',
  }))
  const trendCSV = trendRows.length > 0 ? `\n\nHistorical Trend\n${buildCSV(TREND_HEADERS, trendRows)}` : ''

  // Section 3: framework scores (deduped)
  const frameworkRows = collectFrameworkScoreRows(profile)
  const FRAMEWORK_HEADERS = [
    'Framework',
    'Framework ID',
    'Version',
    'Score',
    'Grade',
    'Coverage %',
    'Gaps',
    'Analyzed',
  ]
  const frameworkCSV =
    frameworkRows.length > 0
      ? `\n\nFramework Scores\n${buildCSV(FRAMEWORK_HEADERS, frameworkRows)}`
      : ''

  // Section 4: scored_metrics evidence + framework mappings
  const evidenceRows = collectScoredMetricEvidenceRows(profile)
  const EVIDENCE_HEADERS = [
    'Metric',
    'Value',
    'Unit',
    'Period',
    'Source Document Type',
    'Page',
    'Snippet',
    'Extraction Method',
    'Confidence',
    'Source Doc ID',
    'Framework Mappings',
  ]
  const evidenceCSV =
    evidenceRows.length > 0
      ? `\n\nScored Metrics Evidence\n${buildCSV(EVIDENCE_HEADERS, evidenceRows)}`
      : ''

  const defaultName = `${profile.company_name.replace(/[^a-z0-9]/gi, '_')}_esg_${profile.latest_year}_${new Date().toISOString().slice(0, 10)}.csv`
  const name = filename ?? defaultName
  triggerDownload(
    `${metadataCSV}\n\nLatest Metrics (${profile.latest_year})\n${metricsCSV}${trendCSV}${frameworkCSV}${evidenceCSV}`,
    name,
    'text/csv;charset=utf-8;'
  )
}

/**
 * Export any data object as a pretty-printed JSON file.
 */
export function exportToJSON(data: unknown, filename: string): void {
  const json = JSON.stringify(data, null, 2)
  triggerDownload(json, filename, 'application/json;charset=utf-8;')
}

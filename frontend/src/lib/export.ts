/**
 * Client-side export utilities — no server resources required.
 * All serialization happens in the browser using data already in memory.
 */

import type { CompanyESGData, CompanyProfile, CompanyTrendPoint } from '@/lib/types'

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

function escapeCSVCell(value: unknown): string {
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

function buildCSV(headers: string[], rows: Record<string, unknown>[]): string {
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

/**
 * Export a single company profile (latest metrics + historical trend) as CSV.
 * Generates two sections: a header section with latest metrics, then the trend table.
 * Now includes metadata section with export date and data version.
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

  const defaultName = `${profile.company_name.replace(/[^a-z0-9]/gi, '_')}_esg_${profile.latest_year}_${new Date().toISOString().slice(0, 10)}.csv`
  const name = filename ?? defaultName
  triggerDownload(`${metadataCSV}\n\nLatest Metrics (${profile.latest_year})\n${metricsCSV}${trendCSV}`, name, 'text/csv;charset=utf-8;')
}

/**
 * Export any data object as a pretty-printed JSON file.
 */
export function exportToJSON(data: unknown, filename: string): void {
  const json = JSON.stringify(data, null, 2)
  triggerDownload(json, filename, 'application/json;charset=utf-8;')
}

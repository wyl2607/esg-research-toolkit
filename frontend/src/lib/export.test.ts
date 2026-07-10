import { describe, expect, it } from 'vitest'
import {
  buildCSV,
  collectFrameworkScoreRows,
  collectScoredMetricEvidenceRows,
  escapeCSVCell,
} from './export'
import type { CompanyProfile } from './types'

describe('escapeCSVCell', () => {
  it('returns empty string for null and undefined', () => {
    expect(escapeCSVCell(null)).toBe('')
    expect(escapeCSVCell(undefined)).toBe('')
  })

  it('passes plain values through unquoted', () => {
    expect(escapeCSVCell('Siemens AG')).toBe('Siemens AG')
    expect(escapeCSVCell(2024)).toBe('2024')
    expect(escapeCSVCell(12.5)).toBe('12.5')
  })

  it('quotes values containing commas', () => {
    expect(escapeCSVCell('Müller, Thomas')).toBe('"Müller, Thomas"')
  })

  it('quotes and doubles embedded quotes', () => {
    expect(escapeCSVCell('the "green" fund')).toBe('"the ""green"" fund"')
  })

  it('quotes values containing newlines', () => {
    expect(escapeCSVCell('line1\nline2')).toBe('"line1\nline2"')
  })

  it('preserves zero and negative numbers', () => {
    expect(escapeCSVCell(0)).toBe('0')
    expect(escapeCSVCell(-42.5)).toBe('-42.5')
  })
})

describe('buildCSV', () => {
  it('joins headers and rows with newlines', () => {
    const csv = buildCSV(
      ['Company', 'Year'],
      [
        { Company: 'Contract Demo AG', Year: 2024 },
        { Company: 'RWE, AG', Year: 2023 },
      ]
    )
    expect(csv).toBe('Company,Year\nContract Demo AG,2024\n"RWE, AG",2023')
  })

  it('escapes header cells too', () => {
    expect(buildCSV(['Scope 1 (tCO₂e)', 'a,b'], [])).toBe('Scope 1 (tCO₂e),"a,b"')
  })

  it('produces only the header line for zero rows', () => {
    expect(buildCSV(['A', 'B'], [])).toBe('A,B')
  })
})

function miniProfile(overrides: Partial<CompanyProfile> = {}): CompanyProfile {
  const latest_metrics = {
    company_name: 'Export Co',
    report_year: 2024,
    scope1_co2e_tonnes: 1,
    scope2_co2e_tonnes: null,
    scope3_co2e_tonnes: null,
    energy_consumption_mwh: null,
    renewable_energy_pct: 10,
    water_usage_m3: null,
    waste_recycled_pct: null,
    total_revenue_eur: null,
    taxonomy_aligned_revenue_pct: null,
    total_capex_eur: null,
    taxonomy_aligned_capex_pct: null,
    total_employees: null,
    female_pct: null,
    primary_activities: [],
  }
  return {
    company_name: 'Export Co',
    years_available: [2024],
    latest_year: 2024,
    latest_period: {
      report_year: 2024,
      reporting_period_label: 'FY 2024',
      reporting_period_type: 'annual',
      source_document_type: 'annual_report',
      industry_code: null,
      industry_sector: null,
      period: {
        period_id: 'p',
        label: 'FY 2024',
        type: 'annual',
        source_document_type: 'annual_report',
        legacy_report_year: 2024,
      },
      framework_metadata: [],
    },
    latest_metrics,
    trend: [],
    periods: [],
    framework_results: [],
    evidence_summary: [],
    data_quality_summary: {
      total_key_metrics_count: 0,
      present_metrics_count: 0,
      present_metrics: [],
      missing_metrics: [],
      completion_percentage: 0,
      readiness_label: 'draft',
    },
    latest_sources: [],
    latest_merged_result: {
      company_name: 'Export Co',
      report_year: 2024,
      merged_metrics: latest_metrics,
      metrics: {},
      source_count: 0,
    },
    ...overrides,
  }
}

describe('collectFrameworkScoreRows', () => {
  it('dedupes framework_scores and framework_results', () => {
    const profile = miniProfile({
      framework_scores: [
        {
          framework: 'EU Taxonomy',
          framework_id: 'eu_taxonomy',
          framework_region: 'EU',
          company_name: 'Export Co',
          report_year: 2024,
          framework_version: 'v1',
          analyzed_at: '2026-01-01T00:00:00Z',
          total_score: 0.5,
          grade: 'C',
          dimensions: [],
          gaps: ['missing water'],
          recommendations: [],
          coverage_pct: 60,
        },
      ],
      framework_results: [
        {
          framework: 'EU Taxonomy',
          framework_id: 'eu_taxonomy',
          framework_region: 'EU',
          company_name: 'Export Co',
          report_year: 2024,
          framework_version: 'v1',
          analyzed_at: '2026-01-01T00:00:00Z',
          total_score: 0.5,
          grade: 'C',
          dimensions: [],
          gaps: ['missing water'],
          recommendations: [],
          coverage_pct: 60,
        },
      ],
    })
    const rows = collectFrameworkScoreRows(profile)
    expect(rows).toHaveLength(1)
    expect(rows[0].Framework).toBe('EU Taxonomy')
    expect(rows[0].Gaps).toBe('missing water')
  })
})

describe('collectScoredMetricEvidenceRows', () => {
  it('flattens scored_metrics evidence and mappings for CSV', () => {
    const profile = miniProfile({
      scored_metrics: {
        renewable_energy_pct: {
          metric: 'renewable_energy_pct',
          value: 10,
          unit: '%',
          period: {
            period_id: 'p',
            label: 'FY 2024',
            type: 'annual',
            source_document_type: 'annual_report',
            legacy_report_year: 2024,
          },
          source_document_type: 'annual_report',
          evidence: {
            source_doc_id: 'doc-x',
            page: 2,
            snippet: 'Renewables at 10%.',
            extraction_method: 'regex',
            confidence: 0.91,
          },
          framework_mappings: [
            {
              framework_id: 'eu_taxonomy',
              framework_name: 'EU Taxonomy 2020',
              dimension: 'Climate',
            },
          ],
        },
      },
    })
    const rows = collectScoredMetricEvidenceRows(profile)
    expect(rows).toHaveLength(1)
    expect(rows[0].Metric).toBe('renewable_energy_pct')
    expect(rows[0].Page).toBe(2)
    expect(rows[0]['Framework Mappings']).toBe('EU Taxonomy 2020 · Climate')
  })
})

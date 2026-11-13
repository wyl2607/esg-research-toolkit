import { describe, expect, it } from 'vitest'
import type { CompanyESGData } from '@/lib/types'
import {
  compareEvidenceCount,
  comparePeriodLabel,
  compareSourceContext,
  compareSourceDocumentType,
  prettifyCompareToken,
} from './utils'

type CompareCompany = CompanyESGData & {
  period?: {
    period_id: string
    label: string
    type: string
    source_document_type: string | null
    legacy_report_year: number
  } | null
}

function company(overrides: Partial<CompareCompany> = {}): CompareCompany {
  return {
    company_name: 'Acme',
    report_year: 2024,
    scope1_co2e_tonnes: null,
    scope2_co2e_tonnes: null,
    scope3_co2e_tonnes: null,
    energy_consumption_mwh: null,
    renewable_energy_pct: null,
    water_usage_m3: null,
    waste_recycled_pct: null,
    total_revenue_eur: null,
    taxonomy_aligned_revenue_pct: null,
    total_capex_eur: null,
    taxonomy_aligned_capex_pct: null,
    total_employees: null,
    female_pct: null,
    primary_activities: [],
    ...overrides,
  }
}

function period(
  label: string,
  sourceDocumentType: string | null
): NonNullable<CompareCompany['period']> {
  return {
    period_id: `period-${label}`,
    label,
    type: 'annual',
    source_document_type: sourceDocumentType,
    legacy_report_year: 2024,
  }
}

describe('prettifyCompareToken', () => {
  it('replaces runs of underscores and hyphens with one space', () => {
    expect(prettifyCompareToken('annual--sustainability__report')).toBe(
      'annual sustainability report'
    )
  })

  it('returns null for nullish and empty tokens', () => {
    expect(prettifyCompareToken(null)).toBeNull()
    expect(prettifyCompareToken(undefined)).toBeNull()
    expect(prettifyCompareToken('')).toBeNull()
  })
})

describe('comparePeriodLabel', () => {
  it('prefers the normalized period label', () => {
    expect(
      comparePeriodLabel(company({ period: period('FY2023', 'annual_report') }))
    ).toBe('FY2023')
  })

  it('falls back to the reporting period label', () => {
    expect(comparePeriodLabel(company({ reporting_period_label: '2023 annual' }))).toBe(
      '2023 annual'
    )
  })

  it('falls back to the report year as a string', () => {
    expect(comparePeriodLabel(company({ report_year: 2021 }))).toBe('2021')
  })
})

describe('compareSourceDocumentType', () => {
  it('prettifies the normalized period document type first', () => {
    expect(
      compareSourceDocumentType(
        company({
          period: period('FY2023', 'annual_report'),
          source_document_type: 'sustainability_report',
        })
      )
    ).toBe('annual report')
  })

  it('falls back to the company document type and then to null', () => {
    expect(
      compareSourceDocumentType(company({ source_document_type: 'sustainability_report' }))
    ).toBe('sustainability report')
    expect(compareSourceDocumentType(company())).toBeNull()
  })
})

describe('compareEvidenceCount', () => {
  it('returns zero when the evidence summary is missing or empty', () => {
    expect(compareEvidenceCount(company())).toBe(0)
    expect(compareEvidenceCount(company({ evidence_summary: [] }))).toBe(0)
  })

  it('counts the evidence anchors', () => {
    const anchor = { metric: null, source: null, page: null, snippet: null }
    expect(compareEvidenceCount(company({ evidence_summary: [anchor, anchor] }))).toBe(2)
  })
})

describe('compareSourceContext', () => {
  it('joins the period label and document type', () => {
    expect(
      compareSourceContext(company({ period: period('FY2023', 'annual_report') }))
    ).toBe('FY2023 · annual report')
  })

  it('omits the separator when there is no document type', () => {
    expect(compareSourceContext(company({ report_year: 2020 }))).toBe('2020')
  })
})

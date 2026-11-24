import { describe, expect, it } from 'vitest'
import type {
  CompanySourceDocument,
  CompanyTrendPoint,
  EvidenceAnchor,
  FrameworkMetadata,
} from '@/lib/types'
import {
  asDate,
  asNum,
  asPct,
  buildCompanyTrendData,
  compactList,
  deltaNumber,
  deltaPercent,
  deltaPercentLabel,
  deltaPctLabel,
  deltaToneClass,
  evidenceRichness,
  frameworkRunKey,
  mergeEvidenceAnchor,
  metricDisclosureLabel,
  metricLabelsFromKeys,
  normalizeProfileEvidenceAnchor,
  parseCompanyReportId,
  prettifyToken,
  sourceOriginLabel,
} from './utils'
import type { FrameworkDisplayResult } from './utils'

type ProfileEvidence = EvidenceAnchor & { source_doc_id?: string | null }

type ProfileSource = CompanySourceDocument & {
  period?: {
    period_id: string
    label: string
    type: string
    source_document_type: string | null
    legacy_report_year: number
  } | null
  framework_metadata?: FrameworkMetadata[]
}

function evidence(overrides: Partial<ProfileEvidence> = {}): ProfileEvidence {
  return {
    metric: null,
    source: null,
    page: null,
    snippet: null,
    ...overrides,
  }
}

function sourceDocument(overrides: Partial<ProfileSource> = {}): ProfileSource {
  return {
    source_id: 'src-1',
    source_document_type: null,
    reporting_period_label: null,
    reporting_period_type: null,
    source_url: null,
    file_hash: null,
    pdf_filename: null,
    downloaded_at: null,
    evidence_anchors: [],
    ...overrides,
  }
}

function trendPoint(overrides: Partial<CompanyTrendPoint> = {}): CompanyTrendPoint {
  return {
    year: 2024,
    scope1: null,
    scope2: null,
    scope3: null,
    renewable_pct: null,
    taxonomy_aligned_revenue_pct: null,
    taxonomy_aligned_capex_pct: null,
    female_pct: null,
    ...overrides,
  }
}

function frameworkResult(overrides: Partial<FrameworkDisplayResult> = {}): FrameworkDisplayResult {
  return {
    framework: 'GRI',
    framework_id: 'gri',
    framework_region: 'Global',
    company_name: 'Acme',
    report_year: 2024,
    framework_version: 'v1',
    total_score: 50,
    grade: 'C',
    dimensions: [],
    gaps: [],
    recommendations: [],
    coverage_pct: 50,
    ...overrides,
  }
}

describe('asPct', () => {
  it('formats with one decimal and keeps a real zero', () => {
    expect(asPct(42.5)).toBe('42.5%')
    expect(asPct(0)).toBe('0.0%')
  })

  it('returns an em dash for null and undefined', () => {
    expect(asPct(null)).toBe('—')
    expect(asPct(undefined)).toBe('—')
  })
})

describe('asNum', () => {
  it('groups digits with the requested locale', () => {
    expect(asNum(1234567, 'en-US')).toBe('1,234,567')
    expect(asNum(1234567, 'de-DE')).toBe('1.234.567')
    expect(asNum(0, 'en-US')).toBe('0')
  })

  it('returns an em dash for nullish values', () => {
    expect(asNum(null, 'en-US')).toBe('—')
    expect(asNum(undefined, 'de-DE')).toBe('—')
  })
})

describe('deltaNumber', () => {
  it('subtracts the previous value from the current value', () => {
    expect(deltaNumber(120, 100)).toBe(20)
    expect(deltaNumber(80, 100)).toBe(-20)
  })

  it('returns null when either side is missing', () => {
    expect(deltaNumber(null, 100)).toBeNull()
    expect(deltaNumber(100, undefined)).toBeNull()
    expect(deltaNumber(null, null)).toBeNull()
  })
})

describe('deltaPercent', () => {
  it('computes the change relative to the previous value', () => {
    expect(deltaPercent(120, 100)).toBe(20)
    expect(deltaPercent(80, 100)).toBe(-20)
  })

  it('returns null for missing values or a zero baseline', () => {
    expect(deltaPercent(10, null)).toBeNull()
    expect(deltaPercent(null, 10)).toBeNull()
    expect(deltaPercent(10, 0)).toBeNull()
  })

  it('divides by the absolute previous value for negative baselines', () => {
    expect(deltaPercent(50, -100)).toBe(150)
    expect(deltaPercent(-50, -100)).toBe(50)
  })
})

describe('deltaPctLabel', () => {
  it('adds a plus sign only to positive values', () => {
    expect(deltaPctLabel(3.4)).toBe('+3.4')
    expect(deltaPctLabel(-2.3)).toBe('-2.3')
    expect(deltaPctLabel(0)).toBe('0.0')
  })

  it('returns an em dash for nullish values', () => {
    expect(deltaPctLabel(null)).toBe('—')
    expect(deltaPctLabel(undefined)).toBe('—')
  })
})

describe('deltaPercentLabel', () => {
  it('adds the sign and the percent unit', () => {
    expect(deltaPercentLabel(12.34)).toBe('+12.3%')
    expect(deltaPercentLabel(-5.6)).toBe('-5.6%')
  })

  it('keeps zero unsigned and maps missing values to an em dash', () => {
    expect(deltaPercentLabel(0)).toBe('0.0%')
    expect(deltaPercentLabel(null)).toBe('—')
  })
})

describe('deltaToneClass', () => {
  it('uses a neutral tone for missing values', () => {
    expect(deltaToneClass(null)).toBe('text-slate-500')
    expect(deltaToneClass(undefined)).toBe('text-slate-500')
  })

  it('treats zero and positive values as favourable', () => {
    expect(deltaToneClass(0)).toBe('text-emerald-600')
    expect(deltaToneClass(0.1)).toBe('text-emerald-600')
    expect(deltaToneClass(-0.1)).toBe('text-rose-600')
  })
})

describe('metricDisclosureLabel', () => {
  it('returns the translation when the key resolves', () => {
    const t = (key: string) =>
      key === 'profile.metricLabels.scope1_co2e_tonnes' ? 'Scope 1 emissions' : key
    expect(metricDisclosureLabel(t, 'scope1_co2e_tonnes')).toBe('Scope 1 emissions')
  })

  it('prettifies the raw key when the translation is missing', () => {
    const t = (key: string) => key
    expect(metricDisclosureLabel(t, 'scope1_co2e_tonnes')).toBe('scope1 co2e tonnes')
  })
})

describe('metricLabelsFromKeys', () => {
  it('maps each key through the disclosure label helper', () => {
    const t = (key: string) =>
      key === 'profile.metricLabels.scope1_co2e_tonnes' ? 'Scope 1 emissions' : key
    expect(metricLabelsFromKeys(t, ['scope1_co2e_tonnes', 'energy_consumption_mwh'])).toEqual([
      'Scope 1 emissions',
      'energy consumption mwh',
    ])
  })

  it('returns an empty array for no keys', () => {
    expect(metricLabelsFromKeys((key) => key, [])).toEqual([])
  })
})

describe('asDate', () => {
  it('formats a valid timestamp with a short month', () => {
    expect(asDate('2024-03-15T12:00:00', 'en-US')).toBe('Mar 15, 2024')
  })

  it('returns the raw string when the value cannot be parsed', () => {
    expect(asDate('not-a-date', 'en-US')).toBe('not-a-date')
  })

  it('returns an em dash for empty values', () => {
    expect(asDate(null, 'en-US')).toBe('—')
    expect(asDate(undefined, 'en-US')).toBe('—')
    expect(asDate('', 'en-US')).toBe('—')
  })
})

describe('compactList', () => {
  it('joins unique non-empty values in first-seen order', () => {
    expect(compactList(['a', null, 'b', undefined, 'a'])).toBe('a, b')
  })

  it('returns an empty string for an empty list', () => {
    expect(compactList([])).toBe('')
    expect(compactList([null, undefined, ''])).toBe('')
  })

  it('summarizes values beyond the default maximum', () => {
    expect(compactList(['a', 'b', 'c', 'd'])).toBe('a, b, c +1')
    expect(compactList(['a', 'b', 'c'])).toBe('a, b, c')
  })

  it('honours a custom maximum', () => {
    expect(compactList(['a', 'b', 'c'], 1)).toBe('a +2')
  })
})

describe('sourceOriginLabel', () => {
  it('returns an em dash when no source exists', () => {
    expect(sourceOriginLabel(null)).toBe('—')
    expect(sourceOriginLabel(undefined)).toBe('—')
  })

  it('extracts the hostname from a valid document URL', () => {
    expect(
      sourceOriginLabel(sourceDocument({ source_url: 'https://www.example.com/report.pdf' }))
    ).toBe('www.example.com')
  })

  it('falls back to the raw string when the URL is unparseable', () => {
    expect(sourceOriginLabel(sourceDocument({ source_url: 'not a url' }))).toBe('not a url')
  })

  it('falls back from filename to hash to source id', () => {
    expect(sourceOriginLabel(sourceDocument({ pdf_filename: 'report.pdf', file_hash: 'hash' }))).toBe(
      'report.pdf'
    )
    expect(sourceOriginLabel(sourceDocument({ file_hash: 'hash' }))).toBe('hash')
    expect(sourceOriginLabel(sourceDocument())).toBe('src-1')
  })
})

describe('mergeEvidenceAnchor', () => {
  it('returns the incoming anchor when nothing exists yet', () => {
    const incoming = evidence({ metric: 'scope1' })
    expect(mergeEvidenceAnchor(undefined, incoming)).toBe(incoming)
  })

  it('keeps existing values and fills only missing fields', () => {
    const merged = mergeEvidenceAnchor(
      evidence({ metric: 'scope1', snippet: '' }),
      evidence({ metric: 'scope3', page: 7, snippet: 'quoted text', source: 'pdf' })
    )
    expect(merged).toMatchObject({
      metric: 'scope1',
      page: 7,
      snippet: 'quoted text',
      source: 'pdf',
    })
  })

  it('treats zero as an existing value', () => {
    const merged = mergeEvidenceAnchor(evidence({ page: 0 }), evidence({ page: 9 }))
    expect(merged.page).toBe(0)
  })
})

describe('evidenceRichness', () => {
  it('scores an empty anchor as zero', () => {
    expect(evidenceRichness(evidence())).toBe(0)
    expect(evidenceRichness(evidence({ metric: '   ' }))).toBe(0)
  })

  it('counts numbers and non-empty strings', () => {
    expect(evidenceRichness(evidence({ page: 3 }))).toBe(1)
    expect(evidenceRichness(evidence({ snippet: 'x'.repeat(120) }))).toBe(2)
  })

  it('caps the length bonus of long strings at one point', () => {
    expect(evidenceRichness(evidence({ metric: 'x'.repeat(300) }))).toBe(2)
  })
})

describe('normalizeProfileEvidenceAnchor', () => {
  it('enriches an anchor from the source matched by file hash', () => {
    const source = sourceDocument({
      source_id: 'db:9',
      source_document_type: 'sustainability_report',
      reporting_period_label: 'FY2023',
      source_url: 'https://acme.com/esg.pdf',
      file_hash: 'hash-1',
      pdf_filename: 'acme-esg.pdf',
      period: {
        period_id: 'p1',
        label: 'FY2023',
        type: 'annual',
        source_document_type: 'annual_sustainability_report',
        legacy_report_year: 2023,
      },
      framework_metadata: [
        {
          analysis_result_id: 1,
          framework_id: 'gri',
          framework: 'GRI Standards',
          framework_version: '2021',
          report_year: 2023,
          stored_at: null,
        },
      ],
    })

    const result = normalizeProfileEvidenceAnchor(
      evidence({ source_doc_id: 'hash-1', page_number: 4 }),
      [source],
      'fallback-period',
      'fallback-framework'
    )

    expect(result).toMatchObject({
      page: 4,
      source_type: 'annual_sustainability_report',
      source_url: 'https://acme.com/esg.pdf',
      file_hash: 'hash-1',
      document_title: 'acme-esg.pdf',
      reporting_period_label: 'FY2023',
      framework: 'GRI Standards',
    })
  })

  it('falls back to the first source when the anchor matches nothing', () => {
    const source = sourceDocument({
      reporting_period_label: 'FY2022',
      source_url: 'https://a.com/report.pdf',
      pdf_filename: 'a.pdf',
    })

    const result = normalizeProfileEvidenceAnchor(
      evidence({ source_doc_id: 'missing', source_type: 'pdf' }),
      [source],
      'fallback-period',
      'GRI'
    )

    expect(result).toMatchObject({
      source_type: 'GRI',
      source_url: 'https://a.com/report.pdf',
      document_title: 'a.pdf',
      reporting_period_label: 'FY2022',
      framework: 'pdf',
    })
  })

  it('uses the anchor and null defaults when no sources exist', () => {
    const result = normalizeProfileEvidenceAnchor(
      evidence({ source_type: 'pdf', source_url: 'https://e.com', source: 'ESG report' }),
      [],
      null,
      undefined
    )

    expect(result).toMatchObject({
      page: null,
      source_type: 'pdf',
      source_url: 'https://e.com',
      file_hash: null,
      document_title: 'ESG report',
      reporting_period_label: null,
      framework: 'pdf',
    })
  })
})

describe('parseCompanyReportId', () => {
  it('parses the numeric id after the db prefix', () => {
    expect(parseCompanyReportId('db:42')).toBe(42)
    expect(parseCompanyReportId('db:0')).toBe(0)
  })

  it('rejects other prefixes and malformed ids', () => {
    expect(parseCompanyReportId(null)).toBeNull()
    expect(parseCompanyReportId(undefined)).toBeNull()
    expect(parseCompanyReportId('')).toBeNull()
    expect(parseCompanyReportId('src:42')).toBeNull()
    expect(parseCompanyReportId('db:abc')).toBeNull()
    expect(parseCompanyReportId('db:')).toBeNull()
  })
})

describe('buildCompanyTrendData', () => {
  it('sorts points by year and maps the metric fields', () => {
    const result = buildCompanyTrendData([
      trendPoint({ year: 2024, scope1: 20, renewable_pct: 55, taxonomy_aligned_revenue_pct: 30 }),
      trendPoint({ year: 2022, scope1: 40, renewable_pct: 35, taxonomy_aligned_revenue_pct: 10 }),
    ])

    expect(result).toEqual([
      { year: 2022, scope1: 40, renewable: 35, taxonomy: 10 },
      { year: 2024, scope1: 20, renewable: 55, taxonomy: 30 },
    ])
  })

  it('returns an empty array when there is no trend', () => {
    expect(buildCompanyTrendData([])).toEqual([])
  })
})

describe('prettifyToken', () => {
  it('replaces underscores with spaces', () => {
    expect(prettifyToken('scope1_co2e_tonnes')).toBe('scope1 co2e tonnes')
  })

  it('returns an em dash for empty values', () => {
    expect(prettifyToken(null)).toBe('—')
    expect(prettifyToken(undefined)).toBe('—')
    expect(prettifyToken('')).toBe('—')
  })
})

describe('frameworkRunKey', () => {
  it('prefers the stored analysis result id', () => {
    expect(frameworkRunKey(frameworkResult({ analysis_result_id: 7 }))).toBe('gri|id:7')
  })

  it('falls back to version and analysis timestamp', () => {
    expect(
      frameworkRunKey(
        frameworkResult({ framework_version: 'v2', analyzed_at: '2024-06-01T00:00:00Z' })
      )
    ).toBe('gri|version:v2|at:2024-06-01T00:00:00Z')
  })

  it('uses stored_at and the unknown defaults when metadata is absent', () => {
    expect(frameworkRunKey(frameworkResult({ stored_at: '2024-07-01' }))).toBe(
      'gri|version:v1|at:2024-07-01'
    )
    expect(
      frameworkRunKey(
        frameworkResult({
          framework_version: undefined,
          analyzed_at: null,
          stored_at: null,
        })
      )
    ).toBe('gri|version:unknown-version|at:unknown-time')
  })
})

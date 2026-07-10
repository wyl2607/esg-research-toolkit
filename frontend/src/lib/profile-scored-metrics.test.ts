import { describe, expect, it } from 'vitest'

import {
  buildEvidenceByMetric,
  collectLegacyEvidenceAnchors,
  formatFrameworkMappingLabel,
  scoredMetricEvidenceToAnchor,
} from './profile-scored-metrics'
import type { CompanyProfile, CompanyProfileMetric } from './types'

function baseProfile(overrides: Partial<CompanyProfile> = {}): CompanyProfile {
  const latestMetrics = {
    company_name: 'Demo AG',
    report_year: 2024,
    scope1_co2e_tonnes: 10,
    scope2_co2e_tonnes: null,
    scope3_co2e_tonnes: null,
    energy_consumption_mwh: null,
    renewable_energy_pct: 42,
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
    company_name: 'Demo AG',
    years_available: [2024],
    latest_year: 2024,
    latest_period: {
      report_year: 2024,
      reporting_period_label: 'FY 2024',
      reporting_period_type: 'annual',
      source_document_type: 'sustainability_report',
      industry_code: null,
      industry_sector: null,
      period: {
        period_id: 'p-2024',
        label: 'FY 2024',
        type: 'annual',
        source_document_type: 'sustainability_report',
        legacy_report_year: 2024,
        fiscal_year: 2024,
        reporting_standard: 'sustainability_report',
        period_start: '2024-01-01',
        period_end: '2024-12-31',
      },
      framework_metadata: [],
    },
    latest_metrics: latestMetrics,
    trend: [],
    periods: [],
    framework_results: [],
    evidence_summary: [],
    data_quality_summary: {
      total_key_metrics_count: 1,
      present_metrics_count: 1,
      present_metrics: ['renewable_energy_pct'],
      missing_metrics: [],
      completion_percentage: 100,
      readiness_label: 'usable',
    },
    latest_sources: [],
    latest_merged_result: {
      company_name: 'Demo AG',
      report_year: 2024,
      merged_metrics: latestMetrics,
      metrics: {},
      source_count: 1,
    },
    ...overrides,
  }
}

describe('scoredMetricEvidenceToAnchor', () => {
  it('maps v1 evidence onto EvidenceAnchor with framework mappings', () => {
    const scored: CompanyProfileMetric = {
      metric: 'renewable_energy_pct',
      value: 42,
      unit: '%',
      period: {
        period_id: 'p-2024',
        label: 'FY 2024',
        type: 'annual',
        source_document_type: 'sustainability_report',
        legacy_report_year: 2024,
      },
      source_document_type: 'sustainability_report',
      evidence: {
        source_doc_id: 'doc-1',
        page: 7,
        snippet: 'Renewable share was 42%.',
        extraction_method: 'regex',
        confidence: 0.9,
      },
      framework_mappings: [
        {
          framework_id: 'eu_taxonomy',
          framework_name: 'EU Taxonomy 2020',
          dimension: 'Climate',
        },
      ],
    }

    const anchor = scoredMetricEvidenceToAnchor('renewable_energy_pct', scored)
    expect(anchor).not.toBeNull()
    expect(anchor?.metric).toBe('renewable_energy_pct')
    expect(anchor?.page).toBe(7)
    expect(anchor?.snippet).toContain('42%')
    expect(anchor?.framework_mappings?.[0]?.framework_id).toBe('eu_taxonomy')
  })

  it('returns null when scored metric has no evidence', () => {
    expect(
      scoredMetricEvidenceToAnchor('scope1_co2e_tonnes', {
        metric: 'scope1_co2e_tonnes',
        value: null,
        evidence: null,
      })
    ).toBeNull()
  })
})

describe('buildEvidenceByMetric', () => {
  it('prefers scored_metrics over legacy summary and keeps mappings', () => {
    const profile = baseProfile({
      scored_metrics: {
        renewable_energy_pct: {
          metric: 'renewable_energy_pct',
          value: 42,
          unit: '%',
          period: {
            period_id: 'p-2024',
            label: 'FY 2024',
            type: 'annual',
            source_document_type: 'sustainability_report',
            legacy_report_year: 2024,
          },
          source_document_type: 'sustainability_report',
          evidence: {
            source_doc_id: 'hash-v1',
            page: 3,
            snippet: 'Canonical scored_metrics snippet.',
            extraction_method: 'llm',
            confidence: 0.8,
          },
          framework_mappings: [
            {
              framework_id: 'csrd',
              framework_name: 'CSRD/ESRS',
              dimension: 'E1',
            },
          ],
        },
      },
      evidence_summary: [
        {
          metric: 'renewable_energy_pct',
          source: 'Legacy Report.pdf',
          page: 99,
          snippet: 'Legacy only snippet should enrich, not replace page if empty.',
          document_title: 'Legacy Report.pdf',
          extraction_method: 'manual_entry',
          confidence: 0.5,
          source_type: 'manual_case',
          source_url: null,
          file_hash: null,
        },
      ],
    })

    const map = buildEvidenceByMetric(profile)
    const renewable = map.get('renewable_energy_pct')
    expect(renewable?.snippet).toBe('Canonical scored_metrics snippet.')
    expect(renewable?.page).toBe(3)
    expect(renewable?.document_title).toBe('Legacy Report.pdf')
    expect(renewable?.framework_mappings?.[0]?.framework_id).toBe('csrd')
  })

  it('falls back to legacy anchors when scored_metrics is absent', () => {
    const profile = baseProfile({
      evidence_summary: [
        {
          metric: 'scope1_co2e_tonnes',
          source: 'AR 2024',
          page: 12,
          snippet: 'Scope 1 totalled 10 t.',
          document_title: 'AR 2024',
          extraction_method: 'regex',
          confidence: 0.7,
          source_type: 'annual_report',
          source_url: null,
          file_hash: null,
        },
      ],
    })

    const map = buildEvidenceByMetric(profile)
    expect(map.get('scope1_co2e_tonnes')?.snippet).toContain('10 t')
    expect(collectLegacyEvidenceAnchors(profile)).toHaveLength(1)
  })
})

describe('formatFrameworkMappingLabel', () => {
  it('includes dimension when present', () => {
    expect(
      formatFrameworkMappingLabel({
        framework_id: 'eu_taxonomy',
        framework_name: 'EU Taxonomy 2020',
        dimension: 'Climate',
      })
    ).toBe('EU Taxonomy 2020 · Climate')
  })

  it('falls back to framework name alone', () => {
    expect(
      formatFrameworkMappingLabel({
        framework_id: 'gri',
        framework_name: 'GRI',
      })
    ).toBe('GRI')
  })
})

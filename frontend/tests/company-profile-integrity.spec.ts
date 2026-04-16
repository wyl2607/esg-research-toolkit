import { expect, test } from '@playwright/test'

import type {
  CompanyProfile,
  IndustryBenchmarksResponse,
} from '../src/lib/types'

import { expectNoTrackedBrowserIssues, trackBrowserIssues } from './helpers'

function buildCompanyProfileFixture(): CompanyProfile {
  const latestMetrics = {
    company_name: 'Acme Corp',
    report_year: 2024,
    reporting_period_label: 'FY 2024',
    reporting_period_type: 'annual',
    source_document_type: 'annual_report',
    industry_code: 'DE-123',
    industry_sector: 'Industrial machinery',
    scope1_co2e_tonnes: 120,
    scope2_co2e_tonnes: 80,
    scope3_co2e_tonnes: 450,
    energy_consumption_mwh: 1200,
    renewable_energy_pct: 42.5,
    water_usage_m3: 3000,
    waste_recycled_pct: 66.2,
    total_revenue_eur: 250000000,
    taxonomy_aligned_revenue_pct: 18.4,
    total_capex_eur: 52000000,
    taxonomy_aligned_capex_pct: 12.7,
    total_employees: 4200,
    female_pct: 33.3,
    primary_activities: ['machinery manufacturing'],
    evidence_summary: [],
  }

  return {
    company_name: 'Acme Corp',
    years_available: [2022, 2023, 2024],
    latest_year: 2024,
    latest_period: {
      report_year: 2024,
      reporting_period_label: 'FY 2024',
      reporting_period_type: 'annual',
      source_document_type: 'annual_report',
      industry_code: 'DE-123',
      industry_sector: 'Industrial machinery',
      period: {
        period_id: 'period-2024',
        label: 'FY 2024',
        type: 'annual',
        source_document_type: 'annual_report',
        legacy_report_year: 2024,
      },
      framework_metadata: [],
    },
    latest_metrics: latestMetrics,
    trend: [
      {
        year: 2022,
        scope1: 130,
        scope2: 90,
        scope3: 470,
        renewable_pct: 40.1,
        taxonomy_aligned_revenue_pct: 16.5,
        taxonomy_aligned_capex_pct: 11.1,
        female_pct: 32.8,
      },
      {
        year: 2023,
        scope1: null,
        scope2: null,
        scope3: null,
        renewable_pct: null,
        taxonomy_aligned_revenue_pct: null,
        taxonomy_aligned_capex_pct: null,
        female_pct: null,
      },
      {
        year: 2024,
        scope1: 120,
        scope2: 80,
        scope3: 450,
        renewable_pct: 42.5,
        taxonomy_aligned_revenue_pct: 18.4,
        taxonomy_aligned_capex_pct: 12.7,
        female_pct: 33.3,
      },
    ],
    periods: [
      {
        report_year: 2022,
        reporting_period_label: 'FY 2022',
        reporting_period_type: 'annual',
        source_document_type: 'annual_report',
        industry_code: 'DE-123',
        industry_sector: 'Industrial machinery',
        period: {
          period_id: 'period-2022',
          label: 'FY 2022',
          type: 'annual',
          source_document_type: 'annual_report',
          legacy_report_year: 2022,
        },
        source_url: 'https://example.com/2022.pdf',
        downloaded_at: '2026-04-16T10:00:00Z',
        evidence_anchors: [],
        framework_metadata: [],
        source_documents: [],
        merged_result: {
          company_name: 'Acme Corp',
          report_year: 2022,
          merged_metrics: latestMetrics,
          metrics: {},
          source_count: 1,
        },
      },
      {
        report_year: 2023,
        reporting_period_label: 'FY 2023',
        reporting_period_type: 'annual',
        source_document_type: 'annual_report',
        industry_code: 'DE-123',
        industry_sector: 'Industrial machinery',
        period: {
          period_id: 'period-2023',
          label: 'FY 2023',
          type: 'annual',
          source_document_type: 'annual_report',
          legacy_report_year: 2023,
        },
        source_url: 'https://example.com/2023.pdf',
        downloaded_at: '2026-04-16T10:00:00Z',
        evidence_anchors: [],
        framework_metadata: [],
        source_documents: [],
        merged_result: {
          company_name: 'Acme Corp',
          report_year: 2023,
          merged_metrics: latestMetrics,
          metrics: {},
          source_count: 1,
        },
      },
      {
        report_year: 2024,
        reporting_period_label: 'FY 2024',
        reporting_period_type: 'annual',
        source_document_type: 'annual_report',
        industry_code: 'DE-123',
        industry_sector: 'Industrial machinery',
        period: {
          period_id: 'period-2024',
          label: 'FY 2024',
          type: 'annual',
          source_document_type: 'annual_report',
          legacy_report_year: 2024,
        },
        source_url: 'https://example.com/2024.pdf',
        downloaded_at: '2026-04-16T10:00:00Z',
        evidence_anchors: [],
        framework_metadata: [],
        source_documents: [],
        merged_result: {
          company_name: 'Acme Corp',
          report_year: 2024,
          merged_metrics: latestMetrics,
          metrics: {},
          source_count: 1,
        },
      },
    ],
    framework_metadata: [],
    framework_scores: [],
    framework_results: [],
    evidence_summary: [],
    data_quality_summary: {
      total_key_metrics_count: 5,
      present_metrics_count: 5,
      present_metrics: [
        'scope1_co2e_tonnes',
        'renewable_energy_pct',
        'taxonomy_aligned_revenue_pct',
      ],
      missing_metrics: [],
      completion_percentage: 100,
      readiness_label: 'showcase-ready',
    },
    identity_provenance_summary: {
      canonical_company_name: 'Acme Corp',
      requested_company_name: 'Acme Corp',
      has_alias_consolidation: false,
      consolidated_aliases: [],
      latest_source_document_type: 'annual_report',
      source_priority_preview: null,
      merge_priority_preview: null,
    },
    latest_sources: [
      {
        source_id: 'db:77',
        source_document_type: 'annual_report',
        reporting_period_label: 'FY 2024',
        reporting_period_type: 'annual',
        source_url: 'https://example.com/2024.pdf',
        file_hash: 'fixture-hash',
        pdf_filename: 'acme-2024.pdf',
        downloaded_at: '2026-04-16T10:00:00Z',
        evidence_anchors: [],
      },
    ],
    latest_merged_result: {
      company_name: 'Acme Corp',
      report_year: 2024,
      merged_metrics: latestMetrics,
      metrics: {},
      source_count: 1,
    },
  }
}

function buildBenchmarksFixture(): IndustryBenchmarksResponse {
  return {
    industry_code: 'DE-123',
    metrics: [
      {
        metric_name: 'scope1_co2e_tonnes',
        period_year: 2022,
        p10: 90,
        p25: 110,
        p50: 140,
        p75: 180,
        p90: 220,
        sample_size: 12,
        computed_at: '2026-04-16T10:00:00Z',
      },
      {
        metric_name: 'renewable_energy_pct',
        period_year: 2022,
        p10: 28,
        p25: 34,
        p50: 39,
        p75: 45,
        p90: 52,
        sample_size: 12,
        computed_at: '2026-04-16T10:00:00Z',
      },
      {
        metric_name: 'scope1_co2e_tonnes',
        period_year: 2023,
        p10: 85,
        p25: 105,
        p50: 130,
        p75: 170,
        p90: 210,
        sample_size: 13,
        computed_at: '2026-04-16T10:00:00Z',
      },
      {
        metric_name: 'renewable_energy_pct',
        period_year: 2023,
        p10: 31,
        p25: 36,
        p50: 41,
        p75: 47,
        p90: 55,
        sample_size: 13,
        computed_at: '2026-04-16T10:00:00Z',
      },
    ],
  }
}

test.describe('company profile multi-year integrity', () => {
  test('renders gap-aware trend data and exact-year peer mismatch state', async ({
    page,
  }, testInfo) => {
    const issues = trackBrowserIssues(page)

    await page.route(/\/api\/report\/companies\/Acme%20Corp\/profile$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(buildCompanyProfileFixture()),
      })
    })

    await page.route(/\/api\/benchmarks\/DE-123$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(buildBenchmarksFixture()),
      })
    })

    try {
      await page.goto('/companies/Acme%20Corp', { waitUntil: 'networkidle' })

      await expect(page.getByRole('heading', { level: 1, name: 'Acme Corp' })).toBeVisible()
      await expect(page.getByTestId('company-profile-trend-chart')).toBeVisible()

      const lineDots = page
        .getByTestId('company-profile-trend-chart')
        .locator('.recharts-line-dot')
      await expect(lineDots).toHaveCount(4)

      await expect(page.getByTestId('peer-year-mismatch')).toBeVisible()
      await expect(page.getByTestId('peer-comparison-table')).toHaveCount(0)

      await expectNoTrackedBrowserIssues(testInfo, 'company-profile-integrity', issues)
    } finally {
      await page.unroute(/\/api\/report\/companies\/Acme%20Corp\/profile$/)
      await page.unroute(/\/api\/benchmarks\/DE-123$/)
    }
  })
})

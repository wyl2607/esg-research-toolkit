import { expect, test } from '@playwright/test'

import type { CompanyESGData, CompanyNormalizedPeriod } from '../src/lib/types'

type CompanyListFixture = CompanyESGData & {
  period: CompanyNormalizedPeriod
}

const companies: CompanyListFixture[] = [
  {
    company_name: 'Acme Battery AG',
    report_year: 2024,
    reporting_period_label: 'Legacy 2024',
    reporting_period_type: 'annual',
    source_document_type: 'legacy_source',
    period: {
      period_id: 'acme-fy-2024',
      label: 'FY 2024',
      type: 'annual',
      source_document_type: 'annual_report',
      legacy_report_year: 2024,
      fiscal_year: 2024,
      reporting_standard: 'annual_report',
      period_start: '2024-01-01',
      period_end: '2024-12-31',
    },
    industry_code: 'DE-123',
    industry_sector: 'Battery manufacturing',
    scope1_co2e_tonnes: 120,
    scope2_co2e_tonnes: 80,
    scope3_co2e_tonnes: 450,
    energy_consumption_mwh: 1200,
    renewable_energy_pct: 49.1,
    water_usage_m3: 3000,
    waste_recycled_pct: 66.2,
    total_revenue_eur: 250000000,
    taxonomy_aligned_revenue_pct: 18.4,
    total_capex_eur: 52000000,
    taxonomy_aligned_capex_pct: 12.7,
    total_employees: 4200,
    female_pct: 33.3,
    primary_activities: ['battery manufacturing'],
    evidence_summary: [
      {
        metric: 'renewable_energy_pct',
        source: 'Acme Annual Report 2024',
        source_doc_id: 'db:acme-2024',
        page: 14,
        char_range: [40, 55],
        snippet: 'Renewable electricity reached 49.1%.',
        source_type: 'annual_report',
        reporting_period_label: 'FY 2024',
      },
      {
        metric: 'scope1_co2e_tonnes',
        source: 'Acme Annual Report 2024',
        source_doc_id: 'db:acme-2024',
        page: 8,
        char_range: [12, 30],
        snippet: 'Scope 1 emissions were 120 tCO2e.',
        source_type: 'annual_report',
        reporting_period_label: 'FY 2024',
      },
    ],
  },
  {
    company_name: 'Beta Grid SE',
    report_year: 2024,
    reporting_period_label: 'Legacy 2024',
    reporting_period_type: 'annual',
    source_document_type: 'legacy_source',
    period: {
      period_id: 'beta-fy-2024',
      label: 'FY 2024',
      type: 'annual',
      source_document_type: 'sustainability_report',
      legacy_report_year: 2024,
      fiscal_year: 2024,
      reporting_standard: 'sustainability_report',
      period_start: '2024-01-01',
      period_end: '2024-12-31',
    },
    industry_code: 'DE-124',
    industry_sector: 'Grid storage',
    scope1_co2e_tonnes: 92,
    scope2_co2e_tonnes: 70,
    scope3_co2e_tonnes: 390,
    energy_consumption_mwh: 980,
    renewable_energy_pct: 55.5,
    water_usage_m3: 2500,
    waste_recycled_pct: 70.1,
    total_revenue_eur: 210000000,
    taxonomy_aligned_revenue_pct: 21.8,
    total_capex_eur: 48000000,
    taxonomy_aligned_capex_pct: 15.4,
    total_employees: 3600,
    female_pct: 38.1,
    primary_activities: ['grid storage'],
    evidence_summary: [
      {
        metric: 'renewable_energy_pct',
        source: 'Beta Sustainability Report 2024',
        source_doc_id: 'db:beta-2024',
        page: 19,
        char_range: [10, 32],
        snippet: 'Renewable electricity reached 55.5%.',
        source_type: 'sustainability_report',
        reporting_period_label: 'FY 2024',
      },
    ],
  },
]

test.describe('compare source-document contract', () => {
  test('renders normalized source context for selected companies', async ({ page }) => {
    await page.route(/\/api\/report\/companies$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(companies),
      })
    })

    try {
      await page.goto('/compare', { waitUntil: 'networkidle' })
      await page.getByRole('button', { name: 'Acme Battery AG' }).click()
      await page.getByRole('button', { name: 'Beta Grid SE' }).click()

      await expect(page.getByTestId('compare-source-summary-0')).toContainText('FY 2024')
      await expect(page.getByTestId('compare-source-summary-0')).toContainText('annual report')
      await expect(page.getByTestId('compare-source-evidence-count-0')).toHaveText('2')
      await expect(page.getByTestId('compare-table-source-context-0')).toContainText('FY 2024')
      await expect(page.getByTestId('compare-table-source-context-0')).toContainText(
        'annual report'
      )

      await expect(page.getByTestId('compare-source-summary-1')).toContainText('FY 2024')
      await expect(page.getByTestId('compare-source-summary-1')).toContainText(
        'sustainability report'
      )
      await expect(page.getByTestId('compare-source-evidence-count-1')).toHaveText('1')
      await expect(page.getByTestId('compare-table-source-context-1')).toContainText('FY 2024')
      await expect(page.getByTestId('compare-table-source-context-1')).toContainText(
        'sustainability report'
      )
    } finally {
      await page.unroute(/\/api\/report\/companies$/)
    }
  })
})

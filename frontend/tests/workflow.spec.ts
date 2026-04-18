import { expect, test } from '@playwright/test'

import { expectNoTrackedBrowserIssues, trackBrowserIssues } from './helpers'
import {
  addManualSourceToSeededCompany,
  deleteSeededCompany,
  seedManualCompany,
} from './seeded-company'

test.describe('seeded analyst workflow', () => {
  test('companies list navigates into a seeded profile route without browser issues', async ({
    page,
    request,
  }, testInfo) => {
    const seeded = await seedManualCompany(request, testInfo)
    await addManualSourceToSeededCompany(request, seeded, {
      source_document_type: 'sustainability_fact_sheet',
      source_url: `${seeded.payload.source_url}/supplement`,
      renewable_energy_pct: 49.1,
      taxonomy_aligned_revenue_pct: 34.2,
      evidence_summary: [
        {
          metric: 'renewable_energy_pct',
          source: 'supplement appendix',
          page: 5,
          snippet: 'Renewable electricity share reached 49.1% in FY 2025.',
          source_type: 'sustainability_fact_sheet',
        },
      ],
    })
    const issues = trackBrowserIssues(page)

    try {
      await page.goto('/companies', { waitUntil: 'networkidle' })
      await expect(page.getByRole('main')).toBeVisible()

      const searchInput = page.getByRole('textbox').first()
      await expect(searchInput).toBeVisible()
      await searchInput.fill(seeded.companyName)

      const companyCardHeading = page.getByRole('heading', {
        level: 2,
        name: seeded.companyName,
      })
      await expect(companyCardHeading).toBeVisible()

      const profileResponsePromise = page.waitForResponse((response) => {
        const url = new URL(response.url())
        return (
          url.pathname === `/api/report/companies/${encodeURIComponent(seeded.companyName)}/profile` &&
          response.status() === 200
        )
      })

      const [profileResponse] = await Promise.all([
        profileResponsePromise,
        page.waitForURL((url) => url.pathname === seeded.profilePath),
        companyCardHeading.click(),
      ])
      const profileJson = await profileResponse.json()
      expect(profileJson.latest_sources?.length).toBeGreaterThanOrEqual(2)
      expect(profileJson.latest_merged_result?.source_count).toBeGreaterThanOrEqual(2)
      expect(
        (profileJson.latest_sources ?? []).some(
          (source: { source_document_type?: string | null }) =>
            source.source_document_type === 'sustainability_fact_sheet'
        )
      ).toBeTruthy()

      await expect(
        page.getByRole('heading', { level: 1, name: seeded.companyName })
      ).toBeVisible()
      await expect(page.locator('main')).toContainText(seeded.payload.reporting_period_label ?? '')
      await expect(page.locator('main')).toContainText(seeded.payload.source_document_type ?? '')
      await expect(page.getByTestId('profile-provenance-source-summary')).toContainText(/\b2\b/)
      await expect(page.getByTestId('profile-provenance-source-types')).toContainText(
        'sustainability fact sheet'
      )
      await expect(page.getByTestId('profile-provenance-merge-summary')).toContainText(/\b2\b/)
      await page.getByTestId('evidence-badge-renewable_energy_pct').click()
      await expect(
        page.getByTestId('evidence-badge-renewable_energy_pct-popover')
      ).toBeVisible()
      await page.waitForLoadState('networkidle')

      await expectNoTrackedBrowserIssues(testInfo, 'seeded-company-profile', issues)
    } finally {
      await deleteSeededCompany(request, seeded)
    }
  })

  test('frameworks page can select and score a seeded company without browser issues', async ({
    page,
    request,
  }, testInfo) => {
    const seeded = await seedManualCompany(request, testInfo)
    const issues = trackBrowserIssues(page)

    try {
      await page.goto('/frameworks', { waitUntil: 'networkidle' })
      await expect(page.getByRole('main')).toBeVisible()

      const companySelect = page.getByRole('combobox').first()
      await expect(companySelect).toBeVisible()

      const comparisonResponse = page.waitForResponse((response) => {
        const url = new URL(response.url())
        return (
          url.pathname === '/api/frameworks/compare' &&
          url.searchParams.get('company_name') === seeded.companyName &&
          url.searchParams.get('report_year') === String(seeded.reportYear) &&
          response.status() === 200
        )
      })

      await companySelect.click()
      const companyOption = page.getByRole('option', { name: seeded.optionLabel })
      await expect(companyOption).toBeVisible()
      await companyOption.click()

      await comparisonResponse
      await expect(companySelect).toContainText(seeded.companyName)

      const frameworkHeadings = page.locator('main h3')
      await expect(frameworkHeadings.first()).toBeVisible()
      expect(await frameworkHeadings.count()).toBeGreaterThan(0)
      await page.waitForLoadState('networkidle')

      await expectNoTrackedBrowserIssues(testInfo, 'seeded-frameworks-workflow', issues)
    } finally {
      await deleteSeededCompany(request, seeded)
    }
  })

  test('frameworks picker routes not-imported years to upload deep-link', async ({
    page,
    request,
  }, testInfo) => {
    const seeded = await seedManualCompany(request, testInfo)
    const missingYear = seeded.reportYear - 1
    const issues = trackBrowserIssues(page)

    try {
      await page.goto('/frameworks', { waitUntil: 'networkidle' })
      await expect(page.getByRole('main')).toBeVisible()

      const companySelect = page.getByRole('combobox').first()
      await companySelect.click()
      await page.getByRole('option', { name: seeded.companyName }).click()

      const yearSelect = page.getByRole('combobox').nth(1)
      await yearSelect.click()
      await page.getByRole('option', { name: new RegExp(`^${missingYear}\\b`) }).click()

      await page.waitForURL((url) => url.pathname === '/upload')
      const current = new URL(page.url())
      expect(current.searchParams.get('company')).toBe(seeded.companyName)
      expect(current.searchParams.get('year')).toBe(String(missingYear))
      await expect(page.locator('main')).toContainText(seeded.companyName)
      await expect(page.locator('main')).toContainText(String(missingYear))
      await page.waitForLoadState('networkidle')

      await expectNoTrackedBrowserIssues(testInfo, 'frameworks-missing-year-upload-handoff', issues)
    } finally {
      await deleteSeededCompany(request, seeded)
    }
  })
})

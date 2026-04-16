import { expect, test } from '@playwright/test'

import {
  buildEvidenceBenchmarksFixture,
  buildEvidenceCompanyProfileFixture,
} from './company-profile-evidence-fixtures'
import { expectNoTrackedBrowserIssues, trackBrowserIssues } from './helpers'

test.describe('company profile evidence workflow', () => {
  test('opens an evidence badge popover and shows the supporting snippet', async ({
    page,
  }, testInfo) => {
    const issues = trackBrowserIssues(page)

    await page.route(/\/api\/report\/companies\/Acme%20Corp\/profile$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(buildEvidenceCompanyProfileFixture()),
      })
    })

    await page.route(/\/api\/benchmarks\/DE-123$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(buildEvidenceBenchmarksFixture()),
      })
    })

    try {
      await page.goto('/companies/Acme%20Corp', { waitUntil: 'networkidle' })

      const badge = page.getByTestId('evidence-badge-renewable_energy_pct')
      await expect(badge).toBeVisible()

      await badge.click()

      const popover = page.getByTestId('evidence-badge-renewable_energy_pct-popover')
      await expect(popover).toBeVisible()
      await expect(popover).toContainText(
        'Renewable electricity share reached 49.1% in FY 2024'
      )
      await expect(popover).toContainText('manual entry')
      await expect(popover).toContainText('Acme Sustainability Fact Sheet 2024')

      await expect(popover).toHaveScreenshot('company-profile-evidence-popover.png')
      await expectNoTrackedBrowserIssues(testInfo, 'company-profile-evidence', issues)
    } finally {
      await page.unroute(/\/api\/report\/companies\/Acme%20Corp\/profile$/)
      await page.unroute(/\/api\/benchmarks\/DE-123$/)
    }
  })
})

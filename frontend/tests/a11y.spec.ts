import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

import {
  buildEvidenceBenchmarksFixture,
  buildEvidenceCompanyProfileFixture,
} from './company-profile-evidence-fixtures'
import { a11yRoutes, expectHealthyPage } from './helpers'

test.describe('frontend accessibility', () => {
  for (const route of a11yRoutes) {
    test(`${route.path} has no serious axe violations`, async ({ page }, testInfo) => {
      await expectHealthyPage(page, testInfo, route)

      const axe = await new AxeBuilder({ page }).analyze()
      const violations = axe.violations.filter((violation) =>
        ['serious', 'critical'].includes((violation.impact || '').toLowerCase())
      )

      await testInfo.attach(`${route.name}-axe.json`, {
        body: JSON.stringify(
          violations.map((violation) => ({
            id: violation.id,
            impact: violation.impact,
            help: violation.help,
            nodes: violation.nodes.length,
          })),
          null,
          2
        ),
        contentType: 'application/json',
      })

      expect(
        violations,
        `${route.path} should not have serious or critical axe violations`
      ).toEqual([])
    })
  }

  test('company profile evidence popover has no serious axe violations', async ({
    page,
  }, testInfo) => {
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
      await page.getByTestId('evidence-badge-renewable_energy_pct').click()

      const axe = await new AxeBuilder({ page }).analyze()
      const violations = axe.violations.filter((violation) =>
        ['serious', 'critical'].includes((violation.impact || '').toLowerCase())
      )

      await testInfo.attach('company-profile-evidence-axe.json', {
        body: JSON.stringify(
          violations.map((violation) => ({
            id: violation.id,
            impact: violation.impact,
            help: violation.help,
            nodes: violation.nodes.length,
          })),
          null,
          2
        ),
        contentType: 'application/json',
      })

      expect(
        violations,
        'company profile evidence popover should not have serious or critical axe violations'
      ).toEqual([])
    } finally {
      await page.unroute(/\/api\/report\/companies\/Acme%20Corp\/profile$/)
      await page.unroute(/\/api\/benchmarks\/DE-123$/)
    }
  })
})

import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

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
})

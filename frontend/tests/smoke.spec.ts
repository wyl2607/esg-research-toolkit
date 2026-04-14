import { test } from '@playwright/test'

import { expectHealthyPage, smokeRoutes } from './helpers'

test.describe('frontend smoke routes', () => {
  for (const route of smokeRoutes) {
    test(`${route.path} renders without critical browser errors`, async ({
      page,
    }, testInfo) => {
      await expectHealthyPage(page, testInfo, route)
    })
  }
})

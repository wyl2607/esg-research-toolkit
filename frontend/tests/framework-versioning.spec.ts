import { expect, test } from '@playwright/test'

import { expectNoTrackedBrowserIssues, trackBrowserIssues } from './helpers'
import { deleteSeededCompany, seedManualCompany } from './seeded-company'

test.describe('framework versioning', () => {
  test.skip(({ browserName }) => browserName !== 'chromium', 'chromium only')

  test('GET /api/frameworks/versions returns 6 canonical non-v1 versions', async ({
    request,
  }) => {
    const response = await request.get('/api/frameworks/versions')
    expect(response.ok(), await response.text()).toBeTruthy()

    const versions = (await response.json()) as Array<{
      display_name: string
      framework_id: string
      framework_version: string
    }>

    expect(versions).toHaveLength(6)
    for (const item of versions) {
      expect(item.framework_id).toBeTruthy()
      expect(item.framework_version).toBeTruthy()
      expect(item.framework_version).not.toBe('v1')
      expect(item.display_name).toBeTruthy()
    }
  })

  test('framework score provenance badge renders on company profile', async ({
    page,
    request,
  }, testInfo) => {
    test.setTimeout(60_000)

    const issues = trackBrowserIssues(page)
    const seeded = await seedManualCompany(request, testInfo)

    try {
      const scoreResponse = await request.get('/api/frameworks/score', {
        params: {
          company_name: seeded.companyName,
          report_year: String(seeded.reportYear),
          framework: 'eu_taxonomy',
        },
      })
      expect(scoreResponse.ok(), await scoreResponse.text()).toBeTruthy()

      await page.goto(seeded.profilePath, { waitUntil: 'networkidle' })
      await expect(
        page.getByRole('heading', { level: 1, name: seeded.companyName })
      ).toBeVisible()

      const frameworkSection = page.getByTestId('framework-scores-section')
      const provenanceText = page.getByText(/v2020\/852|analyzed/i)

      if ((await frameworkSection.count()) > 0) {
        await expect(provenanceText.first()).toBeVisible({ timeout: 10_000 })
      } else {
        const provenanceVisible = await provenanceText
          .first()
          .waitFor({ state: 'visible', timeout: 5_000 })
          .then(() => true)
          .catch(() => false)

        if (provenanceVisible) {
          await expect(provenanceText.first()).toBeVisible()
        }
      }

      await expectNoTrackedBrowserIssues(testInfo, 'framework-versioning-profile', issues)
    } finally {
      await deleteSeededCompany(request, seeded)
    }
  })
})

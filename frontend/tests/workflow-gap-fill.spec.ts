import { expect, test } from '@playwright/test'

import { expectNoTrackedBrowserIssues, trackBrowserIssues } from './helpers'
import { deleteSeededCompany, seedManualCompany } from './seeded-company'

test.describe('workflow gap-fill journey', () => {
  test('picker missing year can flow through pending disclosures approval into companies list', async ({
    page,
    request,
  }, testInfo) => {
    test.setTimeout(90_000)
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
      await expect(page.locator('main')).toContainText(seeded.companyName)
      await expect(page.locator('main')).toContainText(String(missingYear))

      const sourceUrl = `https://example.com/${encodeURIComponent(seeded.companyName)}/${missingYear}-${Date.now()}.pdf`
      await page.getByTestId('auto-fetch-source-url').fill(sourceUrl)
      await page.locator('#auto-fetch-source-hint').selectOption('sec_edgar')
      await page.locator('#auto-fetch-source-type').selectOption('pdf')
      await page.getByTestId('auto-fetch-trigger').click()

      const uploadPendingItem = page.getByTestId('pending-disclosure-item').first()
      await expect(uploadPendingItem).toContainText(sourceUrl)

      await page.goto('/disclosures', { waitUntil: 'networkidle' })
      await expect(page.getByRole('main')).toBeVisible()

      const pendingRow = page
        .getByTestId('pending-disclosure-row')
        .filter({ hasText: seeded.companyName })
        .filter({ hasText: String(missingYear) })
        .filter({ hasText: sourceUrl })
      await expect(pendingRow.first()).toBeVisible()

      const approveButton = pendingRow
        .first()
        .getByRole('button', { name: /freigeben|approve|genehmigen|批准|承认/i })
      await expect(approveButton).toBeVisible()
      await approveButton.click()

      await expect(pendingRow).toHaveCount(0)

      await expect
        .poll(async () => {
          const response = await request.get(
            `/api/report/companies/${encodeURIComponent(seeded.companyName)}/${missingYear}`
          )
          return response.status()
        })
        .toBe(200)

      await page.goto('/companies', { waitUntil: 'networkidle' })
      const searchInput = page.getByRole('textbox').first()
      await searchInput.fill(seeded.companyName)

      const companyCard = page
        .locator('[class*="group"]')
        .filter({ hasText: seeded.companyName })
        .filter({ hasText: String(missingYear) })
        .first()
      await expect(companyCard).toBeVisible()
      await expect(companyCard).toContainText(String(missingYear))

      await expectNoTrackedBrowserIssues(testInfo, 'workflow-gap-fill', issues)
    } finally {
      const cleanupMissing = await request.delete(
        `/api/report/companies/${encodeURIComponent(seeded.companyName)}/${missingYear}?hard=true`
      )
      expect([200, 404]).toContain(cleanupMissing.status())
      await deleteSeededCompany(request, seeded, { allowMissing: true })
    }
  })
})

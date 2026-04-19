import { expect, test } from '@playwright/test'

import { expectNoTrackedBrowserIssues, trackBrowserIssues } from './helpers'

type CompanyCoverage = {
  company_name: string
  imported_years: number[]
}

test.describe('company profile trend visualization', () => {
  test('renders multi-year trend dots and YoY delta card', async ({
    page,
    request,
  }, testInfo) => {
    test.setTimeout(60_000)
    const issues = trackBrowserIssues(page)

    const coverageResponse = await request.get('/api/report/companies/v2')
    expect(coverageResponse.ok(), await coverageResponse.text()).toBeTruthy()
    const companies = (await coverageResponse.json()) as CompanyCoverage[]
    const targetCompany = companies.find(
      (entry) => Array.isArray(entry.imported_years) && entry.imported_years.length >= 3
    )
    expect(
      targetCompany,
      'Expected at least one company with >=3 imported years for trend assertions'
    ).toBeTruthy()

    await page.goto(`/companies/${encodeURIComponent(targetCompany!.company_name)}`, {
      waitUntil: 'networkidle',
    })

    const trendChart = page.getByTestId('company-profile-trend-chart')
    await expect(trendChart).toBeVisible()

    await expect
      .poll(async () => trendChart.locator('.recharts-dot').count())
      .toBeGreaterThanOrEqual(3)

    await expect(page.getByTestId('yoy-delta-card')).toBeVisible()

    await expectNoTrackedBrowserIssues(testInfo, 'trend-visualization', issues)
  })
})

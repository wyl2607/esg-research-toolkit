import { expect, test } from '@playwright/test'

import { expectHealthyPage, expectNoTrackedBrowserIssues, smokeRoutes, trackBrowserIssues } from './helpers'
import { deleteSeededCompany, seedManualCompany } from './seeded-company'

test.describe('frontend smoke routes', () => {
  for (const route of smokeRoutes) {
    test(`${route.path} renders without critical browser errors`, async ({
      page,
    }, testInfo) => {
      await expectHealthyPage(page, testInfo, route)
    })
  }

  test('pending disclosures page can approve a queued disclosure into companies', async ({
    page,
    request,
  }, testInfo) => {
    test.setTimeout(60_000)
    const seedId = `${Date.now()}-${testInfo.project.name}`.replace(/[^a-zA-Z0-9-]/g, '')
    const companyName = `Smoke Pending ${seedId}`.slice(0, 80)
    const reportYear = 2024
    const encodedCompany = encodeURIComponent(companyName)
    const sourceUrl = `https://example.com/${seedId}/disclosure.pdf`
    const issues = trackBrowserIssues(page)

    let pendingId: number | null = null

    try {
      const cleanupBefore = await request.delete(`/api/report/companies/${encodedCompany}/${reportYear}?hard=true`)
      expect([200, 404]).toContain(cleanupBefore.status())

      const queued = await request.post('/api/disclosures/fetch', {
        data: {
          company_name: companyName,
          report_year: reportYear,
          source_url: sourceUrl,
          source_type: 'pdf',
          source_hint: 'company_site',
        },
      })
      expect(queued.ok(), await queued.text()).toBeTruthy()
      const queuedBody = (await queued.json()) as { pending: { id: number } }
      pendingId = queuedBody.pending.id

      await page.goto('/disclosures', { waitUntil: 'networkidle' })
      const pendingRow = page
        .locator('[data-testid="pending-disclosure-row"]')
        .filter({ hasText: companyName })
        .first()
      await expect(pendingRow).toBeVisible()

      await pendingRow.getByTestId(`pending-approve-${pendingId}`).click()

      await expect
        .poll(async () => {
          const res = await request.get('/api/disclosures/pending', {
            params: {
              company_name: companyName,
              report_year: String(reportYear),
              status: 'pending',
              limit: '5',
            },
          })
          if (!res.ok()) return ['request-failed']
          const body = (await res.json()) as Array<{ id: number }>
          return body.map((row) => row.id)
        }, { timeout: 20_000 })
        .toEqual([])

      await page.waitForLoadState('networkidle')
      await page.goto('/companies', { waitUntil: 'networkidle' })
      const searchInput = page.getByRole('textbox').first()
      await searchInput.fill(companyName)
      await expect(page.getByRole('heading', { level: 2, name: companyName })).toBeVisible()

      await expect
        .poll(async () => {
          const profileResponse = await request.get(`/api/api/v1/companies/${encodedCompany}/profile`)
          if (!profileResponse.ok()) return false
          const profileBody = (await profileResponse.json()) as {
            evidence_summary?: Array<{ metric?: string; source_url?: string }>
            latest_sources?: Array<{ source_url?: string | null }>
          }
          const hasSource = profileBody.latest_sources?.some(
            (source) => source.source_url === sourceUrl
          )
          const hasReviewEvidence = profileBody.evidence_summary?.some(
            (entry) =>
              entry.metric === 'auto_disclosure_review' &&
              entry.source_url === sourceUrl
          )
          return Boolean(hasSource && hasReviewEvidence)
        }, { timeout: 20_000 })
        .toBe(true)

      await page.waitForLoadState('networkidle')
      await page.goto(`/companies/${encodedCompany}`, { waitUntil: 'networkidle' })
      await expect(page.getByRole('heading', { level: 1, name: companyName })).toBeVisible()
      await expect(page.getByTestId('profile-provenance-source-summary')).toContainText('1')
      const sourceDocument = page
        .locator('[data-testid^="profile-provenance-source-document-"]')
        .filter({ hasText: sourceUrl })
        .filter({ has: page.locator('[data-testid$="-evidence-count"]') })
        .first()
      await expect(sourceDocument).toBeVisible()
      await expect(sourceDocument.locator('[data-testid$="-evidence-count"]')).not.toHaveText('0')

      await expectNoTrackedBrowserIssues(testInfo, 'pending-disclosures-approve-smoke', issues)
    } finally {
      if (pendingId != null) {
        const pending = await request.get('/api/disclosures/pending', {
          params: {
            company_name: companyName,
            report_year: String(reportYear),
            status: 'pending',
            limit: '5',
          },
        })
        if (pending.ok()) {
          const rows = (await pending.json()) as Array<{ id: number }>
          if (rows.some((row) => row.id === pendingId)) {
            await request.post(`/api/disclosures/${pendingId}/reject`, {
              data: { review_note: 'playwright-cleanup' },
            })
          }
        }
      }

      const cleanupAfter = await request.delete(`/api/report/companies/${encodedCompany}/${reportYear}?hard=true`)
      expect([200, 404]).toContain(cleanupAfter.status())
    }
  })

  test('company profile evidence summary badge renders for seeded evidence anchors', async ({
    page,
    request,
  }, testInfo) => {
    test.setTimeout(60_000)
    const issues = trackBrowserIssues(page)
    const seeded = await seedManualCompany(request, testInfo, {
      evidence_summary: [
        {
          metric: 'renewable_energy_pct',
          document_title: 'Annual sustainability annex',
          page: 12,
          source_type: 'manual_case',
          reporting_period_label: 'FY 2025',
        },
      ],
    })

    try {
      await page.goto(seeded.profilePath, { waitUntil: 'networkidle' })
      await expect(
        page.getByRole('heading', { level: 1, name: seeded.companyName })
      ).toBeVisible()
      await expect(page.getByTestId('evidence-summary-renewable_energy_pct')).toBeVisible()

      await expectNoTrackedBrowserIssues(testInfo, 'company-profile-evidence-summary', issues)
    } finally {
      await deleteSeededCompany(request, seeded)
    }
  })

  test('manual case builder form panel keeps core fields interactive', async ({ page }, testInfo) => {
    test.setTimeout(60_000)
    const issues = trackBrowserIssues(page)

    await page.goto('/manual', { waitUntil: 'networkidle' })

    const companyInput = page.locator('#company_name')
    const yearInput = page.locator('#report_year')
    const industrySelect = page.locator('#manual-industry-code')
    const saveButton = page.getByRole('button', { name: /fall speichern|save case|保存案例/i })
    const resetButton = page.getByRole('button', { name: /zurücksetzen|reset|重置/i })

    await expect(companyInput).toBeVisible()
    await expect(yearInput).toBeVisible()
    await expect(industrySelect).toBeVisible()
    await expect(page.locator('#primary_activities')).toBeVisible()
    await expect(saveButton).toBeDisabled()
    await expect(resetButton).toBeEnabled()

    await companyInput.fill('Smoke Manual Case')
    await yearInput.fill('2025')
    await expect(saveButton).toBeEnabled()

    await expectNoTrackedBrowserIssues(testInfo, 'manual-case-form-panel', issues)
  })

  test('navigation prioritizes the disclosure analyst workflow before optional tools', async ({
    page,
  }, testInfo) => {
    test.skip(
      testInfo.project.name !== 'desktop-chrome',
      'Navigation grouping is viewport-independent and is covered once to keep smoke stable.'
    )
    test.setTimeout(60_000)
    const issues = trackBrowserIssues(page)

    await page.goto('/', { waitUntil: 'networkidle' })
    const mobileMenuButton = page.getByRole('button', {
      name: /open navigation menu|navigationsmenü öffnen|打开导航菜单/i,
    })
    if (await mobileMenuButton.isVisible()) {
      await mobileMenuButton.click()
    }

    const primaryWorkflow = page.getByTestId('primary-workflow-nav')
    await expect(primaryWorkflow.getByRole('link', { name: /companies|unternehmen|公司列表/i })).toBeVisible()
    await expect(primaryWorkflow.getByRole('link', { name: /pending disclosures|ausstehende offenlegungen|待审核披露/i })).toBeVisible()
    await expect(primaryWorkflow.getByRole('link', { name: /compare|vergleich|对比分析/i })).toBeVisible()
    await expect(primaryWorkflow.getByRole('link', { name: /frameworks|rahmenwerke|多框架/i })).toBeVisible()
    await expect(primaryWorkflow.getByRole('link', { name: /lcoe|度电成本/i })).toHaveCount(0)
    await expect(primaryWorkflow.getByRole('link', { name: /saf|可持续航空燃油/i })).toHaveCount(0)

    const optionalTools = page.getByTestId('optional-tools-nav')
    await expect(optionalTools.getByRole('link', { name: /lcoe|度电成本/i })).toBeVisible()
    await expect(optionalTools.getByRole('link', { name: /saf|可持续航空燃油/i })).toBeVisible()

    await expectNoTrackedBrowserIssues(testInfo, 'navigation-workflow-priority', issues)
  })
})

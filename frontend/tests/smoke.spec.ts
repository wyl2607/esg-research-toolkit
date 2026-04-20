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
        })
        .toEqual([])

      await page.goto('/companies', { waitUntil: 'networkidle' })
      const searchInput = page.getByRole('textbox').first()
      await searchInput.fill(companyName)
      await expect(page.getByRole('heading', { level: 2, name: companyName })).toBeVisible()

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
})

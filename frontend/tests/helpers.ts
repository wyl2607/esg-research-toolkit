import { expect, type Page, type TestInfo } from '@playwright/test'

export type RouteExpectation = {
  path: string
  heading: string
  name: string
}

export const smokeRoutes: RouteExpectation[] = [
  { path: '/', heading: 'Dashboard', name: 'dashboard' },
  { path: '/upload', heading: 'ESG-Bericht hochladen', name: 'upload' },
  { path: '/manual', heading: 'Manuelle Eingabe / Case Builder', name: 'manual' },
  { path: '/design-lab', heading: 'Design-Labor', name: 'design-lab' },
  { path: '/taxonomy', heading: 'Taxonomie-Bewertung', name: 'taxonomy' },
  { path: '/lcoe', heading: 'Stromgestehungskosten-Analyse', name: 'lcoe' },
  { path: '/companies', heading: 'Unternehmen', name: 'companies' },
  { path: '/compare', heading: 'Unternehmensvergleich', name: 'compare' },
  { path: '/frameworks', heading: 'Multi-Rahmenwerk ESG', name: 'frameworks' },
  { path: '/regional', heading: 'Drei-Regionen ESG-Vergleich', name: 'regional' },
]

export const a11yRoutes: RouteExpectation[] = smokeRoutes.filter((route) =>
  ['/', '/upload', '/companies', '/design-lab', '/frameworks'].includes(route.path)
)

export function trackBrowserIssues(page: Page) {
  const consoleErrors: string[] = []
  const pageErrors: string[] = []
  const networkErrors: string[] = []

  page.on('console', (msg) => {
    if (msg.type() !== 'error') return
    consoleErrors.push(normalizeMessage(msg.text()))
  })

  page.on('pageerror', (error) => {
    pageErrors.push(normalizeMessage(error.message))
  })

  page.on('requestfailed', (request) => {
    const failure = request.failure()?.errorText || 'request failed'
    networkErrors.push(
      normalizeMessage(`${request.method()} ${request.url()} -> ${failure}`)
    )
  })

  page.on('response', (response) => {
    if (response.status() < 500) return
    networkErrors.push(
      normalizeMessage(
        `${response.request().method()} ${response.url()} -> HTTP ${response.status()}`
      )
    )
  })

  return { consoleErrors, pageErrors, networkErrors }
}

export async function expectHealthyPage(
  page: Page,
  testInfo: TestInfo,
  route: RouteExpectation
) {
  const issues = trackBrowserIssues(page)

  await page.goto(route.path, { waitUntil: 'networkidle' })
  await expect(page.getByRole('main')).toBeVisible()
  await expect(page.getByRole('heading', { level: 1, name: route.heading })).toBeVisible()

  const browserIssues = {
    consoleErrors: dedupe(issues.consoleErrors),
    pageErrors: dedupe(issues.pageErrors),
    networkErrors: dedupe(issues.networkErrors),
  }

  await testInfo.attach(`${route.name}-browser-issues.json`, {
    body: JSON.stringify(browserIssues, null, 2),
    contentType: 'application/json',
  })

  expect(browserIssues.consoleErrors, `${route.path} has console errors`).toEqual([])
  expect(browserIssues.pageErrors, `${route.path} has page errors`).toEqual([])
  expect(browserIssues.networkErrors, `${route.path} has network errors`).toEqual([])
}

function normalizeMessage(message: string) {
  return message.replace(/\s+/g, ' ').trim()
}

function dedupe(values: string[]) {
  return [...new Set(values)]
}

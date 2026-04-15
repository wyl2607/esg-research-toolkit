import { expect, type Page, type TestInfo } from '@playwright/test'

export type RouteExpectation = {
  path: string
  heading: string
  name: string
}

export type BrowserIssueTracker = ReturnType<typeof trackBrowserIssues>

export type BrowserIssues = {
  consoleErrors: string[]
  pageErrors: string[]
  networkErrors: string[]
}

export const smokeRoutes: RouteExpectation[] = [
  { path: '/', heading: 'Dashboard', name: 'dashboard' },
  { path: '/upload', heading: 'ESG-Bericht hochladen', name: 'upload' },
  { path: '/manual', heading: 'Manuelle Eingabe / Case Builder', name: 'manual' },
  { path: '/taxonomy', heading: 'EU-Taxonomie Offenlegungsspiegel', name: 'taxonomy' },
  { path: '/lcoe', heading: 'Stromgestehungskosten-Analyse', name: 'lcoe' },
  { path: '/companies', heading: 'Unternehmen', name: 'companies' },
  { path: '/compare', heading: 'Unternehmensvergleich', name: 'compare' },
  { path: '/benchmarks', heading: 'Branchenbenchmarks', name: 'benchmarks' },
  { path: '/frameworks', heading: 'Multi-Rahmenwerk ESG', name: 'frameworks' },
  { path: '/regional', heading: 'Drei-Regionen ESG-Vergleich', name: 'regional' },
]

export const a11yRoutes: RouteExpectation[] = smokeRoutes.filter((route) =>
  ['/', '/upload', '/companies', '/frameworks'].includes(route.path)
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
    if (shouldIgnoreFailedRequest(request.url(), failure)) return
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

export function buildBrowserIssues(tracker: BrowserIssueTracker): BrowserIssues {
  return {
    consoleErrors: dedupe(tracker.consoleErrors),
    pageErrors: dedupe(tracker.pageErrors),
    networkErrors: dedupe(tracker.networkErrors),
  }
}

export async function attachBrowserIssues(
  testInfo: TestInfo,
  name: string,
  tracker: BrowserIssueTracker
) {
  const browserIssues = buildBrowserIssues(tracker)

  await testInfo.attach(`${name}-browser-issues.json`, {
    body: JSON.stringify(browserIssues, null, 2),
    contentType: 'application/json',
  })

  return browserIssues
}

export async function expectNoTrackedBrowserIssues(
  testInfo: TestInfo,
  name: string,
  tracker: BrowserIssueTracker
) {
  const browserIssues = await attachBrowserIssues(testInfo, name, tracker)

  expect(browserIssues.consoleErrors, `${name} has console errors`).toEqual([])
  expect(browserIssues.pageErrors, `${name} has page errors`).toEqual([])
  expect(browserIssues.networkErrors, `${name} has network errors`).toEqual([])
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

  await expectNoTrackedBrowserIssues(testInfo, route.name, issues)
}

function normalizeMessage(message: string) {
  return message.replace(/\s+/g, ' ').trim()
}

function shouldIgnoreFailedRequest(url: string, failure: string) {
  if (!failure.includes('net::ERR_ABORTED')) return false

  try {
    const parsed = new URL(url)
    const isLocalPreview =
      (parsed.hostname === '127.0.0.1' || parsed.hostname === 'localhost') &&
      parsed.port === '4173'
    const isGoogleFontsStylesheet =
      parsed.hostname === 'fonts.googleapis.com' &&
      parsed.pathname === '/css2'
    const isModuleAsset =
      parsed.pathname.startsWith('/node_modules/.vite/deps/') ||
      parsed.pathname.startsWith('/src/') ||
      /\.(js|ts|tsx|css)$/.test(parsed.pathname)

    return (isLocalPreview && isModuleAsset) || isGoogleFontsStylesheet
  } catch {
    return false
  }
}

function dedupe(values: string[]) {
  return [...new Set(values)]
}

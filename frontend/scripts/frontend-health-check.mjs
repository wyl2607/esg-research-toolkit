import { spawn } from 'node:child_process'
import fs from 'node:fs/promises'
import net from 'node:net'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

import AxeBuilder from '@axe-core/playwright'
import { chromium } from 'playwright'
import lighthouse from 'lighthouse'
import { launch } from 'chrome-launcher'

const __filename = fileURLToPath(import.meta.url)
const frontendDir = path.resolve(path.dirname(__filename), '..')
const repoRoot = path.resolve(frontendDir, '..')
const reportDir = path.join(frontendDir, 'health-reports', 'latest')
const reportJsonPath = path.join(reportDir, 'result.json')
const reportSummaryPath = path.join(reportDir, 'summary.md')
const logsDir = path.join(reportDir, 'logs')

const bundleBaselinePath = path.join(frontendDir, 'health', 'bundle-baseline.json')
const lighthouseBaselinePath = path.join(frontendDir, 'health', 'lighthouse-baseline.json')
const knownErrorsPath = path.join(frontendDir, 'health', 'known-errors.json')
const manifestPath = path.join(frontendDir, 'dist', '.vite', 'manifest.json')

const FRONTEND_PORT = process.env.ESG_FRONTEND_PORT || '4175'
const BACKEND_PORT = process.env.ESG_API_PORT || '8000'
const BACKEND_BASE_URL = process.env.ESG_API_BASE_URL || `http://127.0.0.1:${BACKEND_PORT}`
let APP_URL = process.env.ESG_FRONTEND_URL || `http://127.0.0.1:${FRONTEND_PORT}`
let API_URL = process.env.ESG_API_URL || `http://127.0.0.1:${BACKEND_PORT}/health`
const IS_CI = process.argv.includes('--ci') || process.env.CI === 'true'
const BROWSER_CHANNEL = process.env.ESG_PW_CHANNEL || 'chrome'
const SKIP_SERVER_BOOT = process.env.ESG_SKIP_SERVER_BOOT === '1'
const PYTHON_CMD =
  process.env.ESG_PYTHON_CMD ||
  (await fs
    .access(path.join(repoRoot, '.venv', 'bin', 'python'))
    .then(() => path.join(repoRoot, '.venv', 'bin', 'python'))
    .catch(() => 'python'))

const smokeRoutes = [
  { id: 'dashboard', path: '/', page: 'Dashboard' },
  { path: '/upload', page: 'Upload' },
  { path: '/companies', page: 'Companies' },
  { path: '/compare', page: 'Compare' },
  { path: '/taxonomy', page: 'Taxonomy' },
  { path: '/frameworks', page: 'Frameworks' },
]

const lighthouseRoutes = [
  { id: 'dashboard', path: '/', page: 'Dashboard' },
  { id: 'companies', path: '/companies', page: 'Companies' },
  { id: 'frameworks', path: '/frameworks', page: 'Frameworks' },
]

const perfBundleEntries = [
  { id: 'dashboard', page: 'Dashboard', manifestKey: 'src/pages/DashboardPage.tsx' },
  { id: 'company-profile', page: 'Company Profile', manifestKey: 'src/pages/CompanyProfilePage.tsx' },
]

const lighthouseThreshold = {
  performance: 0.6,
  accessibility: 0.9,
  'best-practices': 0.85,
  seo: 0.8,
}

const LIGHTHOUSE_REGRESSION_TOLERANCE = 0.15

function nowIso() {
  return new Date().toISOString()
}

async function ensureDirs() {
  await fs.mkdir(reportDir, { recursive: true })
  await fs.mkdir(logsDir, { recursive: true })
}

async function readJson(filePath, fallback) {
  try {
    const raw = await fs.readFile(filePath, 'utf8')
    return JSON.parse(raw)
  } catch {
    return fallback
  }
}

function runCommand(command, args, cwd, logFile) {
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      cwd,
      env: process.env,
      stdio: ['ignore', 'pipe', 'pipe'],
    })
    let output = ''
    child.stdout.on('data', (chunk) => {
      output += chunk.toString()
      process.stdout.write(chunk)
    })
    child.stderr.on('data', (chunk) => {
      output += chunk.toString()
      process.stderr.write(chunk)
    })
    child.on('close', async (code) => {
      await fs.writeFile(logFile, output, 'utf8')
      resolve({ ok: code === 0, code: code ?? 1, logFile })
    })
  })
}

async function pickAvailablePort(preferredPort) {
  const preferred = Number(preferredPort)
  if (!Number.isNaN(preferred) && preferred > 0) {
    const free = await new Promise((resolve) => {
      const server = net.createServer()
      server.once('error', () => resolve(false))
      server.listen(preferred, '127.0.0.1', () => {
        server.close(() => resolve(true))
      })
    })
    if (free) return String(preferred)
  }

  return await new Promise((resolve, reject) => {
    const server = net.createServer()
    server.once('error', reject)
    server.listen(0, '127.0.0.1', () => {
      const address = server.address()
      const dynamicPort =
        typeof address === 'object' && address && address.port ? String(address.port) : null
      server.close(() => {
        if (dynamicPort) resolve(dynamicPort)
        else reject(new Error('failed to allocate port'))
      })
    })
  })
}

function startServer(command, args, cwd, logFile) {
  const child = spawn(command, args, {
    cwd,
    env: process.env,
    detached: false,
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  child.stdout.on('data', (chunk) => {
    fs.appendFile(logFile, chunk.toString(), 'utf8').catch(() => undefined)
  })
  child.stderr.on('data', (chunk) => {
    fs.appendFile(logFile, chunk.toString(), 'utf8').catch(() => undefined)
  })
  return child
}

async function waitForUrl(url, timeoutMs = 60_000) {
  const start = Date.now()
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url)
      if (res.ok) return true
    } catch {
      // retry
    }
    await new Promise((r) => setTimeout(r, 1000))
  }
  return false
}

function normalizeConsoleMessage(text) {
  return text.replace(/\s+/g, ' ').trim()
}

function shouldIgnoreNetworkFailure(url, error) {
  if (error !== 'net::ERR_ABORTED') return false

  return (
    url.includes('fonts.googleapis.com') ||
    url.includes('/src/') ||
    url.includes('/node_modules/.vite/')
  )
}

function inferRiskLevel(issue) {
  const t = issue.type
  if (t === 'lint-failed' || t === 'build-failed' || t === 'server-start-failed') return 'high'
  if (t === 'new-console-error' || t === 'new-network-error') return 'high'
  if (t === 'axe-violation' || t === 'layout-regression') return 'high'
  if (t === 'bundle-regression' || t === 'route-bundle-regression' || t === 'lighthouse-threshold' || t === 'lighthouse-regression') return 'medium'
  return 'low'
}

function suggestFix(issue) {
  switch (issue.type) {
    case 'lint-failed':
      return '修复 ESLint 报错后重新运行 npm run lint。'
    case 'build-failed':
      return '修复 TypeScript/Vite 构建错误后重新运行 npm run build。'
    case 'new-console-error':
      return '检查对应页面组件与数据请求链路，优先处理未捕获异常与状态空值分支。'
    case 'new-network-error':
      return '检查 API 路径、后端可用性与 CORS/代理配置，必要时补充重试或降级提示。'
    case 'axe-violation':
      return '根据 axe 结果修复语义标签、颜色对比度、表单可访问性与 ARIA 标注。'
    case 'layout-regression':
      return '排查响应式样式与容器宽度约束，修复溢出/遮挡后回归关键页面。'
    case 'bundle-regression':
      return '定位新增大体积依赖，采用按需加载、代码分割或懒加载。'
    case 'route-bundle-regression':
      return '检查路由首屏是否重新引入图表或重量级模块，优先恢复延迟加载与更细粒度切分。'
    case 'lighthouse-threshold':
      return '优化首屏加载与可访问性指标，确保关键分类分数回到阈值以上。'
    case 'lighthouse-regression':
      return '对比基线分数下降页面，优先排查近期改动引入的渲染与资源负担。'
    default:
      return '根据日志定位问题并回归验证。'
  }
}

async function computeBundleStats() {
  const distAssets = path.join(frontendDir, 'dist', 'assets')
  const stats = {
    totalBytes: 0,
    jsBytes: 0,
    cssBytes: 0,
    files: [],
  }
  try {
    const files = await fs.readdir(distAssets)
    for (const file of files) {
      const fullPath = path.join(distAssets, file)
      const s = await fs.stat(fullPath)
      if (!s.isFile()) continue
      stats.totalBytes += s.size
      if (file.endsWith('.js')) stats.jsBytes += s.size
      if (file.endsWith('.css')) stats.cssBytes += s.size
      stats.files.push({ file, size: s.size })
    }
    stats.files.sort((a, b) => b.size - a.size)
  } catch {
    // ignored
  }
  return stats
}

async function statFileBytes(filePath) {
  try {
    const stat = await fs.stat(filePath)
    return stat.isFile() ? stat.size : 0
  } catch {
    return 0
  }
}

async function computeRouteBundleEvidence() {
  const manifest = await readJson(manifestPath, null)
  if (!manifest) return []

  const distDir = path.join(frontendDir, 'dist')
  const assetBytes = new Map()

  async function fileBytes(relativeFile) {
    if (!relativeFile) return 0
    if (assetBytes.has(relativeFile)) return assetBytes.get(relativeFile)
    const size = await statFileBytes(path.join(distDir, relativeFile))
    assetBytes.set(relativeFile, size)
    return size
  }

  function collectImportKeys(key, targetSet) {
    if (!key || targetSet.has(key)) return
    const chunk = manifest[key]
    if (!chunk) return
    targetSet.add(key)
    for (const importedKey of chunk.imports ?? []) {
      collectImportKeys(importedKey, targetSet)
    }
  }

  function collectDynamicKeys(key, targetSet) {
    const chunk = manifest[key]
    if (!chunk) return
    for (const dynamicKey of chunk.dynamicImports ?? []) {
      collectImportKeys(dynamicKey, targetSet)
      collectDynamicKeys(dynamicKey, targetSet)
    }
  }

  const routeEvidence = []
  for (const entry of perfBundleEntries) {
    const manifestEntry = manifest[entry.manifestKey]
    if (!manifestEntry) continue

    const initialKeys = new Set()
    collectImportKeys(entry.manifestKey, initialKeys)

    const asyncKeys = new Set()
    collectDynamicKeys(entry.manifestKey, asyncKeys)
    for (const key of initialKeys) {
      asyncKeys.delete(key)
    }

    let chunkBytes = 0
    let initialJsBytes = 0
    let asyncJsBytes = 0

    for (const key of initialKeys) {
      const chunk = manifest[key]
      if (!chunk?.file?.endsWith('.js')) continue
      const size = await fileBytes(chunk.file)
      initialJsBytes += size
      if (key === entry.manifestKey) {
        chunkBytes = size
      }
    }

    for (const key of asyncKeys) {
      const chunk = manifest[key]
      if (!chunk?.file?.endsWith('.js')) continue
      asyncJsBytes += await fileBytes(chunk.file)
    }

    routeEvidence.push({
      id: entry.id,
      page: entry.page,
      manifestKey: entry.manifestKey,
      chunkBytes,
      initialJsBytes,
      asyncJsBytes,
      asyncChunkCount: asyncKeys.size,
    })
  }

  return routeEvidence
}

function buildPerfSeedPayload() {
  const slug = `health-check-${Date.now()}`
  const companyName = `Health Check Analyst ${slug}`
  const reportYear = 2025
  return {
    slug,
    companyName,
    reportYear,
    payload: {
      company_name: companyName,
      report_year: reportYear,
      reporting_period_label: `FY ${reportYear}`,
      reporting_period_type: 'annual',
      source_document_type: 'manual_case',
      scope1_co2e_tonnes: 14250,
      scope2_co2e_tonnes: 6840,
      scope3_co2e_tonnes: 58200,
      energy_consumption_mwh: 194000,
      renewable_energy_pct: 47.5,
      water_usage_m3: 98000,
      waste_recycled_pct: 76.4,
      total_revenue_eur: 640000000,
      taxonomy_aligned_revenue_pct: 32.1,
      total_capex_eur: 215000000,
      taxonomy_aligned_capex_pct: 38.4,
      total_employees: 12800,
      female_pct: 41.2,
      primary_activities: ['battery manufacturing', 'grid storage'],
      source_url: `https://health-check.seed/${slug}`,
      evidence_summary: [],
    },
  }
}

async function seedCompanyProfileRoute() {
  const seed = buildPerfSeedPayload()
  const response = await fetch(`${BACKEND_BASE_URL}/report/manual`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(seed.payload),
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`failed to seed company profile route: HTTP ${response.status} ${detail}`)
  }

  return {
    id: 'company-profile',
    page: 'Company Profile',
    path: `/companies/${encodeURIComponent(seed.companyName)}`,
    pathTemplate: '/companies/:companyName',
    companyName: seed.companyName,
    reportYear: seed.reportYear,
  }
}

async function cleanupSeededCompany(seed) {
  if (!seed) return

  const response = await fetch(
    `${BACKEND_BASE_URL}/report/companies/${encodeURIComponent(seed.companyName)}/${seed.reportYear}?hard=true`,
    { method: 'DELETE' }
  )

  if (response.ok || response.status === 404) {
    return
  }

  const detail = await response.text()
  throw new Error(`failed to clean seeded company profile route: HTTP ${response.status} ${detail}`)
}

async function runBrowserChecks(knownErrors, routes) {
  const result = {
    pages: [],
    issues: [],
    lighthouse: [],
  }

  const browser = await chromium.launch({
    channel: BROWSER_CHANNEL,
    headless: true,
    args: IS_CI ? ['--no-sandbox'] : [],
  })
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })

  for (const route of routes.smoke) {
    const pageResult = {
      page: route.page,
      path: route.path,
      consoleErrors: [],
      networkErrors: [],
      axeViolations: [],
      layoutIssues: [],
    }
    const page = await context.newPage()

    page.on('console', (msg) => {
      if (msg.type() !== 'error') return
      const text = normalizeConsoleMessage(msg.text())
      const signature = `${route.path}|${text}`
      pageResult.consoleErrors.push({ text, signature })
      if (!knownErrors.console.includes(signature)) {
        result.issues.push({
          type: 'new-console-error',
          page: route.page,
          route: route.path,
          repro: `打开 ${route.path}，观察浏览器 console 输出。`,
          detail: text,
        })
      }
    })

    page.on('requestfailed', (request) => {
      const error = request.failure()?.errorText || 'request failed'
      if (shouldIgnoreNetworkFailure(request.url(), error)) return
      const signature = `${route.path}|${request.method()} ${request.url()}|${error}`
      pageResult.networkErrors.push({ url: request.url(), method: request.method(), error, signature })
      if (!knownErrors.network.includes(signature)) {
        result.issues.push({
          type: 'new-network-error',
          page: route.page,
          route: route.path,
          repro: `打开 ${route.path}，在 Network 面板筛选 failed 请求。`,
          detail: `${request.method()} ${request.url()} -> ${error}`,
        })
      }
    })

    page.on('response', (response) => {
      if (response.status() < 500) return
      const url = response.url()
      const signature = `${route.path}|${response.request().method()} ${url}|HTTP ${response.status()}`
      pageResult.networkErrors.push({
        url,
        method: response.request().method(),
        error: `HTTP ${response.status()}`,
        signature,
      })
      if (!knownErrors.network.includes(signature)) {
        result.issues.push({
          type: 'new-network-error',
          page: route.page,
          route: route.path,
          repro: `打开 ${route.path}，观察 Network 中 5xx 响应。`,
          detail: `${response.request().method()} ${url} -> HTTP ${response.status()}`,
        })
      }
    })

    await page.goto(`${APP_URL}${route.path}`, { waitUntil: 'networkidle' })
    await page.waitForTimeout(500)

    const axe = await new AxeBuilder({ page }).analyze()
    const seriousViolations = axe.violations.filter((v) =>
      ['critical', 'serious'].includes((v.impact || '').toLowerCase())
    )
    pageResult.axeViolations = seriousViolations.map((v) => ({
      id: v.id,
      impact: v.impact,
      nodes: v.nodes.length,
      help: v.help,
    }))
    if (seriousViolations.length > 0) {
      result.issues.push({
        type: 'axe-violation',
        page: route.page,
        route: route.path,
        repro: `打开 ${route.path}，运行 axe 扫描。`,
        detail: seriousViolations.map((v) => `${v.id} (${v.impact})`).join('; '),
      })
    }

    const layout = await page.evaluate(() => {
      const issues = []
      if (document.documentElement.scrollWidth > document.documentElement.clientWidth + 4) {
        issues.push('页面存在明显横向溢出')
      }
      const offscreen = Array.from(document.querySelectorAll('body *')).filter((el) => {
        const r = el.getBoundingClientRect()
        return r.width > 0 && (r.left < -2 || r.right > window.innerWidth + 2)
      })
      if (offscreen.length >= 3) {
        issues.push(`检测到 ${offscreen.length} 个可能越界元素`)
      }
      return issues
    })
    pageResult.layoutIssues = layout
    if (layout.length > 0) {
      result.issues.push({
        type: 'layout-regression',
        page: route.page,
        route: route.path,
        repro: `打开 ${route.path}，检查首屏布局与横向滚动。`,
        detail: layout.join('；'),
      })
    }

    result.pages.push(pageResult)
    await page.close()
  }

  await context.close()
  await browser.close()

  const chrome = await launch({ chromeFlags: ['--headless=new', '--no-sandbox'] })
  try {
    for (const route of routes.lighthouse) {
      const url = `${APP_URL}${route.path}`
      const runnerResult = await lighthouse(url, {
        port: chrome.port,
        output: 'json',
        logLevel: 'error',
        onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo'],
      })
      const categories = runnerResult?.lhr?.categories ?? {}
      const audits = runnerResult?.lhr?.audits ?? {}
      const metrics = {
        id: route.id ?? route.path,
        page: route.page,
        path: route.path,
        pathTemplate: route.pathTemplate ?? route.path,
        performance: categories.performance?.score ?? null,
        accessibility: categories.accessibility?.score ?? null,
        'best-practices': categories['best-practices']?.score ?? null,
        seo: categories.seo?.score ?? null,
        timings: {
          firstContentfulPaintMs: audits['first-contentful-paint']?.numericValue ?? null,
          largestContentfulPaintMs: audits['largest-contentful-paint']?.numericValue ?? null,
          totalBlockingTimeMs: audits['total-blocking-time']?.numericValue ?? null,
          speedIndexMs: audits['speed-index']?.numericValue ?? null,
          cumulativeLayoutShift: audits['cumulative-layout-shift']?.numericValue ?? null,
        },
      }
      result.lighthouse.push(metrics)
    }
  } finally {
    await chrome.kill()
  }

  return result
}

function formatPct(value) {
  if (value == null || Number.isNaN(value)) return 'n/a'
  return `${Math.round(value * 100)}%`
}

function formatMs(value) {
  if (value == null || Number.isNaN(value)) return 'n/a'
  return `${Math.round(value)}ms`
}

function formatCls(value) {
  if (value == null || Number.isNaN(value)) return 'n/a'
  return value.toFixed(3)
}

function formatBytes(value) {
  if (value == null || Number.isNaN(value)) return 'n/a'
  return `${value}B`
}

async function main() {
  await ensureDirs()

  const runtimeFrontendPort = process.env.ESG_FRONTEND_URL
    ? null
    : await pickAvailablePort(FRONTEND_PORT)
  if (runtimeFrontendPort) {
    APP_URL = `http://127.0.0.1:${runtimeFrontendPort}`
  }
  if (!process.env.ESG_API_URL) {
    API_URL = `http://127.0.0.1:${BACKEND_PORT}/health`
  }

  const knownErrors = await readJson(knownErrorsPath, { console: [], network: [] })
  const bundleBaseline = await readJson(bundleBaselinePath, {
    totalBytes: 0,
    jsBytes: 0,
    cssBytes: 0,
    routes: {},
  })
  const lighthouseBaseline = await readJson(lighthouseBaselinePath, {})

  const result = {
    generatedAt: nowIso(),
    ci: IS_CI,
    appUrl: APP_URL,
    checks: {
      lint: { ok: false, logFile: path.join(logsDir, 'lint.log') },
      build: { ok: false, logFile: path.join(logsDir, 'build.log') },
      smoke: { ok: false, logFile: path.join(logsDir, 'smoke.log') },
      bundle: { ok: false },
    },
    bundle: {
      baseline: bundleBaseline,
      current: null,
      regression: null,
      routeEvidence: [],
    },
    browser: null,
    issues: [],
  }

  result.checks.lint = await runCommand('npm', ['run', 'lint'], frontendDir, result.checks.lint.logFile)
  if (!result.checks.lint.ok) {
    result.issues.push({
      type: 'lint-failed',
      page: 'N/A',
      route: 'N/A',
      repro: '在 frontend 目录执行 npm run lint。',
      detail: `lint 失败，退出码 ${result.checks.lint.code}。`,
    })
  }

  result.checks.build = await runCommand('npm', ['run', 'build'], frontendDir, result.checks.build.logFile)
  if (!result.checks.build.ok) {
    result.issues.push({
      type: 'build-failed',
      page: 'N/A',
      route: 'N/A',
      repro: '在 frontend 目录执行 npm run build。',
      detail: `build 失败，退出码 ${result.checks.build.code}。`,
    })
  }

  result.bundle.current = await computeBundleStats()
  result.bundle.routeEvidence = await computeRouteBundleEvidence()
  result.checks.bundle.ok = result.bundle.current.totalBytes > 0

  if (result.bundle.current.totalBytes > 0 && bundleBaseline.totalBytes > 0) {
    const growth = (result.bundle.current.totalBytes - bundleBaseline.totalBytes) / bundleBaseline.totalBytes
    if (growth > 0.05) {
      result.bundle.regression = {
        growthRatio: growth,
        baselineBytes: bundleBaseline.totalBytes,
        currentBytes: result.bundle.current.totalBytes,
      }
      result.issues.push({
        type: 'bundle-regression',
        page: 'N/A',
        route: 'dist/assets',
        repro: '执行 npm run build 后对比 dist/assets 总体积与基线。',
        detail: `包体积从 ${bundleBaseline.totalBytes}B 增长到 ${result.bundle.current.totalBytes}B（+${(growth * 100).toFixed(1)}%）。`,
      })
    }
  }

  for (const route of result.bundle.routeEvidence) {
    const baselineRoute = bundleBaseline.routes?.[route.id]
    if (!baselineRoute?.initialJsBytes) continue

    const growth =
      (route.initialJsBytes - baselineRoute.initialJsBytes) / baselineRoute.initialJsBytes
    if (growth > 0.1) {
      result.issues.push({
        type: 'route-bundle-regression',
        page: route.page,
        route: route.id,
        repro: `执行 npm run build 后检查 ${route.page} 路由首屏 JS 负载。`,
        detail: `${route.page} 首屏 JS 从 ${baselineRoute.initialJsBytes}B 增长到 ${route.initialJsBytes}B（+${(growth * 100).toFixed(1)}%）。`,
      })
    }
  }

  const backendLog = path.join(logsDir, 'backend.log')
  const frontendLog = path.join(logsDir, 'frontend-preview.log')
  const backend = SKIP_SERVER_BOOT
    ? null
    : startServer(
        PYTHON_CMD,
        ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', BACKEND_PORT],
        repoRoot,
        backendLog
      )
  const frontend = SKIP_SERVER_BOOT
    ? null
    : startServer(
        'npm',
        [
          'run',
          'preview',
          '--',
          '--host',
          '127.0.0.1',
          '--port',
          runtimeFrontendPort || FRONTEND_PORT,
          '--strictPort',
        ],
        frontendDir,
        frontendLog
      )
  let seededCompanyRoute = null

  try {
    const backendReady = await waitForUrl(API_URL, 60_000)
    const frontendReady = await waitForUrl(APP_URL, 60_000)

    if (!backendReady || !frontendReady) {
      result.issues.push({
        type: 'server-start-failed',
        page: 'N/A',
        route: 'N/A',
        repro: '启动后端/前端服务并访问健康检查 URL。',
        detail: `服务未在超时内就绪（backend: ${backendReady}, frontend: ${frontendReady}）。`,
      })
      result.checks.smoke = { ok: false, code: 1, logFile: path.join(logsDir, 'smoke.log') }
    } else {
      seededCompanyRoute = await seedCompanyProfileRoute()
      const runtimeRoutes = {
        smoke: [...smokeRoutes, seededCompanyRoute],
        lighthouse: [...lighthouseRoutes, seededCompanyRoute],
      }

      result.browser = await runBrowserChecks(knownErrors, runtimeRoutes)
      result.issues.push(...result.browser.issues)
      await fs.writeFile(result.checks.smoke.logFile, JSON.stringify(result.browser, null, 2), 'utf8')
      result.checks.smoke = { ok: result.browser.issues.length === 0, code: result.browser.issues.length === 0 ? 0 : 1, logFile: result.checks.smoke.logFile }

      for (const metric of result.browser.lighthouse) {
        const baseline = lighthouseBaseline[metric.id] ?? lighthouseBaseline[metric.path] ?? {}
        for (const [key, threshold] of Object.entries(lighthouseThreshold)) {
          const value = metric[key]
          if (typeof value !== 'number') continue
          if (value < threshold) {
            result.issues.push({
              type: 'lighthouse-threshold',
              page: metric.page,
              route: metric.path,
              repro: `运行 Lighthouse 审核 ${metric.path}。`,
              detail: `${key}=${formatPct(value)} 低于阈值 ${formatPct(threshold)}。`,
            })
          }
          const baseValue = baseline[key]
          if (
            typeof baseValue === 'number' &&
            baseValue - value > LIGHTHOUSE_REGRESSION_TOLERANCE
          ) {
            result.issues.push({
              type: 'lighthouse-regression',
              page: metric.page,
              route: metric.path,
              repro: `对比 Lighthouse 基线（${metric.path}）。`,
              detail: `${key} 从 ${formatPct(baseValue)} 降到 ${formatPct(value)}（-${Math.round((baseValue - value) * 100)}pt）。`,
            })
          }
        }
      }
    }
  } finally {
    await cleanupSeededCompany(seededCompanyRoute).catch(async (error) => {
      const cleanupMessage = error instanceof Error ? error.message : String(error)
      result.issues.push({
        type: 'new-network-error',
        page: 'Company Profile',
        route: seededCompanyRoute?.path ?? '/companies/:companyName',
        repro: '清理 health-check 临时种子公司数据。',
        detail: cleanupMessage,
      })
    })
    frontend?.kill('SIGTERM')
    backend?.kill('SIGTERM')
  }

  const uniqueIssues = []
  const seen = new Set()
  for (const issue of result.issues) {
    const key = `${issue.type}|${issue.page}|${issue.route}|${issue.detail}`
    if (!seen.has(key)) {
      seen.add(key)
      uniqueIssues.push(issue)
    }
  }
  result.issues = uniqueIssues

  const summaryLines = []
  summaryLines.push(`# Frontend Health Check Summary`)
  summaryLines.push(`- Generated: ${result.generatedAt}`)
  summaryLines.push(`- Lint: ${result.checks.lint.ok ? '✅' : '❌'}`)
  summaryLines.push(`- Build: ${result.checks.build.ok ? '✅' : '❌'}`)
  summaryLines.push(`- Playwright/Axe/Lighthouse: ${result.checks.smoke.ok ? '✅' : '❌'}`)
  if (result.bundle.current) {
    summaryLines.push(`- Bundle: ${result.bundle.current.totalBytes}B (baseline: ${bundleBaseline.totalBytes || 'n/a'}B)`)
  }
  if (result.bundle.routeEvidence.length > 0) {
    summaryLines.push(`- Analyst route bundle evidence: ${result.bundle.routeEvidence.length} routes`)
  }

  if (result.bundle.routeEvidence.length > 0) {
    summaryLines.push('')
    summaryLines.push('## Analyst route JS evidence')
    summaryLines.push('| Route | Route chunk | Initial JS | Deferred JS | Async chunks |')
    summaryLines.push('|---|---:|---:|---:|---:|')
    for (const route of result.bundle.routeEvidence) {
      summaryLines.push(
        `| ${route.page} | ${formatBytes(route.chunkBytes)} | ${formatBytes(route.initialJsBytes)} | ${formatBytes(route.asyncJsBytes)} | ${route.asyncChunkCount} |`
      )
    }
  }

  if (result.browser?.lighthouse?.length) {
    summaryLines.push('')
    summaryLines.push('## Lighthouse analyst route evidence')
    summaryLines.push('| Route | Perf | A11y | Best | SEO | FCP | LCP | TBT | CLS |')
    summaryLines.push('|---|---:|---:|---:|---:|---:|---:|---:|---:|')
    for (const metric of result.browser.lighthouse) {
      summaryLines.push(
        `| ${metric.page} | ${formatPct(metric.performance)} | ${formatPct(metric.accessibility)} | ${formatPct(metric['best-practices'])} | ${formatPct(metric.seo)} | ${formatMs(metric.timings.firstContentfulPaintMs)} | ${formatMs(metric.timings.largestContentfulPaintMs)} | ${formatMs(metric.timings.totalBlockingTimeMs)} | ${formatCls(metric.timings.cumulativeLayoutShift)} |`
      )
    }
  }

  if (result.issues.length === 0) {
    summaryLines.push('')
    summaryLines.push('✅ 未发现失败、关键路由包体积回退、明显布局问题或新的 console/network error。')
  } else {
    summaryLines.push('')
    summaryLines.push('## Issues')
    summaryLines.push('| 页面 | 复现步骤 | 风险级别 | 建议修复点 | 详情 |')
    summaryLines.push('|---|---|---|---|---|')
    for (const issue of result.issues) {
      summaryLines.push(
        `| ${issue.page} (${issue.route}) | ${issue.repro} | ${inferRiskLevel(issue)} | ${suggestFix(issue)} | ${issue.detail} |`
      )
    }
  }

  await fs.writeFile(reportJsonPath, JSON.stringify(result, null, 2), 'utf8')
  await fs.writeFile(reportSummaryPath, summaryLines.join('\n') + '\n', 'utf8')

  process.stdout.write(`\n[health-check] report: ${reportSummaryPath}\n`)
  process.exit(result.issues.length > 0 ? 1 : 0)
}

main().catch(async (error) => {
  await ensureDirs()
  const fallback = `# Frontend Health Check Summary\n\n❌ 健康检查脚本异常：${error instanceof Error ? error.stack : String(error)}\n`
  await fs.writeFile(reportSummaryPath, fallback, 'utf8')
  process.stderr.write(`${error instanceof Error ? error.stack : String(error)}\n`)
  process.exit(1)
})

import { spawn } from 'node:child_process'
import fs from 'node:fs/promises'
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

const APP_URL = process.env.ESG_FRONTEND_URL || 'http://127.0.0.1:4173'
const API_URL = process.env.ESG_API_URL || 'http://127.0.0.1:8000/health'
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
  { path: '/', page: 'Dashboard' },
  { path: '/upload', page: 'Upload' },
  { path: '/companies', page: 'Companies' },
  { path: '/compare', page: 'Compare' },
  { path: '/taxonomy', page: 'Taxonomy' },
  { path: '/frameworks', page: 'Frameworks' },
]

const lighthouseRoutes = [
  { path: '/', page: 'Dashboard' },
  { path: '/companies', page: 'Companies' },
  { path: '/frameworks', page: 'Frameworks' },
]

const lighthouseThreshold = {
  performance: 0.6,
  accessibility: 0.9,
  'best-practices': 0.85,
  seo: 0.8,
}

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
  if (t === 'bundle-regression' || t === 'lighthouse-threshold' || t === 'lighthouse-regression') return 'medium'
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

async function runBrowserChecks(knownErrors) {
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

  for (const route of smokeRoutes) {
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
    for (const route of lighthouseRoutes) {
      const url = `${APP_URL}${route.path}`
      const runnerResult = await lighthouse(url, {
        port: chrome.port,
        output: 'json',
        logLevel: 'error',
        onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo'],
      })
      const categories = runnerResult?.lhr?.categories ?? {}
      const metrics = {
        page: route.page,
        path: route.path,
        performance: categories.performance?.score ?? null,
        accessibility: categories.accessibility?.score ?? null,
        'best-practices': categories['best-practices']?.score ?? null,
        seo: categories.seo?.score ?? null,
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

async function main() {
  await ensureDirs()

  const knownErrors = await readJson(knownErrorsPath, { console: [], network: [] })
  const bundleBaseline = await readJson(bundleBaselinePath, { totalBytes: 0, jsBytes: 0, cssBytes: 0 })
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

  const backendLog = path.join(logsDir, 'backend.log')
  const frontendLog = path.join(logsDir, 'frontend-dev.log')
  const backend = SKIP_SERVER_BOOT
    ? null
    : startServer(
        PYTHON_CMD,
        ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000'],
        repoRoot,
        backendLog
      )
  const frontend = SKIP_SERVER_BOOT
    ? null
    : startServer(
        'npm',
        ['run', 'dev', '--', '--host', '127.0.0.1', '--port', '4173'],
        frontendDir,
        frontendLog
      )

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
      result.browser = await runBrowserChecks(knownErrors)
      result.issues.push(...result.browser.issues)
      await fs.writeFile(result.checks.smoke.logFile, JSON.stringify(result.browser, null, 2), 'utf8')
      result.checks.smoke = { ok: result.browser.issues.length === 0, code: result.browser.issues.length === 0 ? 0 : 1, logFile: result.checks.smoke.logFile }

      for (const metric of result.browser.lighthouse) {
        const baseline = lighthouseBaseline[metric.path] ?? {}
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
          if (typeof baseValue === 'number' && baseValue - value > 0.05) {
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

  if (result.issues.length === 0) {
    summaryLines.push('')
    summaryLines.push('✅ 未发现失败、包体积回退、明显布局问题或新的 console/network error。')
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

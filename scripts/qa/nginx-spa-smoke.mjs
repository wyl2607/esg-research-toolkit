#!/usr/bin/env node

const baseUrl = (process.env.ESG_FRONTEND_URL || process.argv[2] || '').replace(/\/$/, '')

if (!baseUrl) {
  console.error('Usage: ESG_FRONTEND_URL=https://example.test node scripts/qa/nginx-spa-smoke.mjs')
  process.exit(2)
}

async function fetchPath(pathname) {
  return fetch(`${baseUrl}${pathname}`, { redirect: 'manual' })
}

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function checkSecurityHeaders(response, pathname) {
  for (const [header, expected] of Object.entries({
    'x-frame-options': 'SAMEORIGIN',
    'x-content-type-options': 'nosniff',
    'referrer-policy': 'strict-origin-when-cross-origin',
    'strict-transport-security': 'max-age=31536000',
    'reporting-endpoints': 'csp-endpoint="/api/csp-report"',
    'permissions-policy': 'camera=(), microphone=(), geolocation=()',
    'content-security-policy-report-only': "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'self'; img-src 'self' data: blob: https:; font-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self' https:; worker-src 'self' blob:; report-uri /api/csp-report; report-to csp-endpoint;",
  })) {
    assert(response.headers.get(header) === expected, `${pathname}: ${header} expected ${expected}`)
  }
}

try {
  const root = await fetchPath('/')
  assert(root.status === 200, `root expected 200, got ${root.status}`)
  const rootContentType = root.headers.get('content-type') || ''
  const rootCache = root.headers.get('cache-control') || ''
  assert(/text\/html/i.test(rootContentType) && /charset=utf-8/i.test(rootContentType), 'root must be HTML UTF-8')
  assert(/no-cache/i.test(rootCache), 'index HTML must be no-cache')

  checkSecurityHeaders(root, '/')
  const indexHtml = await root.clone().text()
  const knownPaths = [
    '/upload', '/disclosures', '/taxonomy', '/lcoe', '/saf', '/companies',
    '/companies/SAP%20SE', '/manual', '/compare', '/benchmarks', '/frameworks',
    '/regional', '/coverage/scope1', '/frameworks/regional',
  ]
  for (const pathname of knownPaths) {
    const response = await fetchPath(pathname)
    assert(response.status === 200, `${pathname} expected 200, got ${response.status}`)
    assert(await response.text() === indexHtml, `${pathname} must serve the SPA shell`)
    assert(/no-cache/i.test(response.headers.get('cache-control') || ''), `${pathname} HTML must be no-cache`)
    checkSecurityHeaders(response, pathname)
  }

  const cspReport = await fetch(`${baseUrl}/api/csp-report`, {
    method: 'POST',
    headers: { 'content-type': 'application/csp-report' },
    body: JSON.stringify({ 'csp-report': { 'violated-directive': 'script-src', 'blocked-uri': 'inline' } }),
    redirect: 'manual',
  })
  assert(cspReport.status === 204, `CSP report expected 204, got ${cspReport.status}`)
  assert(await cspReport.text() === '', 'CSP report response must be empty')
  checkSecurityHeaders(cspReport, '/api/csp-report')

  const unknownRoute = await fetchPath('/__nginx_spa_contract_missing__')
  assert(unknownRoute.status === 404, `unknown route expected 404, got ${unknownRoute.status}`)
  const unknownContentType = unknownRoute.headers.get('content-type') || ''
  assert(/text\/html/i.test(unknownContentType), 'unknown route must render the SPA 404 page')

  const missingAsset = await fetchPath('/assets/__codex_missing__.js')
  assert(missingAsset.status === 404, `missing asset expected 404, got ${missingAsset.status}`)

  const deniedPaths = [
    '/.env', '/.git/config', '/companies/.env', '/assets/.hidden/file.js',
    '/index.php', '/dump.sql', '/backup.bak', '/source.env', '/source.git',
    '/settings.ini', '/debug.log', '/index.old', '/file.swp',
    '/assets/__codex_missing__', '/assets/__codex_missing__.unknown',
  ]
  for (const pathname of deniedPaths) {
    const response = await fetchPath(pathname)
    assert(response.status === 404, `${pathname} expected 404, got ${response.status}`)
    assert(await response.text() !== indexHtml, `${pathname} must not serve the SPA shell`)
    assert(!/immutable/i.test(response.headers.get('cache-control') || ''), `${pathname} errors must not be immutable`)
    checkSecurityHeaders(response, pathname)
  }
  checkSecurityHeaders(unknownRoute, '/__nginx_spa_contract_missing__')
  checkSecurityHeaders(missingAsset, '/assets/__codex_missing__.js')
  assert(!/immutable/i.test(missingAsset.headers.get('cache-control') || ''), 'missing JS must not be immutable')

  const assetMatch = indexHtml.match(/(?:src|href)=["'](\/assets\/[^"']+)["']/i)
  assert(assetMatch, 'root HTML must reference a built asset')
  const asset = await fetchPath(assetMatch[1])
  assert(asset.status === 200, `hashed asset expected 200, got ${asset.status}`)
  checkSecurityHeaders(asset, assetMatch[1])
  assert(/immutable/i.test(asset.headers.get('cache-control') || ''), 'hashed asset must be immutable')

  console.log(JSON.stringify({
    baseUrl,
    root: root.status,
    cspReport: cspReport.status,
    knownRoutesChecked: knownPaths.length,
    deniedPathsChecked: deniedPaths.length,
    unknownRoute: unknownRoute.status,
    missingAsset: missingAsset.status,
    hashedAsset: asset.status,
  }))
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error))
  process.exit(1)
}

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

try {
  const root = await fetchPath('/')
  assert(root.status === 200, `root expected 200, got ${root.status}`)
  const rootContentType = root.headers.get('content-type') || ''
  const rootCache = root.headers.get('cache-control') || ''
  assert(/text\/html/i.test(rootContentType) && /charset=utf-8/i.test(rootContentType), 'root must be HTML UTF-8')
  assert(/no-cache/i.test(rootCache), 'index HTML must be no-cache')

  const knownRoute = await fetchPath('/companies')
  assert(knownRoute.status === 200, `known route expected 200, got ${knownRoute.status}`)
  const knownContentType = knownRoute.headers.get('content-type') || ''
  assert(/text\/html/i.test(knownContentType) && /charset=utf-8/i.test(knownContentType), 'known route must be HTML UTF-8')
  assert(/no-cache/i.test(knownRoute.headers.get('cache-control') || ''), 'known route HTML must be no-cache')

  const missingAsset = await fetchPath('/assets/__codex_missing__.js')
  assert(missingAsset.status === 404, `missing asset expected 404, got ${missingAsset.status}`)

  const indexHtml = await root.clone().text()
  const assetMatch = indexHtml.match(/(?:src|href)=["'](\/assets\/[^"']+)["']/i)
  assert(assetMatch, 'root HTML must reference a built asset')
  const asset = await fetchPath(assetMatch[1])
  assert(asset.status === 200, `hashed asset expected 200, got ${asset.status}`)
  assert(/immutable/i.test(asset.headers.get('cache-control') || ''), 'hashed asset must be immutable')

  console.log(JSON.stringify({
    baseUrl,
    root: root.status,
    knownRoute: knownRoute.status,
    missingAsset: missingAsset.status,
    hashedAsset: asset.status,
  }))
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error))
  process.exit(1)
}

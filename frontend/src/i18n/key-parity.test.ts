import { describe, expect, it } from 'vitest'
import de from './locales/de.json'
import en from './locales/en.json'
import zh from './locales/zh.json'

// Only English is bundled at init; de/zh load lazily with en as the sole
// fallback. Any key missing from one locale therefore leaks either a raw
// key or English text into the UI (see upstream #43/#67/#68). This test
// pins full key parity across all three locales.

function flattenKeys(obj: Record<string, unknown>, prefix = ''): string[] {
  return Object.entries(obj).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key
    if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
      return flattenKeys(value as Record<string, unknown>, path)
    }
    return [path]
  })
}

const locales = { en, de, zh } as const

describe('i18n locale key parity', () => {
  const enKeys = new Set(flattenKeys(en))

  it('has a non-trivial English key set', () => {
    expect(enKeys.size).toBeGreaterThan(500)
  })

  for (const [name, bundle] of Object.entries(locales)) {
    if (name === 'en') continue

    it(`${name} has exactly the same keys as en`, () => {
      const keys = new Set(flattenKeys(bundle))
      const missing = [...enKeys].filter((k) => !keys.has(k)).sort()
      const extra = [...keys].filter((k) => !enKeys.has(k)).sort()
      expect({ missing, extra }).toEqual({ missing: [], extra: [] })
    })
  }
})

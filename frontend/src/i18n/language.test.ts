import { createInstance } from 'i18next'
import { describe, expect, it, vi } from 'vitest'

import { BUNDLED_LANGUAGE, activateLanguage, resolveLanguage } from './language'

describe('resolveLanguage', () => {
  it('prefers the query parameter so a page is linkable per language', () => {
    expect(resolveLanguage({ query: 'zh', stored: 'de', navigator: 'en-GB' })).toBe('zh')
  })

  it('falls back to the stored choice, then the browser preference', () => {
    expect(resolveLanguage({ query: null, stored: 'de', navigator: 'en-GB' })).toBe('de')
    expect(resolveLanguage({ query: null, stored: null, navigator: 'de-AT' })).toBe('de')
  })

  it('skips an unsupported value at each step instead of giving up on the rest', () => {
    // A stale `?lang=fr` must not override a valid stored German choice.
    expect(resolveLanguage({ query: 'fr', stored: 'de', navigator: 'en-GB' })).toBe('de')
    expect(resolveLanguage({ query: null, stored: 'fr', navigator: 'zh-CN' })).toBe('zh')
  })

  it('lands on the bundled locale when nothing is usable', () => {
    expect(resolveLanguage({})).toBe(BUNDLED_LANGUAGE)
    expect(resolveLanguage({ query: 'fr', stored: 'ru', navigator: 'ja-JP' })).toBe(
      BUNDLED_LANGUAGE
    )
  })
})

async function bundledOnlyInstance(lng: string) {
  const instance = createInstance()
  await instance.init({
    resources: { en: { translation: { greeting: 'Hello' } } },
    lng,
    fallbackLng: 'en',
  })
  return instance
}

describe('activateLanguage', () => {
  it('loads the bundle before setting the language', async () => {
    const instance = await bundledOnlyInstance('en')
    const order: string[] = []
    const loadBundle = vi.fn(async (lang: string) => {
      order.push(`load:${lang}`)
      instance.addResourceBundle(lang, 'translation', { greeting: 'Hallo' })
    })
    instance.on('languageChanged', (lang) => order.push(`changed:${lang}`))

    await activateLanguage(instance, 'de', loadBundle)

    expect(order).toEqual(['load:de', 'changed:de'])
    expect(instance.t('greeting')).toBe('Hallo')
  })

  it('leaves resolvedLanguage pointing at the language it activated', async () => {
    // This is the invariant that actually matters. `resolvedLanguage` is what
    // every number/date formatter reads to choose a locale, and i18next fixes it
    // at the moment the language is set. Setting the language before its bundle
    // exists latches it on the fallback permanently: the UI then renders German
    // text while formatting its numbers as en-US.
    const instance = await bundledOnlyInstance('en')

    await activateLanguage(instance, 'de', async (lang) => {
      instance.addResourceBundle(lang, 'translation', { greeting: 'Hallo' })
    })

    expect(instance.language).toBe('de')
    expect(instance.resolvedLanguage).toBe('de')
    expect(instance.t('greeting')).toBe('Hallo')
  })

  it('recovers resolvedLanguage even when the language was already set too early', async () => {
    // Reproduces the broken starting state directly: language already `de`,
    // bundle absent, so resolvedLanguage was resolved against the fallback.
    const instance = await bundledOnlyInstance('de')
    expect(instance.resolvedLanguage).toBe('en')

    await activateLanguage(instance, 'de', async (lang) => {
      instance.addResourceBundle(lang, 'translation', { greeting: 'Hallo' })
    })

    expect(instance.resolvedLanguage).toBe('de')
  })

  it('propagates a failed bundle load instead of switching to a language it cannot render', async () => {
    const instance = await bundledOnlyInstance('en')
    const seen: string[] = []
    instance.on('languageChanged', (lang) => seen.push(lang))

    await expect(
      activateLanguage(instance, 'de', async () => {
        throw new Error('chunk load failed')
      })
    ).rejects.toThrow('chunk load failed')

    expect(seen).toEqual([])
    expect(instance.language).toBe('en')
    expect(instance.t('greeting')).toBe('Hello')
  })
})

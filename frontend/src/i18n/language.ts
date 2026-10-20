import type { i18n as I18n } from 'i18next'

export const SUPPORTED_LANGUAGES = ['de', 'en', 'zh'] as const
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number]

/** The one locale bundled at init; every other locale is fetched on demand. */
export const BUNDLED_LANGUAGE: SupportedLanguage = 'en'

export const LANGUAGE_STORAGE_KEY = 'i18nextLng'

export function isSupportedLanguage(value: string | null | undefined): value is SupportedLanguage {
  return !!value && (SUPPORTED_LANGUAGES as readonly string[]).includes(value)
}

export interface LanguageSources {
  /** `?lang=` on the current URL. Wins, so every page is linkable per language. */
  query?: string | null
  /** Previously chosen language, from storage. */
  stored?: string | null
  /** Browser preference, e.g. `de-AT`. */
  navigator?: string | null
}

/**
 * Pick the language to start in, in priority order, skipping anything
 * unsupported at each step rather than falling straight through to English.
 *
 * Takes its inputs as arguments instead of reading `window`, so the precedence
 * rules are testable without a DOM.
 */
export function resolveLanguage(sources: LanguageSources): SupportedLanguage {
  const { query, stored, navigator } = sources
  if (isSupportedLanguage(query)) return query
  if (isSupportedLanguage(stored)) return stored
  const base = navigator?.split('-')[0]
  if (isSupportedLanguage(base)) return base
  return BUNDLED_LANGUAGE
}

/**
 * Load a locale bundle, then switch to it.
 *
 * Order matters, and not only for the text. i18next computes
 * `resolvedLanguage` — the language it could actually resolve resources for —
 * when the language is set. Set the language *before* its bundle exists and
 * `resolvedLanguage` latches onto the fallback and never recovers, even once
 * the bundle arrives and `t()` starts returning translated strings.
 *
 * That was the app's state in production: `language` was `de`, text rendered in
 * German, and `resolvedLanguage` stayed `en`. Since `resolvedLanguage` is what
 * every formatter uses to pick a locale, a German page silently formatted its
 * numbers as `970,000` and `29.5%`, and `<html lang>` claimed English.
 *
 * So the bundle is always loaded first, and the language is only ever set once
 * its resources are in place.
 */
export async function activateLanguage(
  instance: I18n,
  lang: string,
  loadBundle: (lang: string) => Promise<void>
): Promise<void> {
  await loadBundle(lang)
  await instance.changeLanguage(lang)
}

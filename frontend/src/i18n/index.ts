import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import {
  BUNDLED_LANGUAGE,
  LANGUAGE_STORAGE_KEY,
  SUPPORTED_LANGUAGES,
  activateLanguage,
  resolveLanguage,
} from './language'

// PERF: only bundle the default (English) locale in the critical path.
// German and Chinese are lazy-loaded on demand via loadLocale().
import en from './locales/en.json'

function readStoredLanguage(): string | null {
  try {
    return window.localStorage.getItem(LANGUAGE_STORAGE_KEY)
  } catch {
    // Private mode / storage disabled.
    return null
  }
}

function initialLanguage(): string {
  if (typeof window === 'undefined') return BUNDLED_LANGUAGE
  return resolveLanguage({
    query: new URLSearchParams(window.location.search).get('lang'),
    stored: readStoredLanguage(),
    navigator: window.navigator.language,
  })
}

// Start on the bundled locale. Settling on a lazily loaded language here would
// mean the first render resolves against a bundle that has not arrived yet.
i18n.use(initReactI18next).init({
  resources: { en: { translation: en } },
  lng: BUNDLED_LANGUAGE,
  fallbackLng: BUNDLED_LANGUAGE,
  supportedLngs: [...SUPPORTED_LANGUAGES],
  load: 'languageOnly',
  nonExplicitSupportedLngs: true,
  interpolation: { escapeValue: false },
})

// PERF: dynamically import a locale bundle the first time it is requested.
// Subsequent calls are no-ops because the bundle is already registered.
// Explicit per-locale imports (instead of a template-literal glob) keep the
// statically bundled English locale out of the dynamic-import graph.
const localeLoaders: Record<string, () => Promise<{ default: Record<string, unknown> }>> = {
  de: () => import('./locales/de.json'),
  zh: () => import('./locales/zh.json'),
}

export async function loadLocale(lang: string): Promise<void> {
  const load = localeLoaders[lang]
  if (!load || i18n.hasResourceBundle(lang, 'translation')) return
  const mod = await load()
  i18n.addResourceBundle(lang, 'translation', mod.default, true, false)
}

/** Load a locale bundle, then activate it. Always switch language through this. */
export async function setLanguage(lang: string): Promise<void> {
  await activateLanguage(i18n, lang, loadLocale)
  try {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, lang)
  } catch {
    // Storage unavailable — the choice just will not persist.
  }
}

const startLanguage = initialLanguage()
if (startLanguage !== BUNDLED_LANGUAGE) {
  // If the chunk fails to load, stay on the bundled English fallback.
  setLanguage(startLanguage).catch(() => {})
}

export default i18n

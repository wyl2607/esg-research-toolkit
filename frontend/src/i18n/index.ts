import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

// PERF: only bundle the default (English) locale in the critical path.
// German and Chinese are lazy-loaded on demand via loadLocale().
import en from './locales/en.json'

i18n.use(LanguageDetector).use(initReactI18next).init({
  resources: { en: { translation: en } },
  fallbackLng: 'en',
  supportedLngs: ['de', 'en', 'zh'],
  detection: {
    order: ['localStorage', 'navigator'],
    caches: ['localStorage'],
  },
  load: 'languageOnly',
  nonExplicitSupportedLngs: true,
  interpolation: { escapeValue: false },
})

// PERF: dynamically import a locale bundle the first time it is requested.
// Subsequent calls are no-ops because the bundle is already registered.
export async function loadLocale(lang: string): Promise<void> {
  if (lang === 'en' || i18n.hasResourceBundle(lang, 'translation')) return
  const mod = await import(`./locales/${lang}.json`)
  i18n.addResourceBundle(lang, 'translation', mod.default as Record<string, unknown>, true, false)
}

// Resolve the active locale once, deterministically, so a forced ?lang= always
// wins over the detected language instead of racing it. A ?lang=de|en|zh query
// param makes every language version of every page (e.g. /disclosures?lang=zh)
// directly callable; otherwise fall back to the detected/saved language.
const supported = new Set(['de', 'en', 'zh'])
const detected = (i18n.language || 'en').split('-')[0]
const forced =
  typeof window !== 'undefined'
    ? new URLSearchParams(window.location.search).get('lang')
    : null

const nextLang =
  forced && supported.has(forced) ? forced : supported.has(detected) ? detected : 'en'

// loadLocale() is a no-op for English and already-loaded bundles. If the chunk
// fails to load, stay on the bundled English fallback.
loadLocale(nextLang)
  .then(() => i18n.changeLanguage(nextLang))
  .catch(() => {})

export default i18n

import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

// PERF: only bundle the default (German) locale in the critical path.
// English and Chinese are lazy-loaded on demand via loadLocale().
import de from './locales/de.json'

i18n.use(LanguageDetector).use(initReactI18next).init({
  resources: { de: { translation: de } },
  lng: 'de',
  fallbackLng: ['de', 'en', 'zh'],
  supportedLngs: ['de', 'en', 'zh'],
  detection: {
    order: ['localStorage'],
    caches: ['localStorage'],
  },
  load: 'languageOnly',
  nonExplicitSupportedLngs: true,
  interpolation: { escapeValue: false },
})

// PERF: dynamically import a locale bundle the first time it is requested.
// Subsequent calls are no-ops because the bundle is already registered.
export async function loadLocale(lang: string): Promise<void> {
  if (lang === 'de' || i18n.hasResourceBundle(lang, 'translation')) return
  const mod = await import(`./locales/${lang}.json`)
  i18n.addResourceBundle(lang, 'translation', mod.default as Record<string, unknown>, true, false)
}

export default i18n

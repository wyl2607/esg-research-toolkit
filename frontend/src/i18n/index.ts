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

// Detection (saved preference or browser language) may pick a language whose
// bundle is outside the critical path; load it and re-resolve so the UI does
// not stay on fallback English.
const detected = (i18n.language || 'en').split('-')[0]
if (detected !== 'en') {
  loadLocale(detected)
    .then(() => i18n.changeLanguage(detected))
    // If the locale chunk fails to load, stay on the bundled English fallback.
    .catch(() => {})
}

export default i18n

import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

import en from './locales/en.json'
import zh from './locales/zh.json'
import de from './locales/de.json'

i18n.use(LanguageDetector).use(initReactI18next).init({
  resources: { de: { translation: de }, en: { translation: en }, zh: { translation: zh } },
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

export default i18n

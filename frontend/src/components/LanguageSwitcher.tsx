import { useTranslation } from 'react-i18next'

const LANGS = [
  { code: 'en', flag: '🇬🇧', label: 'EN' },
  { code: 'zh', flag: '🇨🇳', label: '中' },
  { code: 'de', flag: '🇩🇪', label: 'DE' },
] as const

export function LanguageSwitcher() {
  const { i18n } = useTranslation()

  return (
    <div className="flex items-center gap-1">
      {LANGS.map(({ code, flag, label }) => (
        <button
          key={code}
          onClick={() => i18n.changeLanguage(code)}
          className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
            i18n.resolvedLanguage === code
              ? 'bg-indigo-600 text-white'
              : 'text-slate-500 hover:bg-slate-100'
          }`}
          title={code}
          type="button"
        >
          {flag} {label}
        </button>
      ))}
    </div>
  )
}

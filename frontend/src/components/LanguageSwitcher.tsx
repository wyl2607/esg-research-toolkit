import { useTranslation } from 'react-i18next'
import { loadLocale } from '@/i18n/index'

const LANGS = [
  { code: 'zh', flag: '🇨🇳' },
  { code: 'en', flag: '🇬🇧' },
  { code: 'de', flag: '🇩🇪' },
] as const

export function LanguageSwitcher() {
  const { i18n, t } = useTranslation()

  return (
    <div className="inline-flex items-center gap-1 rounded-xl border border-stone-200 bg-white/85 p-1 dark:border-slate-700 dark:bg-slate-900/80">
      {LANGS.map(({ code, flag }) => (
        <button
          key={code}
          // PERF: lazy-load the locale bundle before activating it
          onClick={() => loadLocale(code).then(() => i18n.changeLanguage(code))}
          className={`inline-flex h-9 items-center gap-1 rounded-lg px-2.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-1 ${
            i18n.resolvedLanguage === code
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white'
          }`}
          title={code}
          type="button"
          aria-pressed={i18n.resolvedLanguage === code}
        >
          <span aria-hidden="true">{flag}</span>
          <span className="hidden sm:inline">{t(`language.${code}`)}</span>
          <span className="sm:hidden uppercase">{code}</span>
        </button>
      ))}
    </div>
  )
}

import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Sidebar } from './Sidebar'
import { LanguageSwitcher } from './LanguageSwitcher'
import { ThemeSwitcher } from './ThemeSwitcher'

export function Layout() {
  const { t } = useTranslation()
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

  return (
    <div className="flex h-screen overflow-hidden bg-transparent">
      <a
        href="#main-content"
        className="sr-only z-[60] rounded-md bg-white px-3 py-2 text-sm text-slate-800 focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:outline-none focus:ring-2 focus:ring-amber-600"
      >
        {t('a11y.skipToMain')}
      </a>
      <Sidebar className="hidden md:flex" />
      {mobileNavOpen && (
        <div className="fixed inset-0 z-40 bg-slate-900/35 md:hidden">
          <button
            type="button"
            className="h-full w-full"
            aria-label={t('nav.closeMenu')}
            onClick={() => setMobileNavOpen(false)}
          />
          <Sidebar
            id="mobile-sidebar"
            className="absolute left-0 top-0 h-full w-72 max-w-[84vw] border-r border-stone-200/80 bg-stone-50 shadow-xl"
            onNavigate={() => setMobileNavOpen(false)}
          />
        </div>
      )}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="app-shell h-14 border-b border-stone-200/70 dark:border-slate-700/50 flex items-center px-4 md:px-6 shrink-0 gap-2">
          <button
            type="button"
            className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-stone-200 bg-white text-slate-700 md:hidden shrink-0 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
            aria-label={mobileNavOpen ? t('nav.closeMenu') : t('nav.openMenu')}
            onClick={() => setMobileNavOpen((v) => !v)}
            aria-expanded={mobileNavOpen}
            aria-controls="mobile-sidebar"
          >
            {mobileNavOpen ? <X size={16} aria-hidden="true" /> : <Menu size={16} aria-hidden="true" />}
          </button>
          <div className="ml-auto flex items-center gap-2">
            <ThemeSwitcher />
            <LanguageSwitcher />
          </div>
        </header>
        <main id="main-content" className="flex-1 overflow-y-auto" tabIndex={-1}>
          <div className="mx-auto max-w-7xl p-4 md:p-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}

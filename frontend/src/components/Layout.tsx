import { Suspense, useEffect, useRef, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Sidebar } from './Sidebar'
import { LanguageSwitcher } from './LanguageSwitcher'
import { ThemeSwitcher } from './ThemeSwitcher'

/**
 * Route path → nav label key. Kept next to the route table it mirrors so the
 * document title and the header label come from the same place.
 */
const PAGE_LABEL_KEYS: [test: (path: string) => boolean, key: string][] = [
  [(p) => p === '/', 'nav.dashboard'],
  [(p) => p === '/disclosures', 'nav.pendingDisclosures'],
  [(p) => p.startsWith('/companies'), 'nav.companies'],
  [(p) => p === '/upload', 'nav.upload'],
  [(p) => p === '/compare', 'nav.compare'],
  [(p) => p.startsWith('/frameworks'), 'nav.frameworks'],
  [(p) => p === '/taxonomy', 'nav.taxonomy'],
  [(p) => p === '/benchmarks', 'nav.benchmarks'],
  [(p) => p === '/manual', 'nav.manual'],
  [(p) => p === '/lcoe', 'nav.lcoe'],
  [(p) => p === '/saf', 'nav.saf'],
  [(p) => p === '/regional' || p.startsWith('/coverage'), 'nav.regional'],
]

/**
 * Content-area placeholder while a lazy page chunk loads.
 *
 * The Suspense boundary used to sit above the layout, so every navigation
 * replaced the entire shell — sidebar, header and all — with the word
 * "Loading…" in the top-left corner. The boundary now wraps only the outlet,
 * so the shell stays put and just the content area changes.
 */
function PageFallback() {
  return (
    <div className="space-y-6" role="status" aria-live="polite">
      <div className="h-9 w-1/3 animate-pulse rounded-lg bg-stone-200/70 dark:bg-slate-700/50" />
      <div className="h-4 w-2/3 animate-pulse rounded-sm bg-stone-200/60 dark:bg-slate-700/40" />
      <div className="grid gap-4 md:grid-cols-3">
        <div className="h-32 animate-pulse rounded-2xl bg-stone-200/50 dark:bg-slate-700/40" />
        <div className="h-32 animate-pulse rounded-2xl bg-stone-200/50 dark:bg-slate-700/40" />
        <div className="h-32 animate-pulse rounded-2xl bg-stone-200/50 dark:bg-slate-700/40" />
      </div>
    </div>
  )
}

export function Layout() {
  const { t, i18n } = useTranslation()
  const location = useLocation()
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const mainRef = useRef<HTMLElement>(null)

  const pageLabelKey = PAGE_LABEL_KEYS.find(([test]) => test(location.pathname))?.[1]
  const pageLabel = pageLabelKey ? t(pageLabelKey) : ''

  useEffect(() => {
    document.documentElement.setAttribute('lang', i18n.resolvedLanguage || 'en')
    document.title = pageLabel ? `${pageLabel} · ${t('nav.appName')}` : t('nav.appName')
  }, [pageLabel, i18n.resolvedLanguage, t])

  // The page scrolls inside <main>, not the document, so the browser cannot
  // restore scroll on navigation: without this you arrive at a new page already
  // scrolled to wherever you left the previous one.
  useEffect(() => {
    mainRef.current?.scrollTo({ top: 0 })
  }, [location.pathname])

  return (
    <div className="flex h-screen overflow-hidden bg-transparent">
      <a
        href="#main-content"
        className="sr-only z-60 rounded-md bg-white px-3 py-2 text-sm text-slate-800 focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:outline-hidden focus:ring-2 focus:ring-amber-600"
      >
        {t('a11y.skipToMain')}
      </a>

      {/* The rail and the menu button switch at the SAME breakpoint. When they
          disagreed, the range between them had neither. */}
      <Sidebar className="hidden h-full lg:flex" />
      {mobileNavOpen && (
        <div className="fixed inset-0 z-40 bg-slate-900/35 lg:hidden">
          <button
            type="button"
            className="h-full w-full"
            aria-label={t('nav.closeMenu')}
            onClick={() => setMobileNavOpen(false)}
          />
          <Sidebar
            id="mobile-sidebar"
            className="absolute left-0 top-0 h-full max-w-[84vw] shadow-xl"
            onNavigate={() => setMobileNavOpen(false)}
          />
        </div>
      )}

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="app-shell flex h-14 shrink-0 items-center gap-2 border-b border-stone-200/70 px-4 dark:border-slate-700/50 md:px-6">
          <button
            type="button"
            className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-stone-200 bg-white text-slate-700 lg:hidden dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
            aria-label={mobileNavOpen ? t('nav.closeMenu') : t('nav.openMenu')}
            onClick={() => setMobileNavOpen((v) => !v)}
            aria-expanded={mobileNavOpen}
            aria-controls="mobile-sidebar"
          >
            {mobileNavOpen ? <X size={18} aria-hidden="true" /> : <Menu size={18} aria-hidden="true" />}
          </button>
          {/* Without the rail there was nothing on screen naming the current
              page; the header was 56px of empty space. */}
          <span className="min-w-0 truncate text-sm font-medium text-stone-700 lg:hidden dark:text-slate-200">
            {pageLabel}
          </span>
          <div className="ml-auto flex items-center gap-2">
            <ThemeSwitcher />
            <LanguageSwitcher />
          </div>
        </header>
        <main id="main-content" ref={mainRef} className="flex-1 overflow-y-auto" tabIndex={-1}>
          <div className="mx-auto max-w-7xl p-4 md:p-8">
            <Suspense fallback={<PageFallback />}>
              <Outlet />
            </Suspense>
          </div>
        </main>
      </div>
    </div>
  )
}

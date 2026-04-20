import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Upload,
  Tag,
  Zap,
  Building2,
  GitCompare,
  Globe,
  BarChart3,
  FilePenLine,
  ClipboardList,
  Plane,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'

type SidebarProps = {
  id?: string
  className?: string
  onNavigate?: () => void
}

export function Sidebar({ id, className, onNavigate }: SidebarProps) {
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)

  const disclosureLinks = [
    { to: '/', label: t('nav.dashboard'), icon: LayoutDashboard },
    { to: '/upload', label: t('nav.upload'), icon: Upload },
    { to: '/disclosures', label: t('nav.pendingDisclosures'), icon: ClipboardList },
    { to: '/companies', label: t('nav.companies'), icon: Building2 },
    { to: '/compare', label: t('nav.compare'), icon: GitCompare },
    { to: '/benchmarks', label: t('nav.benchmarks'), icon: BarChart3 },
    { to: '/frameworks', label: t('nav.frameworks'), icon: Globe },
    { to: '/taxonomy', label: t('nav.taxonomy'), icon: Tag },
  ]

  const projectLinks = [
    { to: '/manual', label: t('nav.manual'), icon: FilePenLine },
    { to: '/lcoe', label: t('nav.lcoe'), icon: Zap },
    { to: '/saf', label: t('nav.saf', 'SAF Calculator'), icon: Plane },
  ]

  const handleLinkClick = () => {
    onNavigate?.()
    setIsOpen(false)
  }

  return (
    <>
      {/* Sidebar */}
      <aside
        id={id}
        className={cn(
          'fixed lg:static left-0 top-0 z-30 h-screen w-[260px] shrink-0 border-r border-stone-200/80 dark:border-slate-700/50 bg-stone-50/90 dark:bg-slate-900/95 backdrop-blur-sm flex flex-col transition-transform duration-300 lg:translate-x-0',
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
          className
        )}
      >
        <div className="border-b border-stone-200/80 dark:border-slate-700/50 px-6 py-6">
          <div className="space-y-1">
            <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-stone-500 dark:text-slate-400">
              ESG Research
            </span>
            <div
              className="text-[1.45rem] font-semibold leading-none text-amber-800 dark:text-amber-400"
              style={{ fontFamily: "'Newsreader', Georgia, serif" }}
            >
              {t('nav.appName')}
            </div>
          </div>
        </div>
        <nav aria-label={t('nav.main')} className="flex-1 space-y-4 px-3 py-4">
          <div className="space-y-1">
            <p className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-stone-500 dark:text-slate-400">
              {t('nav.sectionDisclosure')}
            </p>
            {disclosureLinks.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  cn(
                    'flex min-h-11 items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-600 focus-visible:ring-offset-2',
                    isActive
                      ? 'bg-amber-100 text-amber-900 dark:bg-amber-900/30 dark:text-amber-300 shadow-sm'
                      : 'text-stone-700 dark:text-slate-300 hover:bg-white/80 dark:hover:bg-slate-700/50 hover:text-stone-900 dark:hover:text-slate-100'
                  )
                }
                onClick={handleLinkClick}
              >
                <Icon size={16} className="shrink-0" aria-hidden="true" />
                <span className="min-w-0 truncate">{label}</span>
              </NavLink>
            ))}
          </div>
          <div className="space-y-1">
            <p className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-stone-500 dark:text-slate-400">
              {t('nav.sectionProject')}
            </p>
            {projectLinks.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  cn(
                    'flex min-h-11 items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-600 focus-visible:ring-offset-2',
                    isActive
                      ? 'bg-amber-100 text-amber-900 dark:bg-amber-900/30 dark:text-amber-300 shadow-sm'
                      : 'text-stone-700 dark:text-slate-300 hover:bg-white/80 dark:hover:bg-slate-700/50 hover:text-stone-900 dark:hover:text-slate-100'
                  )
                }
                onClick={handleLinkClick}
              >
                <Icon size={16} className="shrink-0" aria-hidden="true" />
                <span className="min-w-0 truncate">{label}</span>
              </NavLink>
            ))}
          </div>
        </nav>
      </aside>

      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/20 lg:hidden"
          onClick={() => setIsOpen(false)}
          aria-hidden="true"
        />
      )}
    </>
  )
}

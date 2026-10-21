import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Upload,
  Tag,
  Zap,
  Building2,
  GitCompare,
  Globe,
  Map,
  BarChart3,
  FilePenLine,
  ClipboardList,
  Plane,
  type LucideIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'

type SidebarProps = {
  id?: string
  className?: string
  onNavigate?: () => void
}

type NavItem = { to: string; label: string; icon: LucideIcon }

const NAV_LINK_BASE =
  'flex min-h-11 items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-amber-600 focus-visible:ring-offset-2'
const NAV_LINK_ACTIVE =
  'bg-amber-100 text-amber-900 shadow-xs dark:bg-amber-900/30 dark:text-amber-300'
const NAV_LINK_IDLE =
  'text-stone-700 hover:bg-white/80 hover:text-stone-900 dark:text-slate-300 dark:hover:bg-slate-700/50 dark:hover:text-slate-100'

function NavSection({
  title,
  items,
  testId,
  onNavigate,
}: {
  title: string
  items: NavItem[]
  testId: string
  onNavigate?: () => void
}) {
  return (
    <div className="space-y-1" data-testid={testId}>
      <p className="section-kicker px-3 pb-1">{title}</p>
      {items.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) =>
            cn(NAV_LINK_BASE, isActive ? NAV_LINK_ACTIVE : NAV_LINK_IDLE)
          }
          onClick={onNavigate}
        >
          <Icon size={16} className="shrink-0" aria-hidden="true" />
          <span className="min-w-0 truncate">{label}</span>
        </NavLink>
      ))}
    </div>
  )
}

/**
 * Navigation rail. Purely presentational — where it sits and whether it is
 * visible is the layout's decision.
 *
 * It used to carry its own `fixed`/`-translate-x-full` positioning switched at
 * `lg`, while the layout showed and hid it at `md`. Between 768px and 1023px
 * both were true at once: the rail was translated off-screen and the layout had
 * already hidden the menu button, so on that whole range there was no way to
 * reach any other page.
 */
export function Sidebar({ id, className, onNavigate }: SidebarProps) {
  const { t } = useTranslation()

  const disclosureLinks: NavItem[] = [
    { to: '/', label: t('nav.dashboard'), icon: LayoutDashboard },
    { to: '/companies', label: t('nav.companies'), icon: Building2 },
    { to: '/upload', label: t('nav.upload'), icon: Upload },
    { to: '/disclosures', label: t('nav.pendingDisclosures'), icon: ClipboardList },
    { to: '/compare', label: t('nav.compare'), icon: GitCompare },
    { to: '/frameworks', label: t('nav.frameworks'), icon: Globe },
    { to: '/regional', label: t('nav.regional'), icon: Map },
    { to: '/taxonomy', label: t('nav.taxonomy'), icon: Tag },
  ]

  const projectLinks: NavItem[] = [
    { to: '/benchmarks', label: t('nav.benchmarks'), icon: BarChart3 },
    { to: '/manual', label: t('nav.manual'), icon: FilePenLine },
    { to: '/lcoe', label: t('nav.lcoe'), icon: Zap },
    { to: '/saf', label: t('nav.saf', 'SAF Calculator'), icon: Plane },
  ]

  return (
    <aside
      id={id}
      className={cn(
        'flex w-[260px] shrink-0 flex-col border-r border-stone-200/80 bg-stone-50/90 backdrop-blur-xs dark:border-slate-700/50 dark:bg-slate-900/95',
        className
      )}
    >
      <div className="border-b border-stone-200/80 px-6 py-6 dark:border-slate-700/50">
        <div className="space-y-1">
          <span className="section-kicker">ESG Research</span>
          <div
            className="text-[1.45rem] font-semibold leading-none text-amber-800 dark:text-amber-400"
            style={{ fontFamily: "'Newsreader', Georgia, serif" }}
          >
            {t('nav.appName')}
          </div>
        </div>
      </div>
      <nav aria-label={t('nav.main')} className="flex-1 space-y-4 overflow-y-auto px-3 py-4">
        <NavSection
          title={t('nav.sectionDisclosure')}
          items={disclosureLinks}
          testId="primary-workflow-nav"
          onNavigate={onNavigate}
        />
        <NavSection
          title={t('nav.sectionProject')}
          items={projectLinks}
          testId="optional-tools-nav"
          onNavigate={onNavigate}
        />
      </nav>
    </aside>
  )
}

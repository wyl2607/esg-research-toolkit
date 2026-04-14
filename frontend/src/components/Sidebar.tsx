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
  FilePenLine,
  SwatchBook,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'

export function Sidebar() {
  const { t } = useTranslation()

  const links = [
    { to: '/', label: t('nav.dashboard'), icon: LayoutDashboard },
    { to: '/upload', label: t('nav.upload'), icon: Upload },
    { to: '/manual', label: t('nav.manual'), icon: FilePenLine },
    { to: '/design-lab', label: t('nav.designLab'), icon: SwatchBook },
    { to: '/taxonomy', label: t('nav.taxonomy'), icon: Tag },
    { to: '/lcoe', label: t('nav.lcoe'), icon: Zap },
    { to: '/companies', label: t('nav.companies'), icon: Building2 },
    { to: '/compare', label: t('nav.compare'), icon: GitCompare },
    { to: '/frameworks', label: t('nav.frameworks'), icon: Globe },
    { to: '/regional', label: t('nav.regional'), icon: Map },
  ]

  return (
    <aside className="w-64 shrink-0 border-r border-stone-200/80 bg-stone-50/90 backdrop-blur-sm flex flex-col">
      <div className="border-b border-stone-200/80 px-6 py-6">
        <div className="space-y-1">
          <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-stone-500">
            ESG Research
          </span>
          <div className="text-[1.45rem] font-semibold leading-none text-amber-800" style={{ fontFamily: "'Newsreader', Georgia, serif" }}>
            {t('nav.appName')}
          </div>
        </div>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors',
                isActive
                  ? 'bg-amber-100 text-amber-900 shadow-sm'
                  : 'text-stone-600 hover:bg-white/80 hover:text-stone-900'
              )
            }
          >
            <Icon size={16} className="shrink-0" />
            <span className="min-w-0 truncate">{label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}

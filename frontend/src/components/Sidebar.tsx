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
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'

export function Sidebar() {
  const { t } = useTranslation()

  const links = [
    { to: '/', label: t('nav.dashboard'), icon: LayoutDashboard },
    { to: '/upload', label: t('nav.upload'), icon: Upload },
    { to: '/taxonomy', label: t('nav.taxonomy'), icon: Tag },
    { to: '/lcoe', label: t('nav.lcoe'), icon: Zap },
    { to: '/companies', label: t('nav.companies'), icon: Building2 },
    { to: '/compare', label: t('nav.compare'), icon: GitCompare },
    { to: '/frameworks', label: t('nav.frameworks'), icon: Globe },
    { to: '/regional', label: t('nav.regional'), icon: Map },
  ]

  return (
    <aside className="w-56 shrink-0 border-r bg-white flex flex-col">
      <div className="px-6 py-5 border-b">
        <span className="font-bold text-indigo-600 text-lg">{t('nav.appName')}</span>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                isActive
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-slate-600 hover:bg-slate-100'
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

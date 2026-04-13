import { useEffect, useState } from 'react'
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
  Menu,
  X,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'

export function Sidebar() {
  const { t } = useTranslation()
  const [collapsed, setCollapsed] = useState(false)

  useEffect(() => {
    const syncCollapsed = () => {
      setCollapsed(window.innerWidth < 768)
    }
    syncCollapsed()
    window.addEventListener('resize', syncCollapsed)
    return () => window.removeEventListener('resize', syncCollapsed)
  }, [])

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
    <>
      <button
        type="button"
        onClick={() => setCollapsed((v) => !v)}
        className="fixed left-3 top-2 z-50 rounded-md border bg-white p-2 text-slate-700 md:hidden"
      >
        {collapsed ? <Menu size={18} /> : <X size={18} />}
      </button>
      {!collapsed && (
        <div className="fixed inset-0 z-30 bg-slate-900/30 md:hidden" onClick={() => setCollapsed(true)} />
      )}
      <aside
        className={cn(
          'z-40 w-56 shrink-0 border-r bg-white flex flex-col transition-transform duration-200',
          'fixed inset-y-0 left-0 md:static md:translate-x-0',
          collapsed ? '-translate-x-full' : 'translate-x-0'
        )}
      >
        <div className="px-6 py-5 border-b">
          <span className="font-bold text-indigo-600 text-lg">{t('nav.appName')}</span>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              onClick={() => {
                if (window.innerWidth < 768) setCollapsed(true)
              }}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'text-slate-600 hover:bg-slate-100'
                )
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
    </>
  )
}

import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Upload,
  Tag,
  Zap,
  Building2,
  GitCompare,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const links = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/upload', label: 'Upload', icon: Upload },
  { to: '/taxonomy', label: 'Taxonomy', icon: Tag },
  { to: '/lcoe', label: 'LCOE', icon: Zap },
  { to: '/companies', label: 'Companies', icon: Building2 },
  { to: '/compare', label: 'Compare', icon: GitCompare },
]

export function Sidebar() {
  return (
    <aside className="w-56 shrink-0 border-r bg-white flex flex-col">
      <div className="px-6 py-5 border-b">
        <span className="font-bold text-indigo-600 text-lg">ESG Toolkit</span>
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
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}

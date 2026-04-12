import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { LanguageSwitcher } from './LanguageSwitcher'

export function Layout() {
  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-6xl mx-auto p-8">
          <div className="flex justify-end mb-4">
            <LanguageSwitcher />
          </div>
          <Outlet />
        </div>
      </main>
    </div>
  )
}

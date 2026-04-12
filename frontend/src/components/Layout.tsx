import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { LanguageSwitcher } from './LanguageSwitcher'

export function Layout() {
  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-10 border-b bg-white flex items-center justify-end px-6 shrink-0">
          <LanguageSwitcher />
        </header>
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-6xl mx-auto p-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}

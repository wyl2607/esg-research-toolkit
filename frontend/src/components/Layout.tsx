import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { LanguageSwitcher } from './LanguageSwitcher'
import { ThemeSwitcher } from './ThemeSwitcher'

export function Layout() {
  return (
    <div className="flex h-screen overflow-hidden bg-transparent">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="app-shell h-14 border-b border-stone-200/70 flex items-center justify-end px-4 md:px-6 shrink-0 gap-2">
          <ThemeSwitcher />
          <LanguageSwitcher />
        </header>
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-7xl p-4 md:p-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}

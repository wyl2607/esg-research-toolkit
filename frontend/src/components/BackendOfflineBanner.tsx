import { ServerOff } from 'lucide-react'
import { useTranslation } from 'react-i18next'

export function BackendOfflineBanner({ className }: { className?: string }) {
  const { t } = useTranslation()
  return (
    <div className={`rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 px-5 py-4 flex items-start gap-3 max-w-2xl ${className ?? ''}`}>
      <ServerOff size={18} className="mt-0.5 shrink-0 text-slate-400" />
      <div>
        <p className="font-medium text-slate-700 dark:text-slate-200">{t('dashboard.backendOfflineTitle')}</p>
        <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">{t('dashboard.backendOfflineBody')}</p>
      </div>
    </div>
  )
}

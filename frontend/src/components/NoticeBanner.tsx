import type { ReactNode } from 'react'
import { Info, AlertTriangle, CheckCircle2, Settings2 } from 'lucide-react'
import { cn } from '@/lib/utils'

export type NoticeTone = 'info' | 'warning' | 'success' | 'mode'

const TONES: Record<
  NoticeTone,
  { cls: string; Icon: typeof Info }
> = {
  info: {
    cls: 'border-slate-200 bg-slate-50 text-slate-800 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200',
    Icon: Info,
  },
  warning: {
    cls: 'border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-600 dark:bg-amber-900/30 dark:text-amber-200',
    Icon: AlertTriangle,
  },
  success: {
    cls: 'border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-200',
    Icon: CheckCircle2,
  },
  mode: {
    cls: 'border-violet-300 bg-violet-50 text-violet-900 dark:border-violet-600 dark:bg-violet-900/30 dark:text-violet-200',
    Icon: Settings2,
  },
}

export function NoticeBanner({
  tone = 'info',
  title,
  children,
  className,
}: {
  tone?: NoticeTone
  title?: ReactNode
  children?: ReactNode
  className?: string
}) {
  const { cls, Icon } = TONES[tone]
  return (
    <div
      className={cn('flex items-start gap-3 rounded-2xl border px-5 py-3 text-sm leading-6', cls, className)}
      role={tone === 'warning' ? 'alert' : 'status'}
    >
      <Icon size={18} className="mt-0.5 shrink-0" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        {title ? <p className="font-medium">{title}</p> : null}
        {children ? <div className={title ? 'mt-1' : ''}>{children}</div> : null}
      </div>
    </div>
  )
}

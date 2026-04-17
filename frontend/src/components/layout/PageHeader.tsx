import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

export type PageHeaderKpi = {
  label: string
  value: ReactNode
  hint?: ReactNode
}

export function PageHeader({
  title,
  subtitle,
  actions,
  kpis,
  className,
}: {
  title: ReactNode
  subtitle?: ReactNode
  actions?: ReactNode
  kpis?: PageHeaderKpi[]
  className?: string
}) {
  return (
    <header className={cn('flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between', className)}>
      <div className="min-w-0 space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-900 md:text-4xl dark:text-slate-100">
          {title}
        </h1>
        {subtitle ? (
          <p className="max-w-2xl text-sm leading-6 text-slate-600 dark:text-slate-300">{subtitle}</p>
        ) : null}
        {actions ? <div className="pt-2">{actions}</div> : null}
      </div>
      {kpis && kpis.length > 0 ? (
        <dl className="grid w-full grid-cols-2 gap-3 text-sm sm:grid-cols-3 lg:w-auto lg:min-w-[360px] lg:grid-cols-3">
          {kpis.slice(0, 4).map((kpi, idx) => (
            <div
              key={idx}
              className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800"
            >
              <dt className="text-[11px] font-medium uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">
                {kpi.label}
              </dt>
              <dd className="mt-1 numeric-mono text-3xl font-semibold text-slate-900 dark:text-slate-100">
                {kpi.value}
              </dd>
              {kpi.hint ? (
                <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{kpi.hint}</p>
              ) : null}
            </div>
          ))}
        </dl>
      ) : null}
    </header>
  )
}

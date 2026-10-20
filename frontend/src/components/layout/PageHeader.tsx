import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { MetricTile } from '@/components/MetricTile'

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
    <header className={cn('flex min-w-0 flex-col gap-6 lg:flex-row lg:items-start lg:justify-between', className)}>
      <div className="min-w-0 space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-900 wrap-anywhere md:text-4xl dark:text-slate-100">
          {title}
        </h1>
        {subtitle ? (
          <p className="max-w-2xl text-sm leading-6 text-slate-600 dark:text-slate-300">{subtitle}</p>
        ) : null}
        {actions ? <div className="pt-2">{actions}</div> : null}
      </div>
      {kpis && kpis.length > 0 ? (
        <div className="grid w-full min-w-0 grid-cols-2 gap-3 sm:grid-cols-3 lg:w-auto lg:min-w-[360px] lg:grid-cols-3">
          {kpis.slice(0, 4).map((kpi, idx) => (
            <MetricTile key={idx} label={kpi.label} value={kpi.value} hint={kpi.hint} />
          ))}
        </div>
      ) : null}
    </header>
  )
}

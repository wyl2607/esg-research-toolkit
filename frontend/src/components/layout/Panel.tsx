import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { MetricTile } from '@/components/MetricTile'

const BASE =
  'min-w-0 max-w-full rounded-2xl border border-slate-200 bg-white shadow-xs dark:border-slate-700 dark:bg-slate-800'

/** Primary content container (tables, charts, long-form sections). p-6. */
export function Panel({
  children,
  className,
  title,
  description,
  actions,
}: {
  children: ReactNode
  className?: string
  title?: ReactNode
  description?: ReactNode
  actions?: ReactNode
}) {
  return (
    <section className={cn(BASE, 'p-6', className)}>
      {(title || actions) && (
        <header className="mb-4 flex min-w-0 flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            {title ? (
              <h2 className="text-lg font-semibold text-slate-900 wrap-anywhere dark:text-slate-100">{title}</h2>
            ) : null}
            {description ? (
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{description}</p>
            ) : null}
          </div>
          {actions ? <div className="shrink-0">{actions}</div> : null}
        </header>
      )}
      {children}
    </section>
  )
}

/** Short-form container: selectors, filters, small forms. p-5. */
export function FormCard({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <div className={cn(BASE, 'p-5', className)}>{children}</div>
}

/** Single KPI tile. Re-exported so callers keep one import site; the markup
 * lives in {@link MetricTile} so every KPI in the app shares one scale. */
export function StatCard({
  label,
  value,
  hint,
  className,
}: {
  label: ReactNode
  value: ReactNode
  hint?: ReactNode
  className?: string
}) {
  return <MetricTile label={label} value={value} hint={hint} className={className} />
}

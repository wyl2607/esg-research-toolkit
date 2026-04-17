import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

/**
 * Horizontal filter/selector bar. Stacks on mobile, flows horizontally at md+.
 * Compose with <FilterBar.Field> / <FilterBar.Actions>.
 */
export function FilterBar({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        'flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:flex-row md:flex-wrap md:items-end',
        'dark:border-slate-700 dark:bg-slate-800',
        className,
      )}
    >
      {children}
    </div>
  )
}

FilterBar.Field = function Field({
  label,
  htmlFor,
  children,
  className,
}: {
  label?: ReactNode
  htmlFor?: string
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex min-w-[180px] flex-1 flex-col gap-1', className)}>
      {label ? (
        <label
          htmlFor={htmlFor}
          className="text-[11px] font-medium uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400"
        >
          {label}
        </label>
      ) : null}
      {children}
    </div>
  )
}

FilterBar.Actions = function Actions({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <div className={cn('flex flex-wrap items-center gap-2 md:ml-auto', className)}>{children}</div>
}

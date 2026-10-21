import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

export type MetricTone = 'default' | 'positive' | 'negative'

export interface MetricTileProps {
  label: ReactNode
  value: ReactNode
  /** Unit symbol shown as a chip beside the label. Use `UNITS`, never a literal. */
  unit?: ReactNode
  /** Secondary line under the value. The line is reserved even when absent. */
  hint?: ReactNode
  tone?: MetricTone
  /** Unknown value (failed request / null) — muted, and never styled as a zero. */
  unavailable?: boolean
  unavailableLabel?: string
  footer?: ReactNode
  className?: string
}

const TONE: Record<MetricTone, string> = {
  default: 'text-slate-900 dark:text-slate-100',
  positive: 'text-emerald-700 dark:text-emerald-400',
  negative: 'text-red-700 dark:text-red-400',
}

/**
 * The single KPI tile.
 *
 * Every headline number in the app renders through this component. There used
 * to be three tiles with three different scales — `MetricCard` at 1.85rem with
 * a 14px sentence-case label, `StatCard` at 1.875rem with an 11px tracked
 * label, and a third inline variant at 16px — so two KPI rows on adjacent
 * pages never matched.
 *
 * Alignment rules baked in here rather than left to each caller:
 *  - the label block reserves two lines, so values sit on the same baseline
 *    across a row even when one label wraps and its neighbours do not
 *  - the hint line is always reserved, so a row mixing "Data unavailable" with
 *    plain values still lines up
 *  - values never wrap: a number split across lines (`970.00` / `0`) is
 *    unreadable, so long values shrink the surrounding box instead
 */
export function MetricTile({
  label,
  value,
  unit,
  hint,
  tone = 'default',
  unavailable = false,
  unavailableLabel,
  footer,
  className,
}: MetricTileProps) {
  const resolvedHint = hint ?? (unavailable ? unavailableLabel : undefined)

  return (
    <div
      className={cn(
        'surface-card flex h-full min-w-0 flex-col p-5',
        className
      )}
    >
      <div className="flex min-h-[2.25rem] items-start justify-between gap-2">
        <p className="metric-label min-w-0">{label}</p>
        {unit ? <span className="metric-unit shrink-0">{unit}</span> : null}
      </div>
      <p
        className={cn(
          'metric-value mt-1',
          unavailable ? 'text-slate-400 dark:text-slate-500' : TONE[tone]
        )}
        data-metric-state={unavailable ? 'unavailable' : 'ok'}
        title={unavailable ? unavailableLabel : undefined}
        aria-label={unavailable && unavailableLabel ? `${label}: ${unavailableLabel}` : undefined}
      >
        {value}
      </p>
      <p className="metric-hint mt-1">{resolvedHint ?? ' '}</p>
      {footer ? <div className="mt-3 min-w-0 max-w-full">{footer}</div> : null}
    </div>
  )
}

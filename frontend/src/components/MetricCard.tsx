import type { ReactNode } from 'react'

import { MetricTile, type MetricTone } from '@/components/MetricTile'

interface MetricCardProps {
  label: string
  value: string | number
  sub?: string
  unit?: string
  color?: 'default' | 'green' | 'red'
  /** When true, value is unknown (failed request / null) — muted style, not a measured zero. */
  unavailable?: boolean
  unavailableLabel?: string
  footer?: ReactNode
}

const TONE_BY_COLOR: Record<NonNullable<MetricCardProps['color']>, MetricTone> = {
  default: 'default',
  green: 'positive',
  red: 'negative',
}

/**
 * Dashboard metric card. Kept as a named component because the sortable metric
 * list addresses it by props, but it is now only a thin adapter over the single
 * {@link MetricTile} so the dashboard and every other KPI row share one scale.
 */
export function MetricCard({
  label,
  value,
  sub,
  unit,
  color = 'default',
  unavailable = false,
  unavailableLabel,
  footer,
}: MetricCardProps) {
  return (
    <MetricTile
      label={label}
      value={value}
      unit={unit}
      hint={sub}
      tone={TONE_BY_COLOR[color]}
      unavailable={unavailable}
      unavailableLabel={unavailableLabel}
      footer={footer}
    />
  )
}

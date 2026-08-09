/**
 * Dashboard metric display helpers.
 *
 * Unknown / failed / null must never collapse to 0 — that is the bug class
 * this module exists to prevent (`?? 0`, `|| 0`, `Number(x) || 0`).
 */

export const METRIC_UNAVAILABLE = '—' as const

export type DashboardMetricSource =
  | { kind: 'loading' }
  | { kind: 'error' }
  | { kind: 'ready'; value: number | null | undefined }

export interface DashboardMetricDisplay {
  /** Rendered card value. Loading is handled by SortableMetricList as '…'. */
  value: string | number
  /** True when the metric is unknown (request failed or null from API). */
  unavailable: boolean
}

/**
 * Resolve a single dashboard metric for UI.
 * - loading → placeholder (caller still shows '…' via loading prop)
 * - error / null / undefined → em dash, unavailable
 * - real number including 0 → formatted value, available
 */
export function resolveDashboardMetric(
  source: DashboardMetricSource,
  format: (n: number) => string | number = (n) => n
): DashboardMetricDisplay {
  if (source.kind === 'loading') {
    return { value: METRIC_UNAVAILABLE, unavailable: false }
  }
  if (source.kind === 'error') {
    return { value: METRIC_UNAVAILABLE, unavailable: true }
  }
  const raw = source.value
  if (raw === null || raw === undefined || Number.isNaN(raw)) {
    return { value: METRIC_UNAVAILABLE, unavailable: true }
  }
  return { value: format(raw), unavailable: false }
}

export function formatCountMetric(n: number): number {
  return n
}

export function formatPercentMetric(n: number): string {
  // Keep integer-looking zeros as "0%" to match prior honest-zero display.
  if (Number.isInteger(n)) return `${n}%`
  return `${n}%`
}

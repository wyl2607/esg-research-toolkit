import type { DisclosureMergeMetric } from '@/lib/api'

export type DisclosureReviewMetricKind = 'number' | 'percent' | 'integer' | 'activities'

export const DISCLOSURE_REVIEW_METRICS: Array<{
  key: DisclosureMergeMetric
  labelKey: string
  valueKind: DisclosureReviewMetricKind
}> = [
  { key: 'scope1_co2e_tonnes', labelKey: 'companies.scope1', valueKind: 'number' },
  { key: 'scope2_co2e_tonnes', labelKey: 'companies.scope2', valueKind: 'number' },
  { key: 'scope3_co2e_tonnes', labelKey: 'companies.scope3', valueKind: 'number' },
  { key: 'energy_consumption_mwh', labelKey: 'upload.reviewMetricEnergy', valueKind: 'number' },
  { key: 'renewable_energy_pct', labelKey: 'upload.renewableEnergy', valueKind: 'percent' },
  { key: 'water_usage_m3', labelKey: 'upload.reviewMetricWater', valueKind: 'number' },
  { key: 'waste_recycled_pct', labelKey: 'upload.reviewMetricWaste', valueKind: 'percent' },
  { key: 'total_revenue_eur', labelKey: 'upload.reviewMetricRevenue', valueKind: 'number' },
  { key: 'taxonomy_aligned_revenue_pct', labelKey: 'upload.taxonomyAligned', valueKind: 'percent' },
  { key: 'total_capex_eur', labelKey: 'upload.reviewMetricCapex', valueKind: 'number' },
  { key: 'taxonomy_aligned_capex_pct', labelKey: 'upload.reviewMetricTaxonomyCapex', valueKind: 'percent' },
  { key: 'total_employees', labelKey: 'companies.employees', valueKind: 'integer' },
  { key: 'female_pct', labelKey: 'upload.reviewMetricFemale', valueKind: 'percent' },
  { key: 'primary_activities', labelKey: 'upload.reviewMetricActivities', valueKind: 'activities' },
]

function normalizeDisclosureReviewValue(
  value: unknown,
  kind: DisclosureReviewMetricKind
): unknown {
  if (value == null) return null
  if (kind === 'activities') {
    if (!Array.isArray(value)) return []
    return value.map((item) => String(item))
  }
  return value
}

export function areDisclosureReviewValuesEqual(
  current: unknown,
  next: unknown,
  kind: DisclosureReviewMetricKind
): boolean {
  const a = normalizeDisclosureReviewValue(current, kind)
  const b = normalizeDisclosureReviewValue(next, kind)
  if (a == null && b == null) return true
  if (Array.isArray(a) || Array.isArray(b)) {
    return JSON.stringify(a ?? []) === JSON.stringify(b ?? [])
  }
  return a === b
}

export function formatDisclosureReviewMetricValue(
  value: unknown,
  kind: DisclosureReviewMetricKind,
  locale: string
): string {
  if (value == null) return '—'
  if (kind === 'activities') {
    if (!Array.isArray(value)) return '—'
    return value.length ? value.join(', ') : '—'
  }
  if (typeof value !== 'number' || Number.isNaN(value)) return String(value)
  if (kind === 'percent') return `${value.toFixed(1)}%`
  if (kind === 'integer') return value.toLocaleString(locale)
  return value.toLocaleString(locale, { maximumFractionDigits: 2 })
}

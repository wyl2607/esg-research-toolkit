import type {
  CompanySourceDocument,
  CompanyTrendPoint,
  EvidenceAnchor,
  FrameworkScoreResult,
} from '@/lib/types'

export function asPct(v: number | null | undefined) {
  return v == null ? '—' : `${v.toFixed(1)}%`
}

export function asNum(v: number | null | undefined, locale: string) {
  return v == null ? '—' : v.toLocaleString(locale)
}

export function deltaNumber(current: number | null | undefined, previous: number | null | undefined) {
  if (current == null || previous == null) return null
  return current - previous
}

export function deltaPercent(current: number | null | undefined, previous: number | null | undefined) {
  if (current == null || previous == null || previous === 0) return null
  return ((current - previous) / Math.abs(previous)) * 100
}

export function deltaPctLabel(value: number | null | undefined) {
  if (value == null) return '—'
  const prefix = value > 0 ? '+' : ''
  return `${prefix}${value.toFixed(1)}`
}

export function deltaPercentLabel(value: number | null | undefined) {
  if (value == null) return '—'
  const prefix = value > 0 ? '+' : ''
  return `${prefix}${value.toFixed(1)}%`
}

export function deltaToneClass(value: number | null | undefined) {
  if (value == null) return 'text-slate-400'
  return value >= 0 ? 'text-emerald-600' : 'text-rose-600'
}

export function metricDisclosureLabel(t: (key: string) => string, metricKey: string) {
  const translated = t(`profile.metricLabels.${metricKey}`)
  return translated === `profile.metricLabels.${metricKey}`
    ? prettifyToken(metricKey)
    : translated
}

export function metricLabelsFromKeys(t: (key: string) => string, metricKeys: string[]) {
  return metricKeys.map((metricKey) => metricDisclosureLabel(t, metricKey))
}

export function asDate(value: string | null | undefined, locale: string) {
  if (!value) return '—'
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime())
    ? value
    : parsed.toLocaleDateString(locale, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
}

export function compactList(values: Array<string | null | undefined>, max = 3) {
  const unique = Array.from(new Set(values.filter((value): value is string => Boolean(value))))
  if (unique.length <= max) return unique.join(', ')
  return `${unique.slice(0, max).join(', ')} +${unique.length - max}`
}

export function sourceOriginLabel(source: CompanySourceDocument | null | undefined) {
  if (!source) return '—'
  if (source.source_url) {
    try {
      return new URL(source.source_url).hostname
    } catch {
      return source.source_url
    }
  }
  return source.pdf_filename ?? source.file_hash ?? source.source_id
}

export function mergeEvidenceAnchor(
  existing: EvidenceAnchor | undefined,
  incoming: EvidenceAnchor
): EvidenceAnchor {
  if (!existing) return incoming

  const merged: EvidenceAnchor = { ...existing }
  for (const [key, value] of Object.entries(incoming)) {
    const currentValue = (merged as unknown as Record<string, unknown>)[key]
    if ((currentValue == null || currentValue === '') && value != null && value !== '') {
      ;((merged as unknown) as Record<string, unknown>)[key] = value
    }
  }
  return merged
}

export function evidenceRichness(entry: EvidenceAnchor) {
  return Object.values(entry).reduce((score, value) => {
    if (typeof value === 'string') {
      return score + (value.trim() ? 1 + Math.min(value.length / 120, 1) : 0)
    }
    if (typeof value === 'number') return score + 1
    return value != null ? score + 1 : score
  }, 0)
}

export function normalizeProfileEvidenceAnchor(
  evidence: EvidenceAnchor,
  latestSources: CompanySourceDocument[],
  fallbackPeriodLabel: string | null | undefined,
  fallbackFramework: string | null | undefined
): EvidenceAnchor {
  const matchedSource =
    latestSources.find(
      (source) =>
        (evidence.file_hash && source.file_hash === evidence.file_hash) ||
        (evidence.source_url && source.source_url === evidence.source_url) ||
        (evidence.source_type &&
          source.source_document_type === evidence.source_type)
    ) ?? latestSources[0]

  return {
    ...evidence,
    page: evidence.page ?? evidence.page_number ?? null,
    source_type:
      evidence.source_type ?? matchedSource?.source_document_type ?? fallbackFramework ?? null,
    source_url: evidence.source_url ?? matchedSource?.source_url ?? null,
    file_hash: evidence.file_hash ?? matchedSource?.file_hash ?? null,
    document_title:
      evidence.document_title ??
      evidence.source ??
      matchedSource?.pdf_filename ??
      matchedSource?.source_url ??
      null,
    reporting_period_label:
      evidence.reporting_period_label ?? evidence.period_label ?? fallbackPeriodLabel ?? null,
    framework:
      evidence.framework ??
      evidence.source_type ??
      matchedSource?.source_document_type ??
      fallbackFramework ??
      null,
  }
}

export function parseCompanyReportId(sourceId: string | null | undefined): number | null {
  if (!sourceId?.startsWith('db:')) return null
  const parsed = Number.parseInt(sourceId.slice(3), 10)
  return Number.isNaN(parsed) ? null : parsed
}

type TrendDatum = {
  year: number
  scope1: number | null
  renewable: number | null
  taxonomy: number | null
}

export function buildCompanyTrendData(trend: CompanyTrendPoint[]): TrendDatum[] {
  return [...trend]
    .sort((a, b) => a.year - b.year)
    .map((point) => ({
    year: point.year,
    scope1: point.scope1,
    renewable: point.renewable_pct,
    taxonomy: point.taxonomy_aligned_revenue_pct,
  }))
}

export function prettifyToken(value: string | null | undefined) {
  if (!value) return '—'
  return value.replace(/_/g, ' ')
}

export type FrameworkDisplayResult = FrameworkScoreResult & {
  analysis_result_id?: number
  stored_at?: string | null
}

export function frameworkRunKey(framework: FrameworkDisplayResult) {
  const stableId = framework.analysis_result_id != null ? `id:${framework.analysis_result_id}` : null
  const version = framework.framework_version ?? 'unknown-version'
  const timestamp = framework.analyzed_at ?? framework.stored_at ?? 'unknown-time'
  return [
    framework.framework_id,
    stableId ?? `version:${version}`,
    stableId ? null : `at:${timestamp}`,
  ]
    .filter(Boolean)
    .join('|')
}

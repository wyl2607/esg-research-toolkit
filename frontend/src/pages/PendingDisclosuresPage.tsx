import { useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  type DisclosureMergeMetric,
  type PendingDisclosureItem,
  approveDisclosure,
  listCompanies,
  listPendingDisclosures,
  rejectDisclosure,
} from '@/lib/api'
import { localizeErrorMessage } from '@/lib/error-utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { PageContainer } from '@/components/layout/PageContainer'
import { PageHeader } from '@/components/layout/PageHeader'
import { Panel } from '@/components/layout/Panel'
import { QueryStateCard } from '@/components/QueryStateCard'
import { NoticeBanner } from '@/components/NoticeBanner'
import { useTranslation } from 'react-i18next'

type MetricKind = 'number' | 'percent' | 'integer' | 'activities'

const DISCLOSURE_REVIEW_METRICS: Array<{
  key: DisclosureMergeMetric
  labelKey: string
  valueKind: MetricKind
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

const EMPTY_PENDING_ROWS: PendingDisclosureItem[] = []

function normalizeValue(value: unknown, kind: MetricKind): unknown {
  if (value == null) return null
  if (kind === 'activities') {
    if (!Array.isArray(value)) return []
    return value.map((item) => String(item))
  }
  return value
}

function areValuesEqual(current: unknown, next: unknown, kind: MetricKind): boolean {
  const a = normalizeValue(current, kind)
  const b = normalizeValue(next, kind)
  if (a == null && b == null) return true
  if (Array.isArray(a) || Array.isArray(b)) {
    return JSON.stringify(a ?? []) === JSON.stringify(b ?? [])
  }
  return a === b
}

function formatMetricValue(value: unknown, kind: MetricKind, locale: string): string {
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

function reportKey(companyName: string, reportYear: number): string {
  return `${companyName}::${reportYear}`
}

export function PendingDisclosuresPage() {
  const { t, i18n } = useTranslation()
  const queryClient = useQueryClient()

  const pendingQuery = useQuery({
    queryKey: ['pending-disclosures-page'],
    queryFn: () => listPendingDisclosures({ status: 'pending', limit: 50 }),
    refetchInterval: 5000,
  })
  const companiesQuery = useQuery({
    queryKey: ['companies'],
    queryFn: listCompanies,
    staleTime: 60_000,
  })

  const pendingRows = pendingQuery.data ?? EMPTY_PENDING_ROWS

  const currentReportsByKey = useMemo(() => {
    const map = new Map<string, Record<string, unknown> | null>()
    for (const report of companiesQuery.data ?? []) {
      map.set(
        reportKey(report.company_name, report.report_year),
        report as unknown as Record<string, unknown>
      )
    }
    return map
  }, [companiesQuery.data])

  const approveMutation = useMutation({
    mutationFn: (pendingId: number) =>
      approveDisclosure(pendingId, { review_note: 'approved_from_disclosures_page' }),
    onSuccess: (result) => {
      queryClient.setQueryData<PendingDisclosureItem[] | undefined>(
        ['pending-disclosures-page'],
        (current) => current?.filter((row) => row.id !== result.pending.id)
      )
      void queryClient.invalidateQueries({ queryKey: ['pending-disclosures-page'] })
      void queryClient.invalidateQueries({ queryKey: ['companies'] })
    },
  })

  const rejectMutation = useMutation({
    mutationFn: (pendingId: number) =>
      rejectDisclosure(pendingId, { review_note: 'rejected_from_disclosures_page' }),
    onSuccess: (result) => {
      queryClient.setQueryData<PendingDisclosureItem[] | undefined>(
        ['pending-disclosures-page'],
        (current) => current?.filter((row) => row.id !== result.pending.id)
      )
      void queryClient.invalidateQueries({ queryKey: ['pending-disclosures-page'] })
    },
  })

  const actionError = (approveMutation.error as Error | null) ?? (rejectMutation.error as Error | null)

  return (
    <PageContainer>
      <PageHeader
        title={t('disclosures.title')}
        subtitle={t('disclosures.subtitle')}
        kpis={[{ label: t('disclosures.pendingCount'), value: pendingRows.length }]}
      />

      {pendingQuery.isLoading ? (
        <QueryStateCard
          tone="loading"
          title={t('common.loading')}
          body={t('disclosures.loading')}
        />
      ) : null}

      {pendingQuery.error ? (
        <QueryStateCard
          tone="error"
          title={t('common.error')}
          body={localizeErrorMessage(t, pendingQuery.error, 'upload.error')}
        />
      ) : null}

      {actionError ? (
        <NoticeBanner tone="warning" title={t('common.error')}>
          {localizeErrorMessage(t, actionError, 'upload.error')}
        </NoticeBanner>
      ) : null}

      {!pendingQuery.isLoading && !pendingQuery.error ? (
        <Panel>
          {pendingRows.length === 0 ? (
            <QueryStateCard
              tone="empty"
              title={t('disclosures.emptyTitle')}
              body={t('disclosures.emptyBody')}
            />
          ) : (
            <div className="space-y-4">
              {pendingRows.map((row) => {
                const baseline = currentReportsByKey.get(reportKey(row.company_name, row.report_year)) ?? null
                const extractedPayload = row.extracted_payload as Record<string, unknown>
                const metrics = DISCLOSURE_REVIEW_METRICS.map((metric) => {
                  const currentValue = baseline?.[metric.key]
                  const nextValue = extractedPayload[metric.key]
                  return {
                    ...metric,
                    currentValue,
                    nextValue,
                    changed: !areValuesEqual(currentValue, nextValue, metric.valueKind),
                  }
                }).filter((metric) => metric.currentValue != null || metric.nextValue != null)

                const changedCount = metrics.filter((metric) => metric.changed).length
                const rowBusy = approveMutation.isPending || rejectMutation.isPending

                return (
                  <article
                    key={row.id}
                    data-testid="pending-disclosure-row"
                    data-pending-id={row.id}
                    className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="space-y-1">
                        <h2 className="text-lg font-semibold text-slate-900">
                          {row.company_name} · {row.report_year}
                        </h2>
                        <p className="text-xs text-slate-500">#{row.id} · {row.source_type.toUpperCase()}</p>
                        <p className="break-all text-xs text-slate-500">{row.source_url}</p>
                        <p className="text-xs text-slate-400">
                          {new Date(row.fetched_at).toLocaleString(i18n.resolvedLanguage)}
                        </p>
                      </div>
                      <Badge variant="secondary">{row.status}</Badge>
                    </div>

                    {baseline ? (
                      <p className="mt-2 text-xs text-emerald-700">{t('disclosures.hasCurrentReport')}</p>
                    ) : (
                      <p className="mt-2 text-xs text-slate-500">{t('disclosures.noCurrentReport')}</p>
                    )}

                    <details className="mt-3" open>
                      <summary className="cursor-pointer text-sm font-medium text-slate-700">
                        {t('disclosures.diffSummary', { changed: changedCount, total: metrics.length })}
                      </summary>
                      <div className="mt-2 space-y-2">
                        {metrics.length === 0 ? (
                          <p className="text-xs text-slate-500">{t('disclosures.noComparableMetrics')}</p>
                        ) : (
                          metrics.map((metric) => (
                            <div
                              key={`${row.id}-${metric.key}`}
                              className="rounded-lg border border-stone-200 bg-stone-50/80 p-2"
                            >
                              <div className="mb-1 flex items-center justify-between gap-2">
                                <span className="text-xs font-medium text-slate-700">{t(metric.labelKey)}</span>
                                {metric.changed ? (
                                  <Badge variant="secondary" className="bg-amber-100 text-amber-900">
                                    {t('disclosures.changed')}
                                  </Badge>
                                ) : (
                                  <Badge variant="secondary">{t('disclosures.unchanged')}</Badge>
                                )}
                              </div>
                              <div className="grid gap-2 text-xs md:grid-cols-2">
                                <div className="rounded border border-stone-200 bg-white p-2">
                                  <p className="text-[11px] uppercase tracking-wide text-slate-500">
                                    {t('disclosures.currentValue')}
                                  </p>
                                  <p className="text-slate-700">
                                    {formatMetricValue(
                                      metric.currentValue,
                                      metric.valueKind,
                                      i18n.resolvedLanguage ?? 'en-US'
                                    )}
                                  </p>
                                </div>
                                <div className="rounded border border-stone-200 bg-white p-2">
                                  <p className="text-[11px] uppercase tracking-wide text-slate-500">
                                    {t('disclosures.pendingValue')}
                                  </p>
                                  <p className="text-slate-700">
                                    {formatMetricValue(
                                      metric.nextValue,
                                      metric.valueKind,
                                      i18n.resolvedLanguage ?? 'en-US'
                                    )}
                                  </p>
                                </div>
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </details>

                    <div className="mt-3 flex flex-wrap gap-2">
                      <Button
                        type="button"
                        data-testid={`pending-approve-${row.id}`}
                        onClick={() => approveMutation.mutate(row.id)}
                        disabled={rowBusy}
                      >
                        {t('upload.approveButton')}
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        data-testid={`pending-disclosure-reject-${row.id}`}
                        onClick={() => rejectMutation.mutate(row.id)}
                        disabled={rowBusy}
                      >
                        {t('upload.rejectButton')}
                      </Button>
                    </div>
                  </article>
                )
              })}
            </div>
          )}
        </Panel>
      ) : null}
    </PageContainer>
  )
}

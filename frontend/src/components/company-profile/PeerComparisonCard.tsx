import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { getIndustryBenchmarks } from '@/lib/api'
import { localizeErrorMessage } from '@/lib/error-utils'
import { findNaceOption } from '@/lib/nace-codes'
import type { CompanyESGData, IndustryBenchmarkMetric } from '@/lib/types'

interface PeerComparisonCardProps {
  industryCode: string | null | undefined
  reportYear: number | null | undefined
  metrics: CompanyESGData
}

type PercentileBucket =
  | 'below_p10'
  | 'p10_p25'
  | 'p25_p50'
  | 'p50_p75'
  | 'p75_p90'
  | 'above_p90'
  | 'unknown'

interface PeerRow {
  metricName: string
  companyValue: number | null
  benchmark: IndustryBenchmarkMetric
  bucket: PercentileBucket
}

function classifyBucket(
  value: number | null,
  benchmark: IndustryBenchmarkMetric
): PercentileBucket {
  if (value == null) return 'unknown'
  if (benchmark.p10 !== null && value < benchmark.p10) return 'below_p10'
  if (benchmark.p25 !== null && value < benchmark.p25) return 'p10_p25'
  if (benchmark.p50 !== null && value < benchmark.p50) return 'p25_p50'
  if (benchmark.p75 !== null && value < benchmark.p75) return 'p50_p75'
  if (benchmark.p90 !== null && value < benchmark.p90) return 'p75_p90'
  return 'above_p90'
}

function bucketTone(bucket: PercentileBucket): string {
  switch (bucket) {
    case 'below_p10':
    case 'above_p90':
      return 'border-amber-200 bg-amber-100 text-amber-800 dark:border-amber-700/60 dark:bg-amber-900/20 dark:text-amber-200'
    case 'p10_p25':
    case 'p75_p90':
      return 'border-stone-200 bg-stone-100 text-stone-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200'
    case 'p25_p50':
    case 'p50_p75':
      return 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-700/60 dark:bg-emerald-900/20 dark:text-emerald-200'
    default:
      return 'border-stone-200 bg-stone-50 text-stone-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400'
  }
}

function formatValue(value: number | null, locale: string): string {
  if (value == null || Number.isNaN(value)) return '—'
  const digits = Math.abs(value) >= 1000 ? 0 : 2
  return value.toLocaleString(locale, {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  })
}

function formatMetricName(metricName: string): string {
  return metricName.replaceAll('_', ' ')
}

export function PeerComparisonCard(props: PeerComparisonCardProps) {
  const { industryCode, reportYear, metrics } = props
  const { t, i18n } = useTranslation()
  const locale = i18n.resolvedLanguage ?? 'en'

  const benchmarksQuery = useQuery({
    queryKey: ['benchmarks', industryCode],
    queryFn: () => getIndustryBenchmarks(industryCode as string),
    enabled: Boolean(industryCode),
  })

  const peerRows = useMemo<PeerRow[]>(() => {
    if (!benchmarksQuery.data) return []
    const allRows = benchmarksQuery.data.metrics
    if (allRows.length === 0) return []

    const yearsAvailable = [...new Set(allRows.map((row) => row.period_year))].sort(
      (a, b) => b - a
    )
    const targetYear =
      reportYear != null && yearsAvailable.includes(reportYear)
        ? reportYear
        : yearsAvailable[0]

    const metricsMap = metrics as unknown as Record<string, unknown>
    const selectedRows = allRows.filter((row) => row.period_year === targetYear)
    const rows: PeerRow[] = []

    for (const benchmark of selectedRows) {
      const rawValue = metricsMap[benchmark.metric_name]
      const companyValue = typeof rawValue === 'number' ? rawValue : null
      if (companyValue === null && benchmark.sample_size === 0) continue
      rows.push({
        metricName: benchmark.metric_name,
        companyValue,
        benchmark,
        bucket: classifyBucket(companyValue, benchmark),
      })
    }

    return rows
  }, [benchmarksQuery.data, metrics, reportYear])

  if (!industryCode) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t('peer.title')}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-stone-600 dark:text-slate-300">{t('peer.noIndustryCta')}</p>
        </CardContent>
      </Card>
    )
  }

  const naceOption = findNaceOption(industryCode)
  const industryLabel =
    naceOption == null
      ? industryCode
      : locale === 'de'
        ? naceOption.sectorDe
        : naceOption.sectorEn

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          {t('peer.titleWithIndustry', {
            industry: industryLabel,
            code: industryCode,
          })}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {benchmarksQuery.isLoading ? (
          <p className="text-sm text-stone-500 dark:text-slate-400">{t('peer.loading')}</p>
        ) : null}

        {benchmarksQuery.isError ? (
          <p className="text-sm text-red-600 dark:text-red-300">
            {localizeErrorMessage(t, benchmarksQuery.error)}
          </p>
        ) : null}

        {benchmarksQuery.isSuccess && peerRows.length === 0 ? (
          <p className="text-sm text-stone-500 dark:text-slate-400">{t('peer.empty')}</p>
        ) : null}

        {peerRows.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-stone-200 text-left text-xs uppercase text-stone-500 dark:border-slate-700 dark:text-slate-400">
                  <th className="py-2 pr-4">{t('peer.col.metric')}</th>
                  <th className="py-2 pr-4 text-right">{t('peer.col.company')}</th>
                  <th className="py-2 pr-4 text-right">{t('peer.col.p50')}</th>
                  <th className="py-2 pr-4">{t('peer.col.position')}</th>
                  <th className="py-2 pr-4 text-right">{t('peer.col.sample')}</th>
                </tr>
              </thead>
              <tbody>
                {peerRows.map((row) => (
                  <tr
                    key={row.metricName}
                    className="border-b border-stone-100 dark:border-slate-800"
                  >
                    <td className="py-2 pr-4 text-xs font-medium text-stone-700 dark:text-slate-200">
                      {formatMetricName(row.metricName)}
                    </td>
                    <td className="py-2 pr-4 text-right font-medium text-stone-900 dark:text-slate-100">
                      {formatValue(row.companyValue, locale)}
                    </td>
                    <td className="py-2 pr-4 text-right text-stone-600 dark:text-slate-300">
                      {formatValue(row.benchmark.p50, locale)}
                    </td>
                    <td className="py-2 pr-4">
                      <span
                        className={`inline-block rounded-md border px-2 py-0.5 text-xs ${bucketTone(row.bucket)}`}
                      >
                        {t(`peer.bucket.${row.bucket}`)}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-right text-xs text-stone-500 dark:text-slate-400">
                      n={row.benchmark.sample_size}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-3 text-xs text-stone-500 dark:text-slate-400">
              {t('peer.disclaimer')}
            </p>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}

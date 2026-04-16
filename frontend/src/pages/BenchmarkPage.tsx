import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'

import { Skeleton } from '@/components/ui/skeleton'
import {
  getCompaniesByIndustry,
  getIndustryBenchmarks,
  recomputeIndustryBenchmarks,
} from '@/lib/api'
import { localizeErrorMessage } from '@/lib/error-utils'
import { findNaceOption, NACE_OPTIONS } from '@/lib/nace-codes'
import type { IndustryBenchmarkMetric } from '@/lib/types'

export function BenchmarkPage() {
  const { t, i18n } = useTranslation()
  const queryClient = useQueryClient()
  const locale = i18n.resolvedLanguage ?? 'en'
  const [industryCode, setIndustryCode] = useState<string>(NACE_OPTIONS[0]?.code ?? '')
  const [selectedYear, setSelectedYear] = useState<number | null>(null)

  const benchmarksQuery = useQuery({
    queryKey: ['benchmarks', industryCode],
    queryFn: () => getIndustryBenchmarks(industryCode),
    enabled: Boolean(industryCode),
  })

  const companiesQuery = useQuery({
    queryKey: ['companies-by-industry', industryCode],
    queryFn: () => getCompaniesByIndustry(industryCode),
    enabled: Boolean(industryCode),
  })

  const recomputeMutation = useMutation({
    mutationFn: recomputeIndustryBenchmarks,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['benchmarks', industryCode] })
      await queryClient.invalidateQueries({
        queryKey: ['companies-by-industry', industryCode],
      })
    },
  })

  const metricsByYear = useMemo(() => {
    const grouped = new Map<number, IndustryBenchmarkMetric[]>()
    for (const row of benchmarksQuery.data?.metrics ?? []) {
      const bucket = grouped.get(row.period_year) ?? []
      bucket.push(row)
      grouped.set(row.period_year, bucket)
    }
    return new Map([...grouped.entries()].sort((a, b) => b[0] - a[0]))
  }, [benchmarksQuery.data])

  const availableYears = useMemo(() => [...metricsByYear.keys()], [metricsByYear])

  const effectiveYear =
    selectedYear != null && availableYears.includes(selectedYear)
      ? selectedYear
      : (availableYears[0] ?? null)
  const visibleMetrics = useMemo(
    () => (effectiveYear == null ? [] : (metricsByYear.get(effectiveYear) ?? [])),
    [effectiveYear, metricsByYear]
  )

  const latestComputedAt = useMemo(() => {
    const timestamps = visibleMetrics
      .map((row) => row.computed_at)
      .filter((value): value is string => Boolean(value))
      .map((value) => Date.parse(value))
      .filter((value) => Number.isFinite(value))
    if (!timestamps.length) return null
    return new Date(Math.max(...timestamps))
  }, [visibleMetrics])

  const option = findNaceOption(industryCode)
  const industryLabel =
    option == null
      ? industryCode
      : locale === 'de'
        ? option.sectorDe
        : option.sectorEn

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-3xl font-semibold text-stone-900 dark:text-slate-100">
          {t('benchmark.title')}
        </h1>
        <p className="text-sm text-stone-600 dark:text-slate-300">
          {t('benchmark.subtitle')}
        </p>
      </header>

      <div className="rounded-2xl border border-stone-200 bg-stone-50 px-4 py-3 text-sm text-stone-700 dark:border-slate-700 dark:bg-slate-800/80 dark:text-slate-300">
        {t('benchmark.disclaimer')}
      </div>

      <section className="surface-card space-y-4 p-5">
        <div className="grid gap-4 md:grid-cols-[2fr_1fr_auto] md:items-end">
          <div className="space-y-2">
            <label className="text-sm font-medium text-stone-700 dark:text-slate-300">
              {t('benchmark.industryLabel')}
            </label>
            <select
              className="h-11 w-full rounded-xl border border-stone-300 bg-white px-3 text-sm text-stone-800 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
              value={industryCode}
              onChange={(event) => {
                setIndustryCode(event.target.value)
                setSelectedYear(null)
              }}
            >
              {NACE_OPTIONS.map((nace) => (
                <option key={nace.code} value={nace.code}>
                  {nace.code} —{' '}
                  {locale === 'de' ? nace.sectorDe : nace.sectorEn}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-stone-700 dark:text-slate-300">
              {t('benchmark.yearLabel')}
            </label>
            <select
              className="h-11 w-full rounded-xl border border-stone-300 bg-white px-3 text-sm text-stone-800 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
              value={effectiveYear ?? ''}
              onChange={(event) => setSelectedYear(Number(event.target.value))}
              disabled={availableYears.length === 0}
            >
              {availableYears.length === 0 ? (
                <option value="">{t('benchmark.yearEmpty')}</option>
              ) : (
                availableYears.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))
              )}
            </select>
          </div>

          <button
            type="button"
            className="h-11 rounded-xl border border-stone-300 bg-stone-100 px-4 text-sm font-medium text-stone-800 transition hover:bg-stone-200 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100 dark:hover:bg-slate-600"
            onClick={() => recomputeMutation.mutate()}
            disabled={recomputeMutation.isPending}
          >
            {recomputeMutation.isPending
              ? t('benchmark.refreshingButton')
              : t('benchmark.refreshButton')}
          </button>
        </div>

        {recomputeMutation.isSuccess ? (
          <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-900 dark:border-emerald-700/50 dark:bg-emerald-900/20 dark:text-emerald-200">
            {t('benchmark.refreshSuccess', {
              industries: recomputeMutation.data.industries,
              rows: recomputeMutation.data.metric_rows,
            })}
          </p>
        ) : null}

        {recomputeMutation.isError ? (
          <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-900 dark:border-red-800/60 dark:bg-red-900/20 dark:text-red-200">
            {localizeErrorMessage(t, recomputeMutation.error)}
          </p>
        ) : null}
      </section>

      <section className="surface-card space-y-4 p-5">
        <div className="space-y-1">
          <h2 className="text-xl font-semibold text-stone-900 dark:text-slate-100">
            {t('benchmark.percentilesHeading', { industry: industryLabel })}
          </h2>
          {latestComputedAt ? (
            <p className="text-xs text-stone-500 dark:text-slate-400">
              {t('benchmark.lastComputedAt', {
                time: latestComputedAt.toLocaleString(locale),
              })}
            </p>
          ) : null}
        </div>

        {benchmarksQuery.isLoading ? (
          <div className="space-y-3">
            <Skeleton count={5} height="h-10" />
          </div>
        ) : null}

        {benchmarksQuery.isError ? (
          <p className="text-sm text-red-600 dark:text-red-300">
            {localizeErrorMessage(t, benchmarksQuery.error)}
          </p>
        ) : null}

        {benchmarksQuery.isSuccess && visibleMetrics.length === 0 ? (
          <p className="text-sm text-stone-500 dark:text-slate-400">
            {t('benchmark.emptyMetrics')}
          </p>
        ) : null}

        {visibleMetrics.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-stone-200 text-left text-xs uppercase text-stone-500 dark:border-slate-700 dark:text-slate-400">
                  <th className="py-2 pr-4">{t('benchmark.col.metric')}</th>
                  <th className="py-2 pr-4">p10</th>
                  <th className="py-2 pr-4">p25</th>
                  <th className="py-2 pr-4">p50</th>
                  <th className="py-2 pr-4">p75</th>
                  <th className="py-2 pr-4">p90</th>
                  <th className="py-2 pr-4">{t('benchmark.col.sample')}</th>
                </tr>
              </thead>
              <tbody>
                {visibleMetrics.map((row) => (
                  <tr
                    key={`${row.metric_name}-${row.period_year}`}
                    className="border-b border-stone-100 dark:border-slate-800"
                  >
                    <td className="py-2 pr-4 text-xs font-medium text-stone-700 dark:text-slate-200">
                      {formatMetricName(row.metric_name)}
                    </td>
                    <td className="py-2 pr-4">{formatNumber(row.p10, locale)}</td>
                    <td className="py-2 pr-4">{formatNumber(row.p25, locale)}</td>
                    <td className="py-2 pr-4 font-semibold">
                      {formatNumber(row.p50, locale)}
                    </td>
                    <td className="py-2 pr-4">{formatNumber(row.p75, locale)}</td>
                    <td className="py-2 pr-4">{formatNumber(row.p90, locale)}</td>
                    <td className="py-2 pr-4 text-stone-600 dark:text-slate-400">
                      {row.sample_size}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <section className="surface-card space-y-4 p-5">
        <h2 className="text-xl font-semibold text-stone-900 dark:text-slate-100">
          {t('benchmark.peersHeading', {
            count: companiesQuery.data?.company_count ?? 0,
          })}
        </h2>

        {companiesQuery.isLoading ? (
          <div className="space-y-2">
            <Skeleton count={4} height="h-12" />
          </div>
        ) : null}

        {companiesQuery.isError ? (
          <p className="text-sm text-red-600 dark:text-red-300">
            {localizeErrorMessage(t, companiesQuery.error)}
          </p>
        ) : null}

        {companiesQuery.isSuccess && companiesQuery.data.companies.length === 0 ? (
          <p className="text-sm text-stone-500 dark:text-slate-400">
            {t('benchmark.emptyPeers')}
          </p>
        ) : null}

        {companiesQuery.data && companiesQuery.data.companies.length > 0 ? (
          <ul className="space-y-2">
            {companiesQuery.data.companies.map((company) => (
              <li
                key={company.company_name}
                className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-stone-200 bg-stone-50 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800/70"
              >
                <span className="font-medium text-stone-800 dark:text-slate-100">
                  {company.company_name}
                </span>
                <span className="text-xs text-stone-500 dark:text-slate-400">
                  {company.industry_sector ?? company.industry_code ?? '—'} ·{' '}
                  {company.report_year ?? '—'}
                </span>
              </li>
            ))}
          </ul>
        ) : null}
      </section>
    </div>
  )
}

function formatMetricName(metric: string): string {
  return metric.replaceAll('_', ' ')
}

function formatNumber(value: number | null, locale: string): string {
  if (value == null || Number.isNaN(value)) return '—'
  const digits = Math.abs(value) >= 1000 ? 0 : 2
  return value.toLocaleString(locale, {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  })
}

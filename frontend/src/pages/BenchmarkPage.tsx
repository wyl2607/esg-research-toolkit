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

  const minSampleSize = useMemo(() => {
    if (!visibleMetrics.length) return null
    return visibleMetrics.reduce((smallest, row) => Math.min(smallest, row.sample_size), Number.POSITIVE_INFINITY)
  }, [visibleMetrics])
  const lowSampleSize = minSampleSize != null && Number.isFinite(minSampleSize) && minSampleSize < 5

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-3xl font-semibold text-stone-900 md:text-4xl dark:text-slate-100">
          {t('benchmark.title')}
        </h1>
        <p className="max-w-3xl text-sm leading-6 text-stone-600 dark:text-slate-300">
          {t('benchmark.subtitle')}
        </p>
      </header>

      <div className="rounded-xl border border-stone-200 bg-stone-50 px-4 py-3 text-sm leading-6 text-stone-700 dark:border-slate-700 dark:bg-slate-800/80 dark:text-slate-300">
        {t('benchmark.disclaimer')}
      </div>

      <section className="surface-card space-y-4 p-5">
        <div className="grid gap-4 md:grid-cols-12 md:items-end">
          <div className="space-y-2 md:col-span-6">
            <label className="text-sm font-medium text-stone-700 dark:text-slate-300">
              {t('benchmark.industryLabel')}
            </label>
            <select
              className="h-12 w-full rounded-xl border border-stone-300 bg-white px-3 text-sm text-stone-800 shadow-sm transition hover:border-stone-400 focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-100 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
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

          <div className="space-y-2 md:col-span-3">
            <label className="text-sm font-medium text-stone-700 dark:text-slate-300">
              {t('benchmark.yearLabel')}
            </label>
            <select
              className="h-12 w-full rounded-xl border border-stone-300 bg-white px-3 text-sm text-stone-800 shadow-sm transition hover:border-stone-400 focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-100 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
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
            className="h-12 rounded-xl bg-amber-600 px-5 text-sm font-medium text-white shadow-sm transition hover:bg-amber-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:bg-stone-300 disabled:text-stone-600 md:col-span-3 dark:focus-visible:ring-offset-slate-900"
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

        {visibleMetrics.length > 0 ? (
          <div className="flex flex-wrap gap-2 text-sm">
            <span className="inline-flex items-center rounded-full bg-stone-100 px-3 py-1 text-stone-700 dark:bg-slate-800 dark:text-slate-200">
              {industryLabel}
            </span>
            {effectiveYear != null ? (
              <span className="inline-flex items-center rounded-full bg-stone-100 px-3 py-1 text-stone-700 dark:bg-slate-800 dark:text-slate-200">
                {effectiveYear}
              </span>
            ) : null}
            {minSampleSize != null ? (
              <span className="inline-flex items-center rounded-full bg-stone-100 px-3 py-1 text-stone-700 dark:bg-slate-800 dark:text-slate-200">
                {t('benchmark.col.sample')}: {minSampleSize}
              </span>
            ) : null}
          </div>
        ) : null}

        {lowSampleSize ? (
          <div className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-700/60 dark:bg-amber-950/30 dark:text-amber-100">
            <p className="font-semibold">{t('benchmark.lowSampleWarningTitle')}</p>
            <p className="mt-1 leading-6">
              {t('benchmark.lowSampleWarningBody', { count: minSampleSize ?? 0 })}
            </p>
          </div>
        ) : null}

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
          <div className="overflow-x-auto -mx-5 px-5">
            <table className="min-w-[560px] border-collapse text-sm md:min-w-full">
              <thead>
                <tr className="border-b border-stone-200 text-left text-[11px] uppercase tracking-wide text-stone-500 dark:border-slate-700 dark:text-slate-400">
                  <th className="sticky left-0 bg-white py-2.5 pr-4 dark:bg-[#111827]">{t('benchmark.col.metric')}</th>
                  <th className="bg-white/80 px-3 py-2.5 dark:bg-[#111827]">p10</th>
                  <th className="bg-white/80 px-3 py-2.5 dark:bg-[#111827]">p25</th>
                  <th className="bg-amber-50/80 px-3 py-2.5 font-semibold text-stone-900 dark:bg-amber-950/20 dark:text-stone-100">p50</th>
                  <th className="bg-white/80 px-3 py-2.5 dark:bg-[#111827]">p75</th>
                  <th className="bg-white/80 px-3 py-2.5 dark:bg-[#111827]">p90</th>
                  <th className="bg-white/80 px-3 py-2.5 dark:bg-[#111827]">{t('benchmark.col.sample')}</th>
                </tr>
              </thead>
              <tbody>
                {visibleMetrics.map((row) => (
                  <tr
                    key={`${row.metric_name}-${row.period_year}`}
                    className="border-b border-stone-100 even:bg-stone-50/50 dark:border-slate-800 dark:even:bg-slate-900/30"
                  >
                    <td className="sticky left-0 w-40 min-w-40 bg-inherit py-3 pr-4 text-sm font-medium leading-5 text-stone-700 dark:text-slate-200">
                      {formatMetricName(row.metric_name)}
                    </td>
                    <td className="px-3 py-3 tabular-nums">{formatNumber(row.p10, locale)}</td>
                    <td className="px-3 py-3 tabular-nums">{formatNumber(row.p25, locale)}</td>
                    <td className="bg-amber-50/60 px-3 py-3 font-semibold tabular-nums dark:bg-amber-950/10">
                      {formatNumber(row.p50, locale)}
                    </td>
                    <td className="px-3 py-3 tabular-nums">{formatNumber(row.p75, locale)}</td>
                    <td className="px-3 py-3 tabular-nums">{formatNumber(row.p90, locale)}</td>
                    <td className="px-3 py-3 text-stone-600 dark:text-slate-400">
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

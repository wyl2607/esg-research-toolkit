import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'

import { CompanyYearPicker, type CompanyYearSelection } from '@/components/CompanyYearPicker'
import { FilterBar } from '@/components/FilterBar'
import { NoticeBanner } from '@/components/NoticeBanner'
import { PageContainer } from '@/components/layout/PageContainer'
import { PageHeader } from '@/components/layout/PageHeader'
import { Panel } from '@/components/layout/Panel'
import { Skeleton } from '@/components/ui/skeleton'
import {
  getCompaniesByIndustry,
  getIndustryBenchmarks,
  listCompaniesWithYearCoverage,
  recomputeIndustryBenchmarks,
} from '@/lib/api'
import { isBackendOffline, localizeErrorMessage } from '@/lib/error-utils'
import { findNaceOption, NACE_OPTIONS } from '@/lib/nace-codes'
import type { CompanyByIndustryEntry, IndustryBenchmarkMetric } from '@/lib/types'

// ── Private panel components ──────────────────────────────────────────────

interface PercentilesProps {
  visibleMetrics: IndustryBenchmarkMetric[]
  isLoading: boolean
  isError: boolean
  isSuccess: boolean
  error: unknown
  industryLabel: string
  effectiveYear: number | null
  minSampleSize: number | null
  lowSampleSize: boolean
  latestComputedAt: Date | null
  locale: string
}

function BenchmarkPercentilesPanel({
  visibleMetrics,
  isLoading,
  isError,
  isSuccess,
  error,
  industryLabel,
  effectiveYear,
  minSampleSize,
  lowSampleSize,
  latestComputedAt,
  locale,
}: PercentilesProps) {
  const { t } = useTranslation()
  return (
    <Panel
      title={t('benchmark.percentilesHeading', { industry: industryLabel })}
      description={
        latestComputedAt
          ? t('benchmark.lastComputedAt', { time: latestComputedAt.toLocaleString(locale) })
          : undefined
      }
    >
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
        <div className="mt-4">
          <NoticeBanner tone="warning" title={t('benchmark.lowSampleWarningTitle')}>
            {t('benchmark.lowSampleWarningBody', { count: minSampleSize ?? 0 })}
          </NoticeBanner>
        </div>
      ) : null}

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton count={5} height="h-10" />
        </div>
      ) : null}

      {isError ? (
        <p className="text-sm text-red-600 dark:text-red-300">
          {localizeErrorMessage(t, error)}
        </p>
      ) : null}

      {isSuccess && visibleMetrics.length === 0 ? (
        <p className="text-sm text-stone-500 dark:text-slate-400">
          {t('benchmark.emptyMetrics')}
        </p>
      ) : null}

      {visibleMetrics.length > 0 ? (
        <div className="-mx-6 overflow-x-auto px-6">
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
                  <td className="px-3 py-3 text-stone-600 dark:text-slate-400">{row.sample_size}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </Panel>
  )
}

interface PeersProps {
  isLoading: boolean
  isError: boolean
  error: unknown
  companies: CompanyByIndustryEntry[]
  companyCount: number
}

function BenchmarkPeersPanel({ isLoading, isError, error, companies, companyCount }: PeersProps) {
  const { t } = useTranslation()
  return (
    <Panel title={t('benchmark.peersHeading', { count: companyCount })}>
      {isLoading ? (
        <div className="space-y-2">
          <Skeleton count={4} height="h-12" />
        </div>
      ) : null}

      {isError ? (
        <p className="text-sm text-red-600 dark:text-red-300">
          {localizeErrorMessage(t, error)}
        </p>
      ) : null}

      {!isLoading && !isError && companies.length === 0 ? (
        <p className="text-sm text-stone-500 dark:text-slate-400">
          {t('benchmark.emptyPeers')}
        </p>
      ) : null}

      {companies.length > 0 ? (
        <ul className="space-y-2">
          {companies.map((company) => (
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
    </Panel>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────

export function BenchmarkPage() {
  const { t, i18n } = useTranslation()
  const queryClient = useQueryClient()
  const locale = i18n.resolvedLanguage ?? 'en'
  const [industryCode, setIndustryCode] = useState<string>(NACE_OPTIONS[0]?.code ?? '')
  const [selectedYear, setSelectedYear] = useState<number | null>(null)
  const [companySelection, setCompanySelection] = useState<CompanyYearSelection>({
    company: null,
    year: null,
  })

  const companiesCoverageQuery = useQuery({
    queryKey: ['companies-v2'],
    queryFn: listCompaniesWithYearCoverage,
  })

  const coverageByName = useMemo(
    () =>
      new Map(
        (companiesCoverageQuery.data ?? []).map((row) => [row.company_name, row])
      ),
    [companiesCoverageQuery.data]
  )

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
      await queryClient.invalidateQueries({ queryKey: ['companies-by-industry', industryCode] })
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
    option == null ? industryCode : locale === 'de' ? option.sectorDe : option.sectorEn

  const minSampleSize = useMemo(() => {
    if (!visibleMetrics.length) return null
    return visibleMetrics.reduce(
      (smallest, row) => Math.min(smallest, row.sample_size),
      Number.POSITIVE_INFINITY
    )
  }, [visibleMetrics])

  const lowSampleSize =
    minSampleSize != null && Number.isFinite(minSampleSize) && minSampleSize < 5
  const backendOffline =
    isBackendOffline(companiesCoverageQuery.error) ||
    isBackendOffline(benchmarksQuery.error) ||
    isBackendOffline(companiesQuery.error)

  return (
    <PageContainer>
      <PageHeader title={t('benchmark.title')} subtitle={t('benchmark.subtitle')} />

      <NoticeBanner tone="info">{t('benchmark.disclaimer')}</NoticeBanner>

      {backendOffline ? (
        <NoticeBanner tone="warning">{t('errors.backendOffline')}</NoticeBanner>
      ) : null}

      {companiesCoverageQuery.isError ? (
        <NoticeBanner tone="warning">
          {localizeErrorMessage(t, companiesCoverageQuery.error)}
        </NoticeBanner>
      ) : null}

      <FilterBar>
        <FilterBar.Field
          label={`${t('common.company')} & ${t('common.year')}`}
          htmlFor="benchmark-company-year-picker-company"
        >
          <CompanyYearPicker
            idPrefix="benchmark-company-year-picker"
            companies={companiesCoverageQuery.data ?? []}
            value={companySelection}
            onChange={(next) => {
              setCompanySelection(next)
              const coverage = next.company ? coverageByName.get(next.company) : null
              if (coverage?.industry_code) setIndustryCode(coverage.industry_code)
              if (next.year != null) setSelectedYear(next.year)
            }}
          />
        </FilterBar.Field>

        <FilterBar.Field label={t('benchmark.industryLabel')} htmlFor="benchmark-industry">
          <select
            id="benchmark-industry"
            className="h-12 w-full rounded-xl border border-stone-300 bg-white px-3 text-sm text-stone-800 shadow-sm transition hover:border-stone-400 focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-100 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
            value={industryCode}
            onChange={(event) => {
              setIndustryCode(event.target.value)
              setSelectedYear(null)
            }}
          >
            {NACE_OPTIONS.map((nace) => (
              <option key={nace.code} value={nace.code}>
                {nace.code} — {locale === 'de' ? nace.sectorDe : nace.sectorEn}
              </option>
            ))}
          </select>
        </FilterBar.Field>

        <FilterBar.Field label={t('benchmark.yearLabel')} htmlFor="benchmark-year">
          <select
            id="benchmark-year"
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
        </FilterBar.Field>

        <FilterBar.Actions>
          <button
            type="button"
            className="h-12 rounded-xl bg-amber-600 px-5 text-sm font-medium text-white shadow-sm transition hover:bg-amber-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:bg-stone-300 disabled:text-stone-600 dark:focus-visible:ring-offset-slate-900"
            onClick={() => recomputeMutation.mutate()}
            disabled={recomputeMutation.isPending}
          >
            {recomputeMutation.isPending
              ? t('benchmark.refreshingButton')
              : t('benchmark.refreshButton')}
          </button>
        </FilterBar.Actions>
      </FilterBar>

      {recomputeMutation.isSuccess ? (
        <NoticeBanner tone="success">
          {t('benchmark.refreshSuccess', {
            industries: recomputeMutation.data.industries,
            rows: recomputeMutation.data.metric_rows,
          })}
        </NoticeBanner>
      ) : null}

      {recomputeMutation.isError ? (
        <NoticeBanner tone="warning">
          {localizeErrorMessage(t, recomputeMutation.error)}
        </NoticeBanner>
      ) : null}

      <BenchmarkPercentilesPanel
        visibleMetrics={visibleMetrics}
        isLoading={benchmarksQuery.isLoading}
        isError={benchmarksQuery.isError}
        isSuccess={benchmarksQuery.isSuccess}
        error={benchmarksQuery.error}
        industryLabel={industryLabel}
        effectiveYear={effectiveYear}
        minSampleSize={minSampleSize}
        lowSampleSize={lowSampleSize}
        latestComputedAt={latestComputedAt}
        locale={locale}
      />

      <BenchmarkPeersPanel
        isLoading={companiesQuery.isLoading}
        isError={companiesQuery.isError}
        error={companiesQuery.error}
        companies={companiesQuery.data?.companies ?? []}
        companyCount={companiesQuery.data?.company_count ?? 0}
      />
    </PageContainer>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────

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

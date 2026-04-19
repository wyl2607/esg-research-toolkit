import { lazy, Suspense, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getDashboardStats, listCompanies } from '@/lib/api'
import { SortableMetricList, type MetricItem } from '@/components/SortableMetricList'
import { QueryStateCard } from '@/components/QueryStateCard'
import { Badge } from '@/components/ui/badge'
import { PageContainer } from '@/components/layout/PageContainer'
import { PageHeader } from '@/components/layout/PageHeader'
import { Panel } from '@/components/layout/Panel'
import { NoticeBanner } from '@/components/NoticeBanner'
import { useNavigate, Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useTranslation } from 'react-i18next'
import { ArrowDownUp, ArrowRight, ArrowUpDown } from 'lucide-react'
import { localizeErrorMessage, isBackendOffline } from '@/lib/error-utils'

const DashboardHeavyCharts = lazy(() =>
  import('@/components/dashboard/DashboardHeavyCharts').then((module) => ({
    default: module.DashboardHeavyCharts,
  }))
)

function CoverageBar({ label, pct, href }: { label: string; pct: number; href?: string }) {
  const colorClass = pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-400' : 'bg-red-400'
  const labelEl = href ? (
    <Link
      to={href}
      className="w-24 shrink-0 text-slate-600 hover:text-amber-700 hover:underline sm:w-36"
    >
      {label}
    </Link>
  ) : (
    <span className="w-24 shrink-0 text-slate-600 sm:w-36">{label}</span>
  )
  return (
    <div className="flex items-center gap-2 sm:gap-3 text-sm">
      {labelEl}
      <div className="h-2 flex-1 rounded-full bg-slate-100">
        <div className={`h-2 rounded-full transition-all ${colorClass}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-10 text-right font-medium text-slate-700 sm:w-12">{pct.toFixed(1)}%</span>
    </div>
  )
}

function DeferredHeavyCharts({
  ready,
  fallback,
  children,
}: {
  ready: boolean
  fallback: ReactNode
  children: ReactNode
}) {
  const [revealed, setRevealed] = useState(false)

  useEffect(() => {
    if (!ready || revealed) return

    const timer = window.setTimeout(() => setRevealed(true), 180)
    return () => window.clearTimeout(timer)
  }, [ready, revealed])

  return ready && revealed ? children : fallback
}

export function DashboardPage() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()

  const { data: companies = [], isLoading: companiesLoading, error: companiesError } = useQuery({
    queryKey: ['companies'],
    queryFn: listCompanies,
  })

  const { data: stats, isLoading: statsLoading, error: statsError } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: getDashboardStats,
  })

  const recent = [...companies].sort((a, b) => b.report_year - a.report_year).slice(0, 5)
  const coverageRows = Object.entries(stats?.coverage_rates ?? {})

  // coverage sort state: 'default' | 'asc' | 'desc'
  const [coverageSort, setCoverageSort] = useState<'default' | 'asc' | 'desc'>('default')
  const cycleCoverageSort = () =>
    setCoverageSort((s) => (s === 'default' ? 'desc' : s === 'desc' ? 'asc' : 'default'))

  const sortedCoverageRows = useMemo(() => {
    if (coverageSort === 'default') return coverageRows
    return [...coverageRows].sort(([, a], [, b]) => coverageSort === 'desc' ? b - a : a - b)
  }, [coverageRows, coverageSort])

  // progress derived stats
  const totalFields = coverageRows.length
  const goodFields = coverageRows.filter(([, pct]) => pct >= 80).length
  const partialFields = coverageRows.filter(([, pct]) => pct >= 50 && pct < 80).length
  const weakFields = totalFields - goodFields - partialFields
  const overallProgress = totalFields > 0
    ? Math.round(coverageRows.reduce((sum, [, pct]) => sum + pct, 0) / totalFields)
    : 0

  const backendOffline = isBackendOffline(statsError) || isBackendOffline(companiesError)

  const chartFallback = (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <Panel className="h-[320px] animate-pulse bg-stone-100/70"><div /></Panel>
      <Panel className="h-[320px] animate-pulse bg-stone-100/70"><div /></Panel>
    </div>
  )

  return (
    <PageContainer>
      <PageHeader
        title={t('dashboard.title')}
        subtitle={t('dashboard.subtitle')}
        actions={(
          <Button
            className="shrink-0 self-start rounded-xl bg-amber-700 text-amber-50 hover:bg-amber-800 lg:self-end"
            onClick={() => navigate('/upload')}
          >
            {t('dashboard.uploadReport')}
            <ArrowRight size={14} className="ml-1 shrink-0" aria-hidden="true" />
          </Button>
        )}
      />

      <SortableMetricList
        loading={statsLoading}
        storageKey="dashboard-metric-order"
        direction="horizontal"
        items={[
          {
            id: 'companies',
            label: t('dashboard.companiesAnalyzed'),
            value: stats?.total_companies ?? 0,
            color: 'default',
          } satisfies MetricItem,
          {
            id: 'taxonomy',
            label: t('dashboard.avgTaxonomy'),
            value: `${stats?.avg_taxonomy_aligned ?? 0}%`,
            color: 'blue',
          } satisfies MetricItem,
          {
            id: 'renewable',
            label: t('dashboard.avgRenewable'),
            value: `${stats?.avg_renewable_pct ?? 0}%`,
            color: 'blue',
          } satisfies MetricItem,
        ]}
      />

      {backendOffline ? (
        <NoticeBanner tone="info" title={t('dashboard.backendOfflineTitle')}>
          {t('dashboard.backendOfflineBody')}
        </NoticeBanner>
      ) : statsError ? (
        <QueryStateCard
          tone="error"
          title={t('common.error')}
          body={localizeErrorMessage(t, statsError, 'common.error')}
        />
      ) : null}

      <DeferredHeavyCharts ready={!statsLoading} fallback={chartFallback}>
        <Suspense
          fallback={chartFallback}
        >
          <DashboardHeavyCharts
            yearlyTrend={stats?.yearly_trend ?? []}
            topEmitters={stats?.top_emitters ?? []}
            yearlyTrendLabel={t('dashboard.yearlyTrend')}
            topEmittersLabel={t('dashboard.topEmitters')}
            uploadsLabel={t('dashboard.uploads')}
            chartsEmptyTitle={t('dashboard.chartsEmptyTitle')}
            chartsEmptyBody={t('dashboard.chartsEmptyBody')}
          />
        </Suspense>
      </DeferredHeavyCharts>

      <Panel
        title={t('dashboard.coverageRates')}
        actions={coverageRows.length > 0 ? (
          <button
            type="button"
            onClick={cycleCoverageSort}
            className="flex items-center gap-1.5 rounded-lg border border-stone-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 shadow-sm transition hover:border-amber-400 hover:text-amber-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-600"
            aria-label={t('dashboard.coverageSortDefault')}
          >
            {coverageSort === 'default' ? (
              <><ArrowUpDown size={13} />{t('dashboard.coverageSortDefault')}</>
            ) : coverageSort === 'desc' ? (
              <><ArrowDownUp size={13} />{t('dashboard.coverageSortDesc')}</>
            ) : (
              <><ArrowUpDown size={13} />{t('dashboard.coverageSortAsc')}</>
            )}
          </button>
        ) : null}
      >

        {coverageRows.length > 0 && (
          <div className="rounded-xl border border-stone-100 bg-stone-50 px-4 py-3">
            <div className="mb-2 flex items-center justify-between text-xs text-slate-500">
              <span>{t('dashboard.coverageProgressLabel')}</span>
              <span className="font-semibold text-slate-700">
                {t('dashboard.coverageAverage', { pct: overallProgress })}
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-stone-200">
              <div
                className="h-2 rounded-full bg-gradient-to-r from-amber-400 to-green-500 transition-all"
                style={{ width: `${overallProgress}%` }}
              />
            </div>
            <div className="mt-2 flex flex-wrap gap-3 text-xs">
              <span className="flex items-center gap-1">
                <span className="inline-block h-2 w-2 rounded-full bg-green-500" />
                <span className="text-slate-600">{t('dashboard.coverageBandGood', { count: goodFields })}</span>
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block h-2 w-2 rounded-full bg-yellow-400" />
                <span className="text-slate-600">{t('dashboard.coverageBandPartial', { count: partialFields })}</span>
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block h-2 w-2 rounded-full bg-red-400" />
                <span className="text-slate-600">{t('dashboard.coverageBandWeak', { count: weakFields })}</span>
              </span>
            </div>
          </div>
        )}

        {coverageRows.length === 0 ? (
          <QueryStateCard
            tone="empty"
            title={t('common.noData')}
            body={t('dashboard.noReportsYet')}
          />
        ) : (
          <div className="space-y-3">
            {sortedCoverageRows.map(([field, pct]) => (
              <CoverageBar
                key={field}
                label={t(`coverageField.labels.${field}`, { defaultValue: field })}
                pct={pct}
                href={`/coverage/${field}`}
              />
            ))}
          </div>
        )}
      </Panel>

      <Panel title={t('dashboard.recentAnalyses')}>
        {companiesError && !backendOffline ? (
          <QueryStateCard
            tone="error"
            title={t('common.error')}
            body={localizeErrorMessage(t, companiesError, 'common.error')}
          />
        ) : null}
        {companiesLoading ? (
          <QueryStateCard
            tone="loading"
            title={t('common.loading')}
            body={t('dashboard.subtitle')}
          />
        ) : recent.length === 0 ? (
          <QueryStateCard
            tone="empty"
            title={t('dashboard.noReportsYet')}
            body={t('dashboard.noCompanies')}
          />
        ) : (
          <div className="overflow-hidden">
            <div className="space-y-3 p-4 md:hidden">
              {recent.map((company) => (
                <button
                  key={`${company.company_name}-${company.report_year}`}
                  type="button"
                  className="w-full rounded-xl border border-stone-200 bg-white/90 p-3 text-left transition hover:border-stone-300 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-600"
                  onClick={() => navigate('/taxonomy')}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate font-medium text-slate-900">{company.company_name}</p>
                      <p className="text-xs text-slate-500">{company.report_year}</p>
                    </div>
                    <Badge
                      variant={
                        company.taxonomy_aligned_revenue_pct != null &&
                        company.taxonomy_aligned_revenue_pct > 50
                          ? 'default'
                          : 'secondary'
                      }
                    >
                      {company.taxonomy_aligned_revenue_pct != null
                        ? `${company.taxonomy_aligned_revenue_pct.toFixed(1)}%`
                        : '—'}
                    </Badge>
                  </div>
                  <p className="mt-2 text-xs text-slate-600">
                    {t('companies.employees')}:{' '}
                    {company.total_employees?.toLocaleString(i18n.resolvedLanguage) ?? '—'}
                  </p>
                </button>
              ))}
            </div>
            <div className="hidden overflow-x-auto md:block">
              <table className="min-w-[640px] w-full text-sm">
                <thead className="border-b editorial-table-header">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-slate-600">{t('common.company')}</th>
                    <th className="px-4 py-3 text-left font-medium text-slate-600">{t('common.year')}</th>
                    <th className="px-4 py-3 text-left font-medium text-slate-600">{t('dashboard.taxonomyPct')}</th>
                    <th className="px-4 py-3 text-left font-medium text-slate-600">{t('companies.employees')}</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((company) => (
                    <tr
                      key={`${company.company_name}-${company.report_year}`}
                      className="cursor-pointer border-b last:border-0 hover:bg-slate-50"
                      onClick={() => navigate('/taxonomy')}
                    >
                      <td className="px-4 py-3 font-medium">{company.company_name}</td>
                      <td className="px-4 py-3 text-slate-600">{company.report_year}</td>
                      <td className="px-4 py-3">
                        <Badge
                          variant={
                            company.taxonomy_aligned_revenue_pct != null &&
                            company.taxonomy_aligned_revenue_pct > 50
                              ? 'default'
                              : 'secondary'
                          }
                        >
                          {company.taxonomy_aligned_revenue_pct != null
                            ? `${company.taxonomy_aligned_revenue_pct.toFixed(1)}%`
                            : '—'}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-slate-600">
                        {company.total_employees?.toLocaleString(i18n.resolvedLanguage) ?? '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </Panel>
    </PageContainer>
  )
}

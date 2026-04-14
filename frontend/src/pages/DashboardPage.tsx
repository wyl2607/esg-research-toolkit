import { lazy, Suspense, useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getDashboardStats, listCompanies } from '@/lib/api'
import { MetricCard } from '@/components/MetricCard'
import { Badge } from '@/components/ui/badge'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useTranslation } from 'react-i18next'
import { ArrowRight } from 'lucide-react'

const DashboardHeavyCharts = lazy(() =>
  import('@/components/dashboard/DashboardHeavyCharts').then((module) => ({
    default: module.DashboardHeavyCharts,
  }))
)

const coverageLabelMap: Record<string, string> = {
  scope1_co2e_tonnes: 'Scope 1',
  scope2_co2e_tonnes: 'Scope 2',
  scope3_co2e_tonnes: 'Scope 3',
  energy_consumption_mwh: 'Energy',
  renewable_energy_pct: 'Renewable %',
  water_usage_m3: 'Water',
  waste_recycled_pct: 'Waste %',
  taxonomy_aligned_revenue_pct: 'Taxonomy %',
  female_pct: 'Female %',
}

function CoverageBar({ label, pct }: { label: string; pct: number }) {
  const colorClass = pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-400' : 'bg-red-400'
  return (
    <div className="flex items-center gap-2 sm:gap-3 text-sm">
      <span className="w-24 shrink-0 text-slate-600 sm:w-36">{label}</span>
      <div className="h-2 flex-1 rounded-full bg-slate-100">
        <div className={`h-2 rounded-full transition-all ${colorClass}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-10 text-right font-medium text-slate-700 sm:w-12">{pct.toFixed(1)}%</span>
    </div>
  )
}

export function DashboardPage() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [showHeavyCharts, setShowHeavyCharts] = useState(false)

  useEffect(() => {
    const timer = window.setTimeout(() => setShowHeavyCharts(true), 180)
    return () => window.clearTimeout(timer)
  }, [])

  const { data: companies = [], isLoading: companiesLoading } = useQuery({
    queryKey: ['companies'],
    queryFn: listCompanies,
  })

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: getDashboardStats,
  })

  const recent = [...companies].sort((a, b) => b.report_year - a.report_year).slice(0, 5)
  const coverageRows = Object.entries(stats?.coverage_rates ?? {})

  return (
    <div className="space-y-8">
      <div className="space-y-3">
        <p className="section-kicker">{t('dashboard.kicker')}</p>
        <div className="editorial-panel flex flex-col gap-4 p-5 md:flex-row md:items-end md:justify-between md:p-6">
          <div className="space-y-2">
            <h1 className="text-4xl font-semibold leading-tight text-stone-900">{t('dashboard.title')}</h1>
            <p className="max-w-3xl text-sm leading-6 text-stone-600">{t('dashboard.subtitle')}</p>
          </div>
          <Button className="h-11 rounded-xl bg-amber-700 text-amber-50 hover:bg-amber-800" onClick={() => navigate('/upload')}>
            {t('dashboard.uploadReport')}
            <ArrowRight size={14} className="ml-2" />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <MetricCard
          label={t('dashboard.companiesAnalyzed')}
          value={statsLoading ? '…' : (stats?.total_companies ?? 0)}
          color="blue"
        />
        <MetricCard
          label={t('dashboard.avgTaxonomy')}
          value={statsLoading ? '…' : `${stats?.avg_taxonomy_aligned ?? 0}%`}
          color="green"
        />
        <MetricCard
          label={t('dashboard.avgRenewable')}
          value={statsLoading ? '…' : `${stats?.avg_renewable_pct ?? 0}%`}
          color="green"
        />
      </div>

      {showHeavyCharts ? (
        <Suspense
          fallback={
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <div className="editorial-panel h-[320px] animate-pulse bg-stone-100/70" />
              <div className="editorial-panel h-[320px] animate-pulse bg-stone-100/70" />
            </div>
          }
        >
          <DashboardHeavyCharts
            yearlyTrend={stats?.yearly_trend ?? []}
            topEmitters={stats?.top_emitters ?? []}
            yearlyTrendLabel={t('dashboard.yearlyTrend')}
            topEmittersLabel={t('dashboard.topEmitters')}
            uploadsLabel={t('dashboard.uploads')}
          />
        </Suspense>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="editorial-panel h-[320px] animate-pulse bg-stone-100/70" />
          <div className="editorial-panel h-[320px] animate-pulse bg-stone-100/70" />
        </div>
      )}

      <section className="editorial-panel space-y-3 p-4 md:p-5" aria-labelledby="coverage-rates-title">
        <h2 id="coverage-rates-title" className="text-2xl font-semibold text-stone-900">
          {t('dashboard.coverageRates')}
        </h2>
        {coverageRows.length === 0 ? (
          <p className="text-sm text-slate-400">{t('common.noData')}</p>
        ) : (
          coverageRows.map(([field, pct]) => (
            <CoverageBar key={field} label={coverageLabelMap[field] ?? field} pct={pct} />
          ))
        )}
      </section>

      <div aria-labelledby="recent-analyses-title">
        <h2 id="recent-analyses-title" className="mb-3 text-2xl font-semibold text-stone-900">
          {t('dashboard.recentAnalyses')}
        </h2>
        {companiesLoading ? (
          <p className="text-slate-400">{t('common.loading')}</p>
        ) : recent.length === 0 ? (
          <p className="text-slate-400">{t('dashboard.noReportsYet')}</p>
        ) : (
          <div className="editorial-panel overflow-hidden">
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
      </div>
    </div>
  )
}

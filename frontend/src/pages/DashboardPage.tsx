import { useQuery } from '@tanstack/react-query'
import { getDashboardStats, listCompanies } from '@/lib/api'
import { MetricCard } from '@/components/MetricCard'
import { Badge } from '@/components/ui/badge'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useTranslation } from 'react-i18next'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

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
    <div className="flex items-center gap-3 text-sm">
      <span className="w-36 shrink-0 text-slate-600">{label}</span>
      <div className="h-2 flex-1 rounded-full bg-slate-100">
        <div className={`h-2 rounded-full transition-all ${colorClass}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-12 text-right font-medium text-slate-700">{pct.toFixed(1)}%</span>
    </div>
  )
}

export function DashboardPage() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()

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
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">{t('dashboard.title')}</h1>
        <Button onClick={() => navigate('/upload')}>{t('dashboard.uploadReport')}</Button>
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

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section className="rounded-xl border p-4">
          <h2 className="mb-3 text-lg font-semibold">{t('dashboard.yearlyTrend')}</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stats?.yearly_trend ?? []}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="year" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" fill="#4f46e5" name={t('dashboard.uploads')} radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="rounded-xl border p-4">
          <h2 className="mb-3 text-lg font-semibold">{t('dashboard.topEmitters')}</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={stats?.top_emitters ?? []}
                layout="vertical"
                margin={{ top: 8, right: 16, left: 24, bottom: 8 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" />
                <YAxis type="category" dataKey="company" width={100} />
                <Tooltip />
                <Bar dataKey="scope1" name="Scope 1 (tCO₂e)" radius={[0, 6, 6, 0]}>
                  {(stats?.top_emitters ?? []).map((entry) => (
                    <Cell key={`${entry.company}-${entry.year}`} fill="#ef4444" />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>

      <section className="space-y-3 rounded-xl border p-4">
        <h2 className="text-lg font-semibold">{t('dashboard.coverageRates')}</h2>
        {coverageRows.length === 0 ? (
          <p className="text-sm text-slate-400">{t('common.noData')}</p>
        ) : (
          coverageRows.map(([field, pct]) => (
            <CoverageBar key={field} label={coverageLabelMap[field] ?? field} pct={pct} />
          ))
        )}
      </section>

      <div>
        <h2 className="mb-3 text-lg font-semibold">{t('dashboard.recentAnalyses')}</h2>
        {companiesLoading ? (
          <p className="text-slate-400">{t('common.loading')}</p>
        ) : recent.length === 0 ? (
          <p className="text-slate-400">{t('dashboard.noReportsYet')}</p>
        ) : (
          <div className="overflow-hidden rounded-lg border">
            <table className="w-full text-sm">
              <thead className="border-b bg-slate-50">
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
        )}
      </div>
    </div>
  )
}

import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { listCompanies, getDashboardStats } from '@/lib/api'
import { MetricCard } from '@/components/MetricCard'
import { Badge } from '@/components/ui/badge'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useTranslation } from 'react-i18next'
import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const COVERAGE_LABELS: Record<string, string> = {
  scope1_co2e_tonnes: 'Scope 1 CO2e',
  scope2_co2e_tonnes: 'Scope 2 CO2e',
  scope3_co2e_tonnes: 'Scope 3 CO2e',
  energy_consumption_mwh: 'Energy (MWh)',
  renewable_energy_pct: 'Renewable Energy %',
  water_usage_m3: 'Water Usage (m3)',
  waste_recycled_pct: 'Waste Recycled %',
  taxonomy_aligned_revenue_pct: 'Taxonomy Revenue %',
  female_pct: 'Female %',
}

const BAR_COLORS = ['#0ea5e9', '#0284c7', '#0369a1', '#075985', '#334155']

const CoverageBar = ({ label, pct }: { label: string; pct: number }) => (
  <div className="flex items-center gap-3 text-sm">
    <span className="w-40 text-slate-600 shrink-0">{label}</span>
    <div className="flex-1 bg-slate-100 rounded-full h-2">
      <div
        className={`h-2 rounded-full transition-all ${
          pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-400' : 'bg-red-400'
        }`}
        style={{ width: `${pct}%` }}
      />
    </div>
    <span className="w-10 text-right font-medium text-slate-700">{pct}%</span>
  </div>
)

export function DashboardPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const { data: companies = [], isLoading: isCompaniesLoading } = useQuery({
    queryKey: ['companies'],
    queryFn: listCompanies,
  })

  const { data: stats, isLoading: isStatsLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: getDashboardStats,
  })

  const recent = [...companies].slice(-5).reverse()
  const loading = isCompaniesLoading || isStatsLoading
  const coverageRates = stats?.coverage_rates ?? {}

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">{t('dashboard.title')}</h1>
        <Button onClick={() => navigate('/upload')}>{t('dashboard.uploadReport')}</Button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricCard label={t('dashboard.companiesAnalyzed')} value={stats?.total_companies ?? 0} color="blue" />
          <MetricCard label={t('dashboard.avgTaxonomy')} value={`${stats?.avg_taxonomy_aligned ?? 0}%`} color="green" />
          <MetricCard label={t('upload.renewableEnergy')} value={`${stats?.avg_renewable_pct ?? 0}%`} color="orange" />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>{t('dashboard.yearlyTrend')}</CardTitle>
          </CardHeader>
          <CardContent className="h-72">
            {loading ? (
              <Skeleton className="h-full w-full rounded-lg" />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stats?.yearly_trend ?? []}>
                  <XAxis dataKey="year" />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#0ea5e9" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('dashboard.topEmitters')}</CardTitle>
          </CardHeader>
          <CardContent className="h-72">
            {loading ? (
              <Skeleton className="h-full w-full rounded-lg" />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={stats?.top_emitters ?? []}
                  layout="vertical"
                  margin={{ top: 8, right: 12, left: 12, bottom: 8 }}
                >
                  <XAxis type="number" />
                  <YAxis dataKey="company" type="category" width={120} />
                  <Tooltip />
                  <Bar dataKey="scope1" radius={[0, 6, 6, 0]}>
                    {(stats?.top_emitters ?? []).map((entry, idx) => (
                      <Cell key={`${entry.company}-${idx}`} fill={BAR_COLORS[idx % BAR_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t('dashboard.coverageRates')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-6 rounded-md" />
              ))}
            </div>
          ) : (
            Object.entries(COVERAGE_LABELS).map(([field, label]) => (
              <CoverageBar key={field} label={label} pct={coverageRates[field] ?? 0} />
            ))
          )}
        </CardContent>
      </Card>

      <div>
        <h2 className="text-lg font-semibold mb-3">{t('dashboard.recentAnalyses')}</h2>
        {isCompaniesLoading ? null : recent.length === 0 ? (
          <p className="text-slate-400">{t('dashboard.noCompanies')}</p>
        ) : (
          <div className="rounded-lg border overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 border-b">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-slate-600">{t('common.company')}</th>
                    <th className="px-4 py-3 text-left font-medium text-slate-600">{t('common.year')}</th>
                    <th className="px-4 py-3 text-left font-medium text-slate-600">{t('upload.taxonomyAligned')}</th>
                    <th className="px-4 py-3 text-left font-medium text-slate-600">{t('companies.employees')}</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((company, idx) => (
                    <tr
                      key={`${company.company_name}-${company.report_year}-${idx}`}
                      className="border-b last:border-0 hover:bg-slate-50 cursor-pointer"
                      onClick={() => navigate('/taxonomy')}
                    >
                      <td className="px-4 py-3 font-medium">{company.company_name}</td>
                      <td className="px-4 py-3 text-slate-600">{company.report_year}</td>
                      <td className="px-4 py-3">
                        <Badge
                          variant={
                            company.taxonomy_aligned_revenue_pct && company.taxonomy_aligned_revenue_pct > 50
                              ? 'default'
                              : 'secondary'
                          }
                        >
                          {company.taxonomy_aligned_revenue_pct != null
                            ? `${company.taxonomy_aligned_revenue_pct.toFixed(1)}%`
                            : '—'}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-slate-600">{company.total_employees?.toLocaleString() ?? '—'}</td>
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

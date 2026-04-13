import { useQuery } from '@tanstack/react-query'
import { listCompanies } from '@/lib/api'
import { MetricCard } from '@/components/MetricCard'
import { Badge } from '@/components/ui/badge'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'

const readinessFields = [
  'scope1_co2e_tonnes',
  'scope2_co2e_tonnes',
  'scope3_co2e_tonnes',
  'energy_consumption_mwh',
  'renewable_energy_pct',
  'water_usage_m3',
  'waste_recycled_pct',
  'total_revenue_eur',
  'total_capex_eur',
  'total_employees',
  'female_pct',
] as const

export function DashboardPage() {
  const navigate = useNavigate()
  const { data: companies = [], isLoading } = useQuery({
    queryKey: ['companies'],
    queryFn: listCompanies,
  })

  const taxonomyAvailable = companies.filter(
    (c) => c.taxonomy_aligned_revenue_pct != null
  )
  const avgTaxonomy = taxonomyAvailable.length
    ? (
        taxonomyAvailable.reduce(
          (s, c) => s + (c.taxonomy_aligned_revenue_pct ?? 0),
          0
        ) / taxonomyAvailable.length
      ).toFixed(1)
    : '—'

  const avgReadiness = companies.length
    ? (
        companies.reduce((sum, company) => {
          const filled = readinessFields.filter(
            (field) => company[field] !== null && company[field] !== undefined
          ).length
          const activitiesReady = company.primary_activities?.length ? 1 : 0
          const total = readinessFields.length + 1
          return sum + ((filled + activitiesReady) / total) * 100
        }, 0) / companies.length
      ).toFixed(1)
    : '—'

  const taxonomyCardLabel = taxonomyAvailable.length
    ? 'Avg Taxonomy Alignment'
    : 'Avg Taxonomy Readiness (Proxy)'
  const taxonomyCardValue = taxonomyAvailable.length
    ? `${avgTaxonomy}%`
    : isLoading
      ? '…'
      : `${avgReadiness}%`

  const recent = [...companies]
    .sort((a, b) => b.report_year - a.report_year)
    .slice(0, 5)

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <Button onClick={() => navigate('/upload')}>Upload Report</Button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <MetricCard
          label="Companies Analyzed"
          value={isLoading ? '…' : companies.length}
          color="blue"
        />
        <MetricCard
          label={taxonomyCardLabel}
          value={taxonomyCardValue}
          color="green"
        />
        <MetricCard
          label="Reports with Taxonomy Data"
          value={
            isLoading
              ? '…'
              : companies.length === 0
                ? '—'
                : taxonomyAvailable.length
          }
        />
      </div>

      <div>
        <h2 className="text-lg font-semibold mb-3">Recent Analyses</h2>
        {isLoading ? (
          <p className="text-slate-400">Loading…</p>
        ) : recent.length === 0 ? (
          <p className="text-slate-400">
            No reports yet. Upload your first ESG report.
          </p>
        ) : (
          <div className="rounded-lg border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-slate-600">
                    Company
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-slate-600">
                    Year
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-slate-600">
                    Taxonomy %
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-slate-600">
                    Employees
                  </th>
                </tr>
              </thead>
              <tbody>
                {recent.map((c, i) => (
                  <tr
                    key={i}
                    className="border-b last:border-0 hover:bg-slate-50 cursor-pointer"
                    onClick={() => navigate('/companies')}
                  >
                    <td className="px-4 py-3 font-medium">{c.company_name}</td>
                    <td className="px-4 py-3 text-slate-600">
                      {c.report_year}
                    </td>
                    <td className="px-4 py-3">
                      <Badge
                        variant={
                          c.taxonomy_aligned_revenue_pct &&
                          c.taxonomy_aligned_revenue_pct > 50
                            ? 'default'
                            : 'secondary'
                        }
                      >
                        {c.taxonomy_aligned_revenue_pct != null
                          ? `${c.taxonomy_aligned_revenue_pct.toFixed(1)}%`
                          : '—'}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {c.total_employees?.toLocaleString() ?? '—'}
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

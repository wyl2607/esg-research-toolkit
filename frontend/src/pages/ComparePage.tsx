import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listCompanies } from '@/lib/api'
import { Button } from '@/components/ui/button'
import type { CompanyESGData } from '@/lib/types'
import { useTranslation } from 'react-i18next'

type RowDef = [string, (c: CompanyESGData) => string]

export function ComparePage() {
  const { t } = useTranslation()
  const [selected, setSelected] = useState<string[]>([])
  const rows: RowDef[] = [
    [
      t('compare.revenueAligned'),
      (c) =>
        c.taxonomy_aligned_revenue_pct != null
          ? `${c.taxonomy_aligned_revenue_pct.toFixed(1)}%`
          : '—',
    ],
    [t('companies.scope1'), (c) => c.scope1_co2e_tonnes?.toLocaleString() ?? '—'],
    [
      t('compare.renewable'),
      (c) =>
        c.renewable_energy_pct != null ? `${c.renewable_energy_pct.toFixed(1)}%` : '—',
    ],
    [t('companies.employees'), (c) => c.total_employees?.toLocaleString() ?? '—'],
    [t('compare.femalePct'), (c) => c.female_pct != null ? `${c.female_pct.toFixed(1)}%` : '—'],
    ['Water (m³)', (c) => c.water_usage_m3?.toLocaleString() ?? '—'],
  ]

  const { data: companies = [] } = useQuery({
    queryKey: ['companies'],
    queryFn: listCompanies,
  })

  const toggleCompany = (key: string) => {
    setSelected((prev) =>
      prev.includes(key)
        ? prev.filter((k) => k !== key)
        : prev.length < 4
          ? [...prev, key]
          : prev
    )
  }

  const selectedCompanies: CompanyESGData[] = selected
    .map((k) => {
      const [name, year] = k.split('|')
      return companies.find(
        (c) => c.company_name === name && c.report_year === Number(year)
      )
    })
    .filter(Boolean) as CompanyESGData[]

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-slate-900">{t('compare.title')}</h1>

      <div>
        <p className="text-sm text-slate-500 mb-3">
          {t('compare.selectUp4')}
        </p>
        <div className="flex flex-wrap gap-2">
          {companies.map((c) => {
            const key = `${c.company_name}|${c.report_year}`
            return (
              <Button
                key={key}
                variant={selected.includes(key) ? 'default' : 'outline'}
                size="sm"
                onClick={() => toggleCompany(key)}
              >
                {c.company_name} ({c.report_year})
              </Button>
            )
          })}
        </div>
      </div>

      {selectedCompanies.length >= 2 ? (
        <div className="space-y-8">
          {/* Metrics table */}
          <div>
            <h2 className="text-lg font-semibold mb-4">{t('dashboard.keyMetrics')}</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm border rounded-lg overflow-hidden">
                <thead className="bg-slate-50 border-b">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-slate-600">
                      {t('common.summary')}
                    </th>
                    {selectedCompanies.map((c) => (
                      <th
                        key={`${c.company_name}${c.report_year}`}
                        className="px-4 py-3 text-left font-medium text-slate-600"
                      >
                        {c.company_name} ({c.report_year})
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map(([label, fmt]) => (
                    <tr key={label} className="border-b last:border-0">
                      <td className="px-4 py-2 text-slate-600 font-medium">
                        {label}
                      </td>
                      {selectedCompanies.map((c) => (
                        <td
                          key={`${c.company_name}${c.report_year}`}
                          className="px-4 py-2"
                        >
                          {fmt(c)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Radar charts side-by-side (only for companies that have taxonomy data) */}
          <div>
            <h2 className="text-lg font-semibold mb-4">
              {t('taxonomy.objectiveScores')}
            </h2>
            <p className="text-sm text-slate-400">
              {t('taxonomy.selectPrompt')}
            </p>
          </div>
        </div>
      ) : (
        <p className="text-slate-400 text-center py-12">
          {t('compare.noSelection')}
        </p>
      )}
    </div>
  )
}

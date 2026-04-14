import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listCompanies } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import type { CompanyESGData } from '@/lib/types'
import { useTranslation } from 'react-i18next'
import { localizeErrorMessage } from '@/lib/error-utils'

type RowDef = {
  label: string
  unit?: string
  format: (c: CompanyESGData) => string
}

export function ComparePage() {
  const { t, i18n } = useTranslation()
  const [selected, setSelected] = useState<string[]>([])

  const rows: RowDef[] = [
    {
      label: t('compare.revenueAligned'),
      unit: '%',
      format: (c) =>
        c.taxonomy_aligned_revenue_pct != null
          ? `${c.taxonomy_aligned_revenue_pct.toFixed(1)}%`
          : '—',
    },
    {
      label: t('companies.scope1'),
      unit: 'tCO2e',
      format: (c) => c.scope1_co2e_tonnes?.toLocaleString(i18n.resolvedLanguage) ?? '—',
    },
    {
      label: t('compare.renewable'),
      unit: '%',
      format: (c) =>
        c.renewable_energy_pct != null ? `${c.renewable_energy_pct.toFixed(1)}%` : '—',
    },
    {
      label: t('companies.employees'),
      unit: t('companies.unitPeople'),
      format: (c) => c.total_employees?.toLocaleString(i18n.resolvedLanguage) ?? '—',
    },
    {
      label: t('compare.femalePct'),
      unit: '%',
      format: (c) => (c.female_pct != null ? `${c.female_pct.toFixed(1)}%` : '—'),
    },
    {
      label: t('compare.waterUsage'),
      unit: 'm3',
      format: (c) => c.water_usage_m3?.toLocaleString(i18n.resolvedLanguage) ?? '—',
    },
  ]

  const { data: companies = [], isLoading, error } = useQuery({
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
      return companies.find((c) => c.company_name === name && c.report_year === Number(year))
    })
    .filter(Boolean) as CompanyESGData[]

  return (
    <div className="space-y-8">
      <section className="editorial-panel space-y-3">
        <p className="section-kicker">{t('compare.kicker')}</p>
        <div>
          <h1 className="text-4xl text-slate-900">{t('compare.title')}</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            {t('compare.subtitle')}
          </p>
        </div>
      </section>

      {error && (
        <p className="text-sm text-red-500">{localizeErrorMessage(t, error, 'common.error')}</p>
      )}
      {isLoading && <p className="text-sm text-slate-400">{t('common.loading')}</p>}

      <div className="surface-card">
        <p className="mb-3 text-sm text-slate-500">{t('compare.selectUp4')}</p>
        <div className="flex flex-wrap gap-2">
          {companies.map((c) => {
            const key = `${c.company_name}|${c.report_year}`
            return (
              <Button
                key={key}
                variant={selected.includes(key) ? 'default' : 'outline'}
                size="sm"
                className="h-auto max-w-full whitespace-normal px-3 py-2 text-left leading-5"
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
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {selectedCompanies.map((company) => (
              <div
                key={`${company.company_name}-${company.report_year}`}
                className="surface-card space-y-3"
              >
                <div className="space-y-2">
                  <p className="section-kicker">{t('common.company')}</p>
                  <h2 className="text-xl leading-snug text-slate-900">{company.company_name}</h2>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="secondary" className="bg-stone-100 text-slate-700">
                      {company.report_year}
                    </Badge>
                    {company.source_document_type && (
                      <Badge variant="secondary" className="bg-amber-100 text-amber-900">
                        {company.source_document_type}
                      </Badge>
                    )}
                  </div>
                </div>
                <div className="grid gap-2 text-sm">
                  <div className="rounded-xl border border-stone-200 bg-white/80 px-3 py-3">
                    <div className="text-xs uppercase tracking-wide text-stone-500">
                      {t('compare.revenueAligned')}
                    </div>
                    <div className="mt-1 text-lg font-semibold text-slate-900">
                      {company.taxonomy_aligned_revenue_pct != null
                        ? `${company.taxonomy_aligned_revenue_pct.toFixed(1)}%`
                        : '—'}
                    </div>
                  </div>
                  <div className="rounded-xl border border-stone-200 bg-white/80 px-3 py-3">
                    <div className="text-xs uppercase tracking-wide text-stone-500">
                      {t('compare.renewable')}
                    </div>
                    <div className="mt-1 text-lg font-semibold text-slate-900">
                      {company.renewable_energy_pct != null
                        ? `${company.renewable_energy_pct.toFixed(1)}%`
                        : '—'}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="editorial-panel">
            <h2 className="mb-4 text-2xl text-slate-900">{t('compare.tableTitle')}</h2>
            <div className="overflow-x-auto">
              <table className="w-full overflow-hidden rounded-2xl border border-stone-200 text-sm">
                <thead className="editorial-table-header">
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
                  {rows.map((row) => (
                    <tr key={row.label} className="border-b border-stone-200 last:border-0">
                      <td className="px-4 py-3 font-medium text-slate-700">
                        <div className="flex flex-wrap items-center gap-2">
                          <span>{row.label}</span>
                          {row.unit && <span className="metric-unit">{row.unit}</span>}
                        </div>
                      </td>
                      {selectedCompanies.map((c) => (
                        <td
                          key={`${c.company_name}${c.report_year}`}
                          className="px-4 py-3 text-slate-900"
                        >
                          {row.format(c)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="surface-card">
            <h2 className="mb-2 text-2xl text-slate-900">{t('taxonomy.objectiveScores')}</h2>
            <p className="text-sm leading-6 text-slate-600">{t('compare.pickAtLeastTwo')}</p>
          </div>
        </div>
      ) : (
        <p className="py-12 text-center text-slate-400">{t('compare.noSelection')}</p>
      )}
    </div>
  )
}

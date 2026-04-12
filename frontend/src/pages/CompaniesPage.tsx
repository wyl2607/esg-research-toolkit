import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listCompanies, deleteCompany } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Trash2, Search, Download } from 'lucide-react'
import type { CompanyESGData } from '@/lib/types'
import { useTranslation } from 'react-i18next'

type SortKey = 'company_name' | 'report_year' | 'taxonomy_aligned_revenue_pct'

export function CompaniesPage() {
  const { t } = useTranslation()
  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('report_year')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const queryClient = useQueryClient()

  const { data: companies = [], isLoading } = useQuery({
    queryKey: ['companies'],
    queryFn: listCompanies,
  })

  const deleteMutation = useMutation({
    mutationFn: ({ name, year }: { name: string; year: number }) =>
      deleteCompany(name, year),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['companies'] }),
  })

  const filtered = companies
    .filter((c) =>
      c.company_name.toLowerCase().includes(search.toLowerCase())
    )
    .sort((a, b) => {
      const va = (a[sortKey] as string | number | null) ?? 0
      const vb = (b[sortKey] as string | number | null) ?? 0
      if (va === vb) return 0
      const cmp = va > vb ? 1 : -1
      return sortDir === 'asc' ? cmp : -cmp
    })

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  const thCls = (key: SortKey) =>
    `px-4 py-3 text-left font-medium cursor-pointer hover:text-indigo-600 ${
      sortKey === key ? 'text-indigo-600' : 'text-slate-600'
    }`

  const handleDelete = (c: CompanyESGData) => {
    if (
      confirm(
        t('companies.deleteConfirm', { name: c.company_name, year: c.report_year })
      )
    ) {
      deleteMutation.mutate({ name: c.company_name, year: c.report_year })
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">{t('companies.title')}</h1>

      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="relative w-full md:w-72">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
          />
          <Input
            className="pl-8"
            placeholder={t('companies.searchPlaceholder')}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => window.open('/api/report/companies/export/csv')}
          >
            <Download size={14} className="mr-1" />
            {t('companies.csvExport')}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => window.open('/api/report/companies/export/xlsx')}
          >
            <Download size={14} className="mr-1" />
            {t('companies.excelExport')}
          </Button>
        </div>
      </div>

      {isLoading ? (
        <p className="text-slate-400">{t('common.loading')}</p>
      ) : filtered.length === 0 ? (
        <p className="text-slate-400">{t('companies.noResults')}</p>
      ) : (
        <div className="rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b">
              <tr>
                <th
                  className={thCls('company_name')}
                  onClick={() => toggleSort('company_name')}
                >
                  {t('common.company')}
                </th>
                <th
                  className={thCls('report_year')}
                  onClick={() => toggleSort('report_year')}
                >
                  {t('common.year')}
                </th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">
                  {t('companies.scope1')}
                </th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">
                  {t('companies.employees')}
                </th>
                <th
                  className={thCls('taxonomy_aligned_revenue_pct')}
                  onClick={() => toggleSort('taxonomy_aligned_revenue_pct')}
                >
                  {t('upload.taxonomyAligned')}
                </th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">
                  {t('common.delete')}
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c, i) => (
                <tr key={i} className="border-b last:border-0 hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium">{c.company_name}</td>
                  <td className="px-4 py-3 text-slate-600">{c.report_year}</td>
                  <td className="px-4 py-3 text-slate-600">
                    {c.scope1_co2e_tonnes?.toLocaleString() ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {c.total_employees?.toLocaleString() ?? '—'}
                  </td>
                  <td className="px-4 py-3">
                    {c.taxonomy_aligned_revenue_pct != null ? (
                      <Badge
                        variant={
                          c.taxonomy_aligned_revenue_pct > 50
                            ? 'default'
                            : 'secondary'
                        }
                      >
                        {c.taxonomy_aligned_revenue_pct.toFixed(1)}%
                      </Badge>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-red-500 hover:text-red-700"
                      onClick={() => handleDelete(c)}
                    >
                      <Trash2 size={14} />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

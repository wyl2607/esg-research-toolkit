import { Fragment, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listCompanies, deleteCompany } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Trash2, Search, Download } from 'lucide-react'
import type { CompanyESGData } from '@/lib/types'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { useNavigate } from 'react-router-dom'
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination'

type SortKey = 'company_name' | 'report_year' | 'taxonomy_aligned_revenue_pct'

export function CompaniesPage() {
  const { t } = useTranslation()
  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('report_year')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [currentPage, setCurrentPage] = useState(1)
  const queryClient = useQueryClient()
  const nav = useNavigate()

  const { data: companies = [], isLoading } = useQuery({
    queryKey: ['companies'],
    queryFn: listCompanies,
  })

  const deleteMutation = useMutation({
    mutationFn: ({ name, year }: { name: string; year: number }) =>
      deleteCompany(name, year),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['companies'] })
      toast.success(t('companies.deleteSuccess'))
    },
    onError: () => {
      toast.error(t('companies.deleteError'))
    },
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
  const pageSize = 20
  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize))
  const page = Math.min(currentPage, totalPages)
  const paginated = filtered.slice((page - 1) * pageSize, page * pageSize)

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else {
      setSortKey(key)
      setSortDir('desc')
    }
    setCurrentPage(1)
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
  const pages = Array.from({ length: totalPages }, (_, i) => i + 1)

  const visiblePages =
    totalPages <= 7
      ? pages
      : pages.filter((p) => p === 1 || p === totalPages || Math.abs(p - page) <= 1)

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
            onChange={(e) => {
              setSearch(e.target.value)
              setCurrentPage(1)
            }}
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
          <div className="overflow-x-auto">
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
                {paginated.map((c) => (
                  <tr
                    key={`${c.company_name}|${c.report_year}`}
                    className="border-b hover:bg-slate-50 cursor-pointer"
                    onClick={() => nav(`/companies/${encodeURIComponent(c.company_name)}`)}
                  >
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
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDelete(c)
                        }}
                      >
                        <Trash2 size={14} />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {filtered.length > pageSize && (
        <Pagination>
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              />
            </PaginationItem>
            {visiblePages.map((p, idx) => {
              const prev = visiblePages[idx - 1]
              const hasGap = idx > 0 && prev && p - prev > 1
              return (
                <Fragment key={p}>
                  {hasGap && (
                    <PaginationItem>
                      <PaginationEllipsis />
                    </PaginationItem>
                  )}
                  <PaginationItem>
                    <PaginationLink
                      isActive={page === p}
                      onClick={() => setCurrentPage(p)}
                    >
                      {p}
                    </PaginationLink>
                  </PaginationItem>
                </Fragment>
              )
            })}
            <PaginationItem>
              <PaginationNext
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}
    </div>
  )
}

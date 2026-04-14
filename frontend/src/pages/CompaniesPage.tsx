import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listCompanies, deleteCompany } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { QueryStateCard } from '@/components/QueryStateCard'
import { Trash2, Search, Download, Building2, CalendarRange, FileStack } from 'lucide-react'
import type { CompanyESGData } from '@/lib/types'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { localizeErrorMessage, isBackendOffline } from '@/lib/error-utils'
import { formatNumber, formatPercent } from '@/lib/format'
import { exportCompaniesCSV, exportToJSON } from '@/lib/export'
import { BackendOfflineBanner } from '@/components/BackendOfflineBanner'

type SortKey = 'company_name' | 'report_year' | 'taxonomy_aligned_revenue_pct'

export function CompaniesPage() {
  const { t, i18n } = useTranslation()
  const [search, setSearch] = useState('')
  const [visibleCount, setVisibleCount] = useState(9)
  const [sortKey, setSortKey] = useState<SortKey>('report_year')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const { data: companies = [], isLoading, error } = useQuery({
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

  const visibleCompanies = filtered.slice(0, visibleCount)

  const toggleSort = (key: SortKey) => {
    setVisibleCount(9)
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

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
      <div className="space-y-2">
        <p className="section-kicker">{t('companies.kicker')}</p>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <h1 className="text-3xl font-semibold text-slate-900">{t('companies.title')}</h1>
            <p className="max-w-3xl text-sm leading-6 text-slate-600">
              {t('companies.subtitle')}
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
            <Card className="surface-card border-slate-200/80">
              <CardContent className="px-4 py-4">
                <p className="section-kicker">{t('companies.summaryCompanies')}</p>
                <p className="mt-2 numeric-mono text-2xl font-semibold text-slate-900">{filtered.length}</p>
              </CardContent>
            </Card>
            <Card className="surface-card border-slate-200/80">
              <CardContent className="px-4 py-4">
                <p className="section-kicker">{t('companies.summaryYears')}</p>
                <p className="mt-2 numeric-mono text-2xl font-semibold text-slate-900">
                  {new Set(filtered.map((company) => company.report_year)).size}
                </p>
              </CardContent>
            </Card>
            <Card className="surface-card border-slate-200/80 col-span-2 sm:col-span-1">
              <CardContent className="px-4 py-4">
                <p className="section-kicker">{t('companies.summaryRows')}</p>
                <p className="mt-2 numeric-mono text-2xl font-semibold text-slate-900">{companies.length}</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
      {isBackendOffline(error) ? (
        <BackendOfflineBanner />
      ) : error ? (
        <QueryStateCard
          tone="error"
          title={t('common.error')}
          body={localizeErrorMessage(t, error, 'common.error')}
        />
      ) : null}
      {deleteMutation.error ? (
        <QueryStateCard
          tone="error"
          title={t('companies.deleteError')}
          body={localizeErrorMessage(t, deleteMutation.error, 'companies.deleteError')}
        />
      ) : null}

      <Card className="surface-card">
        <CardContent className="flex flex-col gap-3 p-4 md:flex-row md:items-center md:justify-between">
        <div className="relative w-full md:w-72">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
          />
          <Input
            className="h-11 rounded-xl border-slate-200 bg-white/90 pl-8"
            placeholder={t('companies.searchPlaceholder')}
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setVisibleCount(9)
            }}
          />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="rounded-xl"
            onClick={() => toggleSort('company_name')}
          >
            {t('companies.sortCompany')}
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="rounded-xl"
            onClick={() => toggleSort('report_year')}
          >
            {t('companies.sortYear')}
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="rounded-xl"
            onClick={() => toggleSort('taxonomy_aligned_revenue_pct')}
          >
            {t('companies.sortTaxonomy')}
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="rounded-xl"
            onClick={() => exportCompaniesCSV(filtered)}
            aria-label={t('companies.csvExport')}
          >
            <Download size={14} className="mr-1 shrink-0" />
            {t('companies.csvExport')}
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="rounded-xl"
            onClick={() => exportToJSON(filtered, `esg-companies-${new Date().toISOString().slice(0, 10)}.json`)}
            aria-label={t('companies.jsonExport')}
          >
            <Download size={14} className="mr-1 shrink-0" />
            {t('companies.jsonExport')}
          </Button>
        </div>
        </CardContent>
      </Card>

      {isLoading ? (
        <QueryStateCard
          tone="loading"
          title={t('common.loading')}
          body={t('companies.subtitle')}
        />
      ) : filtered.length === 0 ? (
        <QueryStateCard
          tone="empty"
          title={t('companies.noResults')}
          body={search ? `${t('common.search')}: “${search}”` : t('companies.subtitle')}
        />
      ) : (
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {visibleCompanies.map((c) => (
              <Card
                key={`${c.company_name}-${c.report_year}`}
                className="surface-card group cursor-pointer overflow-hidden transition-all duration-200 hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-[0_24px_56px_-34px_rgba(15,23,42,0.36)]"
                onClick={() => navigate(`/companies/${encodeURIComponent(c.company_name)}`)}
              >
                <CardContent className="space-y-5 p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 space-y-3">
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="secondary" className="rounded-full bg-slate-100 text-slate-700">
                        <CalendarRange size={12} className="mr-1" />
                        {c.report_year}
                      </Badge>
                      {c.source_document_type ? (
                        <Badge variant="outline" className="rounded-full border-slate-300 text-slate-600">
                          <FileStack size={12} className="mr-1" />
                          {c.source_document_type}
                        </Badge>
                      ) : null}
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5 rounded-xl bg-slate-100 p-2 text-slate-600">
                        <Building2 size={18} />
                      </div>
                      <div className="min-w-0">
                        <h2 className="text-lg font-semibold leading-tight text-slate-900 break-words">
                          {c.company_name}
                        </h2>
                        <p className="mt-1 text-xs leading-5 text-slate-500">
                          {t('companies.companyCardHint')}
                        </p>
                      </div>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="shrink-0 rounded-xl text-red-500 opacity-0 transition-opacity hover:text-red-700 group-hover:opacity-100"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleDelete(c)
                    }}
                    aria-label={t('companies.deleteConfirm', { name: c.company_name, year: c.report_year })}
                    title={t('common.delete')}
                  >
                    <Trash2 size={14} aria-hidden="true" />
                  </Button>
                </div>

                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="rounded-2xl border border-slate-200 bg-slate-50/90 px-3 py-3 dark:border-slate-600 dark:bg-slate-700/60 min-w-0">
                    <p className="section-kicker">{t('companies.metricScope1Short')}</p>
                    <p className="mt-2 numeric-mono text-base font-semibold text-slate-900 dark:text-slate-100 break-all leading-tight">
                      {formatNumber(c.scope1_co2e_tonnes, { locale: i18n.resolvedLanguage })}
                    </p>
                    <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">{t('companies.unitTco2e')}</p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50/90 px-3 py-3 dark:border-slate-600 dark:bg-slate-700/60 min-w-0">
                    <p className="section-kicker">{t('companies.metricEmployeesShort')}</p>
                    <p className="mt-2 numeric-mono text-base font-semibold text-slate-900 dark:text-slate-100 break-all leading-tight">
                      {formatNumber(c.total_employees, { locale: i18n.resolvedLanguage })}
                    </p>
                    <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">{t('companies.unitPeople')}</p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50/90 px-3 py-3 dark:border-slate-600 dark:bg-slate-700/60 min-w-0">
                    <p className="section-kicker">{t('companies.metricTaxonomyShort')}</p>
                    <p className="mt-2 numeric-mono text-base font-semibold text-slate-900 dark:text-slate-100 break-all leading-tight">
                      {formatPercent(c.taxonomy_aligned_revenue_pct, i18n.resolvedLanguage)}
                    </p>
                    <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">{t('companies.unitPercent')}</p>
                  </div>
                </div>
                </CardContent>
              </Card>
            ))}
          </div>
          {filtered.length > visibleCount ? (
            <div className="flex justify-center">
              <Button
                type="button"
                variant="outline"
                className="rounded-xl"
                onClick={() => setVisibleCount((count) => count + 9)}
              >
                {t('common.loadMore')}
              </Button>
            </div>
          ) : null}
        </div>
      )}
    </div>
  )
}

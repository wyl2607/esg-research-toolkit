import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listCompanies, deleteCompany } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { QueryStateCard } from '@/components/QueryStateCard'
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  Building2,
  CalendarRange,
  Download,
  FileStack,
  Search,
  Trash2,
} from 'lucide-react'
import type { CompanyESGData } from '@/lib/types'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { localizeErrorMessage, isBackendOffline } from '@/lib/error-utils'
import { useFormatters } from '@/lib/use-formatters'
import { UNITS } from '@/lib/units'
import { exportCompaniesCSV, exportToJSON } from '@/lib/export'
import { PageContainer } from '@/components/layout/PageContainer'
import { PageHeader } from '@/components/layout/PageHeader'
import { Panel } from '@/components/layout/Panel'
import { NoticeBanner } from '@/components/NoticeBanner'
import { FilterBar } from '@/components/FilterBar'

type SortKey = 'company_name' | 'report_year' | 'taxonomy_aligned_revenue_pct'

const SORT_OPTIONS: { key: SortKey; labelKey: string }[] = [
  { key: 'company_name', labelKey: 'companies.sortCompany' },
  { key: 'report_year', labelKey: 'companies.sortYear' },
  { key: 'taxonomy_aligned_revenue_pct', labelKey: 'companies.sortTaxonomy' },
]

/**
 * A sort control that shows whether it is the active sort and in which
 * direction. The plain buttons it replaces gave no feedback at all, so after
 * clicking one the list reordered with nothing on screen explaining why.
 */
function SortButton({
  label,
  active,
  direction,
  onClick,
}: {
  label: string
  active: boolean
  direction: 'asc' | 'desc'
  onClick: () => void
}) {
  const Icon = !active ? ArrowUpDown : direction === 'asc' ? ArrowUp : ArrowDown
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={onClick}
      aria-pressed={active}
      className={
        active
          ? 'border-amber-500 bg-amber-50 text-amber-900 hover:bg-amber-100 dark:border-amber-500/60 dark:bg-amber-500/15 dark:text-amber-200'
          : undefined
      }
    >
      <Icon size={14} className="mr-1 shrink-0" aria-hidden="true" />
      {label}
    </Button>
  )
}

/**
 * One metric inside a company card.
 *
 * Laid out as label-left / value-right rather than as three narrow columns:
 * the columns were too narrow for German compound labels, so `Mitarbeitende`
 * hyphenated into three lines and made every card a different height. The unit
 * lives here and only here — the value must not repeat it.
 */
function CompanyMetricRow({
  label,
  value,
  unit,
}: {
  label: string
  value: string
  unit: string
}) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="metric-label min-w-0">{label}</dt>
      <dd className="numeric-mono shrink-0 whitespace-nowrap text-sm font-semibold tabular-nums text-slate-900 dark:text-slate-100">
        {value}
        <span className="ml-1 text-[11px] font-normal text-slate-500 dark:text-slate-400">
          {unit}
        </span>
      </dd>
    </div>
  )
}

export function CompaniesPage() {
  const { t } = useTranslation()
  const fmt = useFormatters()
  const [search, setSearch] = useState('')
  const [visibleCount, setVisibleCount] = useState(9)
  const [sortKey, setSortKey] = useState<SortKey>('report_year')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [deleteFeedback, setDeleteFeedback] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data: companies = [], isLoading, error } = useQuery({
    queryKey: ['companies'],
    queryFn: listCompanies,
  })

  const deleteMutation = useMutation({
    mutationFn: ({ name, year }: { name: string; year: number }) =>
      deleteCompany(name, year),
    onSuccess: () => {
      setDeleteFeedback(t('companies.deleteSuccess'))
      queryClient.invalidateQueries({ queryKey: ['companies'] })
    },
    onError: () => {
      setDeleteFeedback(null)
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
    setDeleteFeedback(null)
    if (
      confirm(
        t('companies.deleteConfirm', { name: c.company_name, year: c.report_year })
      )
    ) {
      deleteMutation.mutate({ name: c.company_name, year: c.report_year })
    }
  }

  return (
    <PageContainer>
      <PageHeader
        title={t('companies.title')}
        subtitle={t('companies.subtitle')}
        kpis={[
          {
            label: t('companies.summaryCompanies'),
            // Distinct companies. This counted `filtered.length` — company-year
            // rows — so two companies across five report years read as "5".
            value: new Set(filtered.map((company) => company.company_name)).size,
          },
          { label: t('companies.summaryYears'), value: new Set(filtered.map((company) => company.report_year)).size },
          { label: t('companies.summaryRows'), value: companies.length },
        ]}
      />
      {isBackendOffline(error) ? (
        <NoticeBanner
          tone="info"
          title={t('dashboard.backendOfflineTitle')}
          className="max-w-2xl"
        >
          {t('dashboard.backendOfflineBody')}
        </NoticeBanner>
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
      {deleteFeedback ? (
        <NoticeBanner tone="success">
          {deleteFeedback}
        </NoticeBanner>
      ) : null}

      <FilterBar>
        <FilterBar.Field label={t('common.search')} htmlFor="companies-search">
          <div className="relative">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            />
            <Input
              id="companies-search"
              className="pl-8"
              placeholder={t('companies.searchPlaceholder')}
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setVisibleCount(9)
              }}
            />
          </div>
        </FilterBar.Field>
        <FilterBar.Actions>
          <div className="flex flex-wrap gap-2">
            {SORT_OPTIONS.map((option) => (
              <SortButton
                key={option.key}
                label={t(option.labelKey)}
                active={sortKey === option.key}
                direction={sortDir}
                onClick={() => toggleSort(option.key)}
              />
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => exportCompaniesCSV(filtered)}
              aria-label={t('companies.csvExport')}
            >
              <Download size={14} className="mr-1 shrink-0" />
              {t('companies.csvExport')}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => exportToJSON(filtered, `esg-companies-${new Date().toISOString().slice(0, 10)}.json`)}
              aria-label={t('companies.jsonExport')}
            >
              <Download size={14} className="mr-1 shrink-0" />
              {t('companies.jsonExport')}
            </Button>
          </div>
        </FilterBar.Actions>
      </FilterBar>

      <Panel>
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
                  className="group relative overflow-hidden transition-all duration-200 focus-within:border-amber-400 hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-[0_24px_56px_-34px_rgba(15,23,42,0.36)]"
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
                            <h2 className="text-lg font-semibold leading-tight text-slate-900 wrap-break-word">
                              {/* The card used to be a div with onClick: clickable
                                  with a mouse, invisible to the keyboard and to
                                  screen readers. The link carries the semantics
                                  and stretches over the whole card. */}
                              <Link
                                to={`/companies/${encodeURIComponent(c.company_name)}`}
                                className="rounded-xs after:absolute after:inset-0 after:content-[''] focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-amber-600"
                              >
                                {c.company_name}
                              </Link>
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
                        /* Stays above the stretched link, and stays reachable
                           without a hover — it was `opacity-0` until hover, so on
                           touch and by keyboard it could not be found at all. */
                        className="relative z-10 shrink-0 rounded-xl text-red-500 opacity-60 transition-opacity hover:text-red-700 hover:opacity-100 focus-visible:opacity-100 group-hover:opacity-100"
                        onClick={() => handleDelete(c)}
                        aria-label={t('companies.deleteConfirm', { name: c.company_name, year: c.report_year })}
                        title={t('common.delete')}
                      >
                        <Trash2 size={14} aria-hidden="true" />
                      </Button>
                    </div>

                    <dl className="space-y-1.5 rounded-2xl border border-slate-200 bg-slate-50/90 px-4 py-3 dark:border-slate-700 dark:bg-slate-900/40">
                      <CompanyMetricRow
                        label={t('companies.metricScope1Short')}
                        value={fmt.number(c.scope1_co2e_tonnes)}
                        unit={UNITS.tco2e}
                      />
                      <CompanyMetricRow
                        label={t('companies.metricEmployeesShort')}
                        value={fmt.number(c.total_employees)}
                        unit={t('companies.unitPeople')}
                      />
                      {/* `fixed` so the column reads 41,0 / 25,0 / 19,5 rather
                          than 41 / 25 / 19,5 — a percentage column with a
                          drifting decimal count does not line up. */}
                      <CompanyMetricRow
                        label={t('companies.metricTaxonomyShort')}
                        value={fmt.number(c.taxonomy_aligned_revenue_pct, {
                          fractionDigits: 1,
                          fixed: true,
                        })}
                        unit={UNITS.percent}
                      />
                    </dl>
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
      </Panel>
    </PageContainer>
  )
}

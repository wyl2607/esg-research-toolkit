import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listCompanies } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { CompareTablePanel } from '@/components/compare/CompareTablePanel'
import { InfoTooltip } from '@/components/InfoTooltip'
import { QueryStateCard } from '@/components/QueryStateCard'
import { PageContainer } from '@/components/layout/PageContainer'
import { PageHeader } from '@/components/layout/PageHeader'
import { FormCard } from '@/components/layout/Panel'
import { NoticeBanner } from '@/components/NoticeBanner'
import { FilterBar } from '@/components/FilterBar'
import type { CompanyESGData } from '@/lib/types'
import { useTranslation } from 'react-i18next'
import { localizeErrorMessage } from '@/lib/error-utils'
import { cn } from '@/lib/utils'

type ViewMode = 'absolute' | 'intensity' | 'rank'
type SelectedEntry = { name: string; year: number }

export function ComparePage() {
  const { t, i18n } = useTranslation()
  const locale = i18n.resolvedLanguage ?? 'en'
  const [selected, setSelected] = useState<SelectedEntry[]>([])
  const [viewMode, setViewMode] = useState<ViewMode>('absolute')
  const {
    data: companies = [],
    isLoading,
    error,
    refetch,
  } = useQuery({ queryKey: ['companies'], queryFn: listCompanies })

  const uniqueCompanyNames = [...new Set(companies.map((c) => c.company_name))].sort()
  const yearsForCompany = (name: string): number[] =>
    companies.filter((c) => c.company_name === name).map((c) => c.report_year).sort((a, b) => a - b)
  const isCompanySelected = (name: string) => selected.some((s) => s.name === name)

  const toggleCompany = (name: string) => {
    if (isCompanySelected(name)) {
      setSelected((prev) => prev.filter((s) => s.name !== name))
    } else if (selected.length < 4) {
      const years = yearsForCompany(name)
      setSelected((prev) => [...prev, { name, year: years[years.length - 1] }])
    }
  }
  const setYear = (name: string, year: number) =>
    setSelected((prev) => prev.map((s) => (s.name === name ? { ...s, year } : s)))

  const selectedCompanies: CompanyESGData[] = selected
    .map(({ name, year }) => companies.find((c) => c.company_name === name && c.report_year === year))
    .filter(Boolean) as CompanyESGData[]

  const viewModes: { key: ViewMode; label: string }[] = [
    { key: 'absolute', label: t('compare.modeAbsolute') },
    { key: 'intensity', label: t('compare.modeIntensity') },
    { key: 'rank', label: t('compare.modeRank') },
  ]

  return (
    <PageContainer>
      <PageHeader
        title={t('compare.title')}
        subtitle={t('compare.subtitle')}
      />

      {error ? (
        <QueryStateCard
          tone="error"
          title={t('common.error')}
          body={localizeErrorMessage(t, error, 'common.error')}
          actionLabel={t('errorBoundary.retry')}
          onAction={() => void refetch()}
          className="max-w-2xl"
        />
      ) : null}
      {isLoading ? (
        <QueryStateCard
          tone="loading"
          title={t('common.loading')}
          body={t('compare.subtitle')}
          className="max-w-2xl"
        />
      ) : null}
      {!isLoading && !error && companies.length === 0 ? (
        <QueryStateCard
          tone="empty"
          title={t('common.noData')}
          body={t('dashboard.noCompanies')}
          className="max-w-2xl"
        />
      ) : null}

      <FilterBar>
        <FilterBar.Field
          label={(
            <span className="flex items-center gap-2">
              <span>{t('compare.selectUp4')}</span>
              <span
                className={cn(
                  'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium normal-case tracking-normal',
                  selected.length >= 2
                    ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
                    : 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
                )}
                aria-live="polite"
              >
                {selected.length}/4
              </span>
            </span>
          )}
        >
          <div className="flex flex-wrap gap-3">
            {uniqueCompanyNames.map((name) => {
              const isSelected = isCompanySelected(name)
              const entry = selected.find((s) => s.name === name)
              const years = yearsForCompany(name)
              const disabled = !isSelected && selected.length >= 4
              return (
                <div key={name} className="flex flex-col gap-1.5">
                  <Button
                    variant={isSelected ? 'default' : 'outline'}
                    size="sm"
                    className={cn(
                      'h-auto whitespace-normal px-3 py-2 text-left leading-5 transition-all active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-600',
                      isSelected && 'ring-2 ring-amber-200 dark:ring-amber-900/60',
                      disabled && 'opacity-40 cursor-not-allowed',
                    )}
                    onClick={() => !disabled && toggleCompany(name)}
                    aria-pressed={isSelected}
                  >
                    {name}
                  </Button>
                  {isSelected && years.length > 1 && (
                    <div className="flex flex-wrap gap-1 pl-1">
                      {years.map((year) => (
                        <button
                          key={year}
                          type="button"
                          onClick={() => setYear(name, year)}
                          className={cn(
                            'px-2 py-0.5 text-xs rounded-full border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-600',
                            year === entry?.year
                              ? 'bg-amber-100 border-amber-300 text-amber-900 font-semibold dark:bg-amber-900/40 dark:border-amber-600 dark:text-amber-300'
                              : 'bg-white border-stone-200 text-stone-600 hover:bg-stone-50 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-600'
                          )}
                        >
                          {year}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </FilterBar.Field>
        <FilterBar.Actions>
          <Button
            type="button"
            className="rounded-xl bg-amber-700 px-5 py-2.5 text-white hover:bg-amber-800 disabled:bg-slate-200 disabled:text-slate-500 dark:bg-amber-800 dark:hover:bg-amber-900"
            disabled={selectedCompanies.length < 2}
            onClick={() => {
              const el = document.getElementById('compare-results')
              el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
            }}
          >
            {t('compare.startCta', { defaultValue: 'Vergleich starten' })}
          </Button>
        </FilterBar.Actions>
      </FilterBar>

      {selectedCompanies.length >= 2 ? (
        <div id="compare-results" className="space-y-8">
          <FilterBar>
            <FilterBar.Field label={t('compare.viewMode')}>
              <div className="flex w-fit overflow-hidden rounded-xl border border-stone-200 dark:border-slate-600">
                {viewModes.map((m) => (
                  <button
                    key={m.key}
                    type="button"
                    onClick={() => setViewMode(m.key)}
                    className={cn(
                      'px-3 py-1.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-600',
                      viewMode === m.key
                        ? 'bg-amber-700 text-white dark:bg-amber-800'
                        : 'bg-white text-slate-600 hover:bg-stone-50 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
                    )}
                    style={{ minHeight: 'unset', minWidth: 'unset' }}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            </FilterBar.Field>
            {viewMode === 'intensity' && (
              <FilterBar.Field>
                <span className="text-xs text-slate-500 dark:text-slate-400 italic">
                  <InfoTooltip content={t('compare.tooltips.intensity')} />
                  {' '}{t('compare.intensityUnit')}
                </span>
              </FilterBar.Field>
            )}
          </FilterBar>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {selectedCompanies.map((company) => (
              <FormCard key={`${company.company_name}-${company.report_year}`} className="space-y-3">
                <div className="space-y-2">
                  <p className="section-kicker">{t('common.company')}</p>
                  <h2 className="text-lg leading-snug text-slate-900 dark:text-slate-100 break-words">{company.company_name}</h2>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="secondary" className="bg-stone-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200">
                      {company.report_year}
                    </Badge>
                    {company.source_document_type && (
                      <Badge variant="secondary" className="bg-amber-100 text-amber-900 dark:bg-amber-900/30 dark:text-amber-300">
                        {company.source_document_type}
                      </Badge>
                    )}
                  </div>
                </div>
                <div className="grid gap-2 text-sm">
                  {[
                    { key: 'scope1', val: company.scope1_co2e_tonnes, unit: 'tCO₂e', tooltipKey: 'scope1' },
                    { key: 'renewable', val: company.renewable_energy_pct != null ? `${company.renewable_energy_pct.toFixed(1)}%` : null, unit: '', tooltipKey: 'renewable' },
                  ].map(({ key, val, unit, tooltipKey }) => (
                    <div key={key} className="rounded-xl border border-stone-200 dark:border-slate-600 bg-white/80 dark:bg-slate-700/60 px-3 py-2 min-w-0">
                      <div className="flex items-center gap-1 text-xs uppercase tracking-wide text-stone-500 dark:text-slate-400">
                        {key === 'scope1' ? t('companies.metricScope1Short') : t('compare.renewable')}
                        <InfoTooltip content={t(`compare.tooltips.${tooltipKey}`)} />
                      </div>
                      <div className="mt-1 numeric-mono text-base font-semibold text-slate-900 dark:text-slate-100 break-all leading-tight">
                        {val != null ? `${typeof val === 'number' ? val.toLocaleString(locale) : val}` : '—'}
                        {unit && val != null && <span className="ml-1 text-xs font-normal text-stone-500 dark:text-slate-400">{unit}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </FormCard>
            ))}
          </div>

          <CompareTablePanel
            selectedCompanies={selectedCompanies}
            viewMode={viewMode}
            locale={locale}
          />
        </div>
      ) : (
        <NoticeBanner tone="info" title={t('compare.noSelectionHeadline')}>
          <ul className="mt-2 space-y-2 text-sm text-slate-600 dark:text-slate-300">
            <li className="flex items-center justify-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500" aria-hidden="true" />
              {t('compare.noSelectionBullet1')}
            </li>
            <li className="flex items-center justify-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500" aria-hidden="true" />
              {t('compare.noSelectionBullet2')}
            </li>
            <li className="flex items-center justify-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500" aria-hidden="true" />
              {t('compare.noSelectionBullet3')}
            </li>
          </ul>
          <div className="mt-6 grid grid-cols-3 gap-4" aria-hidden="true">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 rounded-xl border border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800" />
            ))}
          </div>
        </NoticeBanner>
      )}
    </PageContainer>
  )
}

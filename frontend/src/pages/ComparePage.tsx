import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listCompanies } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { InfoTooltip } from '@/components/InfoTooltip'
import { QueryStateCard } from '@/components/QueryStateCard'
import type { CompanyESGData } from '@/lib/types'
import { useTranslation } from 'react-i18next'
import { localizeErrorMessage } from '@/lib/error-utils'
import { cn } from '@/lib/utils'

type ViewMode = 'absolute' | 'intensity' | 'rank'
type SelectedEntry = { name: string; year: number }

// For each row: is higher better?
type RowDef = {
  key: string
  label: string
  tooltipKey: string
  unit?: string
  higherIsBetter: boolean
  getValue: (c: CompanyESGData) => number | null
  format: (v: number | null, locale: string, mode: ViewMode, employees: number | null) => string
}

function intensityVal(v: number | null, employees: number | null): number | null {
  if (v == null || employees == null || employees === 0) return null
  return v / employees
}

function fmtNum(v: number | null, locale: string, decimals = 1): string {
  if (v == null) return '—'
  return v.toLocaleString(locale, { maximumFractionDigits: decimals, minimumFractionDigits: 0 })
}

function RelativeBar({ value, min, max, higherIsBetter }: {
  value: number | null; min: number; max: number; higherIsBetter: boolean
}) {
  if (value == null || max === min) return null
  const pct = ((value - min) / (max - min)) * 100
  const goodPct = higherIsBetter ? pct : 100 - pct
  const barClass = goodPct >= 67 ? 'bg-emerald-400' : goodPct >= 34 ? 'bg-amber-400' : 'bg-red-400'
  return (
    <div className="mt-1.5 h-1.5 w-full rounded-full bg-stone-100 dark:bg-slate-600">
      <div
        className={cn('h-1.5 rounded-full transition-all', barClass)}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

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

  const rows: RowDef[] = [
    {
      key: 'scope1',
      label: t('companies.scope1'),
      tooltipKey: 'scope1',
      unit: 'tCO₂e',
      higherIsBetter: false,
      getValue: (c) => c.scope1_co2e_tonnes,
      format: (v, loc, mode, emp) => {
        if (mode === 'intensity') return fmtNum(intensityVal(v, emp), loc, 2)
        return fmtNum(v, loc, 0)
      },
    },
    {
      key: 'scope2',
      label: t('companies.scope2') ?? 'Scope 2 (tCO₂e)',
      tooltipKey: 'scope2',
      unit: 'tCO₂e',
      higherIsBetter: false,
      getValue: (c) => c.scope2_co2e_tonnes,
      format: (v, loc, mode, emp) => {
        if (mode === 'intensity') return fmtNum(intensityVal(v, emp), loc, 2)
        return fmtNum(v, loc, 0)
      },
    },
    {
      key: 'scope3',
      label: t('companies.scope3') ?? 'Scope 3 (tCO₂e)',
      tooltipKey: 'scope3',
      unit: 'tCO₂e',
      higherIsBetter: false,
      getValue: (c) => c.scope3_co2e_tonnes,
      format: (v, loc, mode, emp) => {
        if (mode === 'intensity') return fmtNum(intensityVal(v, emp), loc, 2)
        return fmtNum(v, loc, 0)
      },
    },
    {
      key: 'revenueAligned',
      label: t('compare.revenueAligned'),
      tooltipKey: 'revenueAligned',
      unit: '%',
      higherIsBetter: true,
      getValue: (c) => c.taxonomy_aligned_revenue_pct,
      format: (v) => (v != null ? `${v.toFixed(1)}%` : '—'),
    },
    {
      key: 'renewable',
      label: t('compare.renewable'),
      tooltipKey: 'renewable',
      unit: '%',
      higherIsBetter: true,
      getValue: (c) => c.renewable_energy_pct,
      format: (v) => (v != null ? `${v.toFixed(1)}%` : '—'),
    },
    {
      key: 'employees',
      label: t('companies.employees'),
      tooltipKey: 'intensity',
      unit: t('companies.unitPeople'),
      higherIsBetter: true,
      getValue: (c) => c.total_employees,
      format: (v, loc) => fmtNum(v, loc, 0),
    },
    {
      key: 'waterUsage',
      label: t('compare.waterUsage'),
      tooltipKey: 'waterUsage',
      unit: 'm³',
      higherIsBetter: false,
      getValue: (c) => c.water_usage_m3,
      format: (v, loc, mode, emp) => {
        if (mode === 'intensity') return fmtNum(intensityVal(v, emp), loc, 1)
        return fmtNum(v, loc, 0)
      },
    },
    {
      key: 'femalePct',
      label: t('compare.femalePct'),
      tooltipKey: 'femalePct',
      unit: '%',
      higherIsBetter: true,
      getValue: (c) => c.female_pct,
      format: (v) => (v != null ? `${v.toFixed(1)}%` : '—'),
    },
  ]

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

  // Compute effective value per row per company (handles intensity mode)
  const effectiveVal = (row: RowDef, c: CompanyESGData): number | null => {
    const raw = row.getValue(c)
    if (viewMode === 'intensity' && (row.key === 'scope1' || row.key === 'scope2' || row.key === 'scope3' || row.key === 'waterUsage')) {
      return intensityVal(raw, c.total_employees)
    }
    return raw
  }

  // Rank: 1 = best
  const rankFor = (row: RowDef, c: CompanyESGData): number => {
    const vals = selectedCompanies
      .map((sc) => effectiveVal(row, sc))
      .filter((v): v is number => v != null)
    const myVal = effectiveVal(row, c)
    if (myVal == null) return selectedCompanies.length + 1
    const sorted = [...vals].sort((a, b) => row.higherIsBetter ? b - a : a - b)
    return sorted.indexOf(myVal) + 1
  }

  const minMax = (row: RowDef) => {
    const vals = selectedCompanies.map((c) => effectiveVal(row, c)).filter((v): v is number => v != null)
    return { min: Math.min(...vals), max: Math.max(...vals) }
  }

  const isBest = (row: RowDef, c: CompanyESGData) => {
    const vals = selectedCompanies.map((sc) => effectiveVal(row, sc)).filter((v): v is number => v != null)
    if (vals.length < 2) return false
    const myVal = effectiveVal(row, c)
    if (myVal == null) return false
    return row.higherIsBetter ? myVal === Math.max(...vals) : myVal === Math.min(...vals)
  }
  const isWorst = (row: RowDef, c: CompanyESGData) => {
    const vals = selectedCompanies.map((sc) => effectiveVal(row, sc)).filter((v): v is number => v != null)
    if (vals.length < 2) return false
    const myVal = effectiveVal(row, c)
    if (myVal == null) return false
    return row.higherIsBetter ? myVal === Math.min(...vals) : myVal === Math.max(...vals)
  }

  const viewModes: { key: ViewMode; label: string }[] = [
    { key: 'absolute', label: t('compare.modeAbsolute') },
    { key: 'intensity', label: t('compare.modeIntensity') },
    { key: 'rank', label: t('compare.modeRank') },
  ]

  return (
    <div className="space-y-8">
      <section className="editorial-panel space-y-3 p-5 md:p-6">
        <p className="section-kicker">{t('compare.kicker')}</p>
        <div>
          <h1 className="text-4xl text-slate-900 dark:text-slate-100">{t('compare.title')}</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
            {t('compare.subtitle')}
          </p>
        </div>
      </section>

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

      {/* Company + year selector */}
      <div className="surface-card p-5">
        <p className="mb-3 text-sm text-slate-500 dark:text-slate-400">{t('compare.selectUp4')}</p>
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
                  className={cn('h-auto whitespace-normal px-3 py-2 text-left leading-5', disabled && 'opacity-40 cursor-not-allowed')}
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
      </div>

      {selectedCompanies.length >= 2 ? (
        <div className="space-y-8">
          {/* View mode toggle */}
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-xs font-semibold uppercase tracking-wide text-stone-500 dark:text-slate-400">
              {t('compare.viewMode')}
            </span>
            <div className="flex rounded-xl border border-stone-200 dark:border-slate-600 overflow-hidden">
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
            {viewMode === 'intensity' && (
              <span className="text-xs text-slate-500 dark:text-slate-400 italic">
                <InfoTooltip content={t('compare.tooltips.intensity')} />
                {' '}{t('compare.intensityUnit')}
              </span>
            )}
          </div>

          {/* Company header cards */}
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {selectedCompanies.map((company) => (
              <div key={`${company.company_name}-${company.report_year}`} className="surface-card space-y-3 p-4">
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
              </div>
            ))}
          </div>

          {/* Full comparison table */}
          <div className="editorial-panel p-0 overflow-hidden">
            <div className="px-5 pt-5 pb-3">
              <h2 className="text-2xl text-slate-900 dark:text-slate-100">{t('compare.tableTitle')}</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="editorial-table-header">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-300 min-w-[160px]">
                      {t('common.summary')}
                    </th>
                    {selectedCompanies.map((c) => (
                      <th
                        key={`${c.company_name}${c.report_year}`}
                        className="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-300 min-w-[140px]"
                      >
                        <div className="break-words leading-snug">{c.company_name}</div>
                        <div className="text-xs font-normal text-stone-400 dark:text-slate-500">{c.report_year}</div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => {
                    const { min, max } = minMax(row)
                    return (
                      <tr key={row.key} className="border-b border-stone-200 dark:border-slate-600 last:border-0 hover:bg-stone-50/50 dark:hover:bg-slate-700/30 transition-colors">
                        <td className="px-4 py-3 font-medium text-slate-700 dark:text-slate-200">
                          <div className="flex flex-wrap items-center gap-1">
                            <span>{row.label}</span>
                            <InfoTooltip content={t(`compare.tooltips.${row.tooltipKey}`)} />
                            {row.unit && viewMode !== 'rank' && (
                              <span className="metric-unit">
                                {viewMode === 'intensity' && (row.key === 'scope1' || row.key === 'scope2' || row.key === 'scope3' || row.key === 'waterUsage')
                                  ? `${row.unit}/${t('compare.intensityUnit')}`
                                  : row.unit}
                              </span>
                            )}
                          </div>
                        </td>
                        {selectedCompanies.map((c) => {
                          const effVal = effectiveVal(row, c)
                          const best = isBest(row, c)
                          const worst = isWorst(row, c)
                          const rank = viewMode === 'rank' ? rankFor(row, c) : null
                          const displayText = viewMode === 'rank'
                            ? (effVal != null ? `#${rank}` : '—')
                            : row.format(row.getValue(c), locale, viewMode, c.total_employees)

                          return (
                            <td
                              key={`${c.company_name}${c.report_year}`}
                              className={cn(
                                'px-4 py-3 transition-colors',
                                best && 'bg-emerald-50/60 dark:bg-emerald-900/20',
                                worst && 'bg-red-50/60 dark:bg-red-900/20'
                              )}
                            >
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className={cn(
                                  'numeric-mono font-semibold text-slate-900 dark:text-slate-100 break-all',
                                  best && 'text-emerald-700 dark:text-emerald-400',
                                  worst && 'text-red-600 dark:text-red-400'
                                )}>
                                  {displayText}
                                </span>
                                {best && (
                                  <span className="text-[10px] font-semibold uppercase tracking-wide text-emerald-600 dark:text-emerald-400">
                                    {t('compare.bestLabel')}
                                  </span>
                                )}
                                {worst && (
                                  <span className="text-[10px] font-semibold uppercase tracking-wide text-red-500 dark:text-red-400">
                                    {t('compare.worstLabel')}
                                  </span>
                                )}
                              </div>
                              {viewMode !== 'rank' && min !== max && (
                                <RelativeBar value={effVal} min={min} max={max} higherIsBetter={row.higherIsBetter} />
                              )}
                            </td>
                          )
                        })}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        <p className="py-12 text-center text-slate-400 dark:text-slate-500">{t('compare.noSelection')}</p>
      )}
    </div>
  )
}

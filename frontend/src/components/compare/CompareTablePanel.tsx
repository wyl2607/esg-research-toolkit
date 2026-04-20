import { useTranslation } from 'react-i18next'

import { InfoTooltip } from '@/components/InfoTooltip'
import { Panel } from '@/components/layout/Panel'
import type { CompanyESGData } from '@/lib/types'
import { cn } from '@/lib/utils'

type ViewMode = 'absolute' | 'intensity' | 'rank'

type RowDef = {
  key: string
  label: string
  tooltipKey: string
  unit?: string
  higherIsBetter: boolean
  getValue: (c: CompanyESGData) => number | null
  format: (v: number | null, locale: string, mode: ViewMode, employees: number | null) => string
}

interface CompareTablePanelProps {
  selectedCompanies: CompanyESGData[]
  viewMode: ViewMode
  locale: string
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

export function CompareTablePanel({
  selectedCompanies,
  viewMode,
  locale,
}: CompareTablePanelProps) {
  const { t } = useTranslation()

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

  return (
    <Panel title={t('compare.tableTitle')} className="overflow-hidden">
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
    </Panel>
  )
}

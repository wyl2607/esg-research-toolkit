import { useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listCompanies } from '@/lib/api'
import { FIELD_CONFIG_MAP } from '@/lib/coverage-field-config'
import { QueryStateCard } from '@/components/QueryStateCard'
import { ArrowLeft, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import type { CompanyESGData } from '@/lib/types'

interface RankedRow {
  company: CompanyESGData
  value: number | null
  achievement: number | null   // value / target * 100, or null if no target
}

function AchievementBadge({ pct }: { pct: number }) {
  if (pct >= 100) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">
        <TrendingUp size={11} />
        {pct.toFixed(1)}% ✓
      </span>
    )
  }
  if (pct >= 50) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-semibold text-yellow-700">
        <Minus size={11} />
        {pct.toFixed(1)}%
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">
      <TrendingDown size={11} />
      {pct.toFixed(1)}%
    </span>
  )
}

export function CoverageFieldPage() {
  const { field = '' } = useParams<{ field: string }>()
  const config = FIELD_CONFIG_MAP[field]

  const { data: companies = [], isLoading, error } = useQuery({
    queryKey: ['companies'],
    queryFn: listCompanies,
  })

  const rows = useMemo<RankedRow[]>(() => {
    if (!config) return []

    const mapped: RankedRow[] = companies.map((c) => {
      const raw = c[config.field as keyof CompanyESGData]
      const value = typeof raw === 'number' ? raw : null
      const achievement =
        value !== null && config.target !== null
          ? (value / config.target) * 100
          : null
      return { company: c, value, achievement }
    })

    // sort: data rows first, then no-data; within data rows respect higherIsBetter
    const withData = mapped
      .filter((r) => r.value !== null)
      .sort((a, b) =>
        config.higherIsBetter
          ? (b.value ?? 0) - (a.value ?? 0)
          : (a.value ?? 0) - (b.value ?? 0)
      )
    const noData = mapped.filter((r) => r.value === null)

    return [...withData, ...noData]
  }, [companies, config])

  if (!config) {
    return (
      <div className="space-y-4">
        <Link to="/" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
          <ArrowLeft size={14} /> 返回仪表盘
        </Link>
        <QueryStateCard tone="error" title="未知字段" body={`字段 "${field}" 不存在`} />
      </div>
    )
  }

  const withDataCount = rows.filter((r) => r.value !== null).length
  const overTargetCount =
    config.target !== null
      ? rows.filter((r) => r.achievement !== null && r.achievement >= 100).length
      : 0

  return (
    <div className="space-y-6">
      {/* back + header */}
      <div className="space-y-2">
        <Link
          to="/"
          className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-amber-700"
        >
          <ArrowLeft size={14} /> 返回仪表盘
        </Link>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="section-kicker">数据覆盖率 · 字段详情</p>
            <h1 className="text-3xl font-semibold text-slate-900">{config.label}</h1>
            <p className="mt-1 text-sm text-slate-500">
              单位：{config.unit} · {config.higherIsBetter ? '越高越好' : '越低越好'}
              {config.target !== null && ` · 目标：${config.format(config.target)}`}
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <div className="rounded-xl border border-stone-200 bg-white px-4 py-2 text-center shadow-sm">
              <p className="text-xl font-semibold text-slate-900">{withDataCount}</p>
              <p className="text-xs text-slate-500">有数据公司</p>
            </div>
            {config.target !== null && (
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-center shadow-sm">
                <p className="text-xl font-semibold text-emerald-700">{overTargetCount}</p>
                <p className="text-xs text-emerald-600">达成或超过目标</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* table */}
      {isLoading ? (
        <QueryStateCard tone="loading" title="加载中…" body="正在读取公司数据" />
      ) : error ? (
        <QueryStateCard tone="error" title="加载失败" body="无法读取公司列表" />
      ) : (
        <div className="editorial-panel overflow-hidden">
          {/* desktop table */}
          <div className="hidden overflow-x-auto md:block">
            <table className="min-w-[640px] w-full text-sm">
              <thead className="border-b editorial-table-header">
                <tr>
                  <th className="w-8 px-4 py-3 text-left font-medium text-slate-500">#</th>
                  <th className="px-4 py-3 text-left font-medium text-slate-600">公司</th>
                  <th className="px-4 py-3 text-left font-medium text-slate-600">年份</th>
                  <th className="px-4 py-3 text-right font-medium text-slate-600">
                    数值 ({config.unit})
                  </th>
                  {config.target !== null && (
                    <>
                      <th className="px-4 py-3 text-right font-medium text-slate-600">
                        目标 ({config.unit})
                      </th>
                      <th className="px-4 py-3 text-right font-medium text-slate-600">
                        达成率
                      </th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, idx) => (
                  <tr
                    key={`${row.company.company_name}-${row.company.report_year}`}
                    className={[
                      'border-b last:border-0',
                      row.value === null ? 'opacity-40' : 'hover:bg-slate-50',
                    ].join(' ')}
                  >
                    <td className="px-4 py-3 text-xs text-slate-400">
                      {row.value !== null ? idx + 1 : '—'}
                    </td>
                    <td className="px-4 py-3 font-medium">
                      <Link
                        to={`/companies/${encodeURIComponent(row.company.company_name)}`}
                        className="hover:text-amber-700 hover:underline"
                      >
                        {row.company.company_name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-slate-500">{row.company.report_year}</td>
                    <td className="px-4 py-3 text-right font-mono">
                      {row.value !== null ? config.format(row.value) : <span className="text-slate-300">无数据</span>}
                    </td>
                    {config.target !== null && (
                      <>
                        <td className="px-4 py-3 text-right text-slate-400">
                          {config.format(config.target)}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {row.achievement !== null ? (
                            <AchievementBadge pct={row.achievement} />
                          ) : (
                            <span className="text-slate-300">—</span>
                          )}
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* mobile cards */}
          <div className="space-y-3 p-4 md:hidden">
            {rows.map((row, idx) => (
              <div
                key={`${row.company.company_name}-${row.company.report_year}`}
                className={[
                  'rounded-xl border border-stone-200 bg-white p-3',
                  row.value === null ? 'opacity-40' : '',
                ].join(' ')}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-xs text-slate-400">
                      {row.value !== null ? `#${idx + 1}` : '—'} · {row.company.report_year}
                    </p>
                    <Link
                      to={`/companies/${encodeURIComponent(row.company.company_name)}`}
                      className="truncate font-medium text-slate-900 hover:text-amber-700"
                    >
                      {row.company.company_name}
                    </Link>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="font-mono text-sm font-semibold text-slate-800">
                      {row.value !== null ? config.format(row.value) : '—'}
                    </p>
                    {row.achievement !== null && (
                      <div className="mt-1">
                        <AchievementBadge pct={row.achievement} />
                      </div>
                    )}
                  </div>
                </div>
                {config.target !== null && row.value !== null && (
                  <div className="mt-2">
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-stone-100">
                      <div
                        className={[
                          'h-1.5 rounded-full transition-all',
                          (row.achievement ?? 0) >= 100
                            ? 'bg-emerald-500'
                            : (row.achievement ?? 0) >= 50
                            ? 'bg-yellow-400'
                            : 'bg-red-400',
                        ].join(' ')}
                        style={{ width: `${Math.min(row.achievement ?? 0, 100)}%` }}
                      />
                    </div>
                    <p className="mt-0.5 text-right text-xs text-slate-400">
                      目标 {config.format(config.target)}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

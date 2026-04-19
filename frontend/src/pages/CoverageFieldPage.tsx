import { useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { listCompanies } from '@/lib/api'
import { FIELD_CONFIG_MAP } from '@/lib/coverage-field-config'
import { QueryStateCard } from '@/components/QueryStateCard'
import { PageContainer } from '@/components/layout/PageContainer'
import { PageHeader } from '@/components/layout/PageHeader'
import { Panel } from '@/components/layout/Panel'
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
  const { t } = useTranslation()
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
      <PageContainer>
        <PageHeader
          title={t('coverageField.unknownTitle')}
          subtitle={t('coverageField.unknownBody', { field })}
          actions={
            <Link to="/" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
              <ArrowLeft size={14} /> {t('coverageField.backToDashboard')}
            </Link>
          }
        />
        <QueryStateCard
          tone="error"
          title={t('coverageField.unknownTitle')}
          body={t('coverageField.unknownBody', { field })}
        />
      </PageContainer>
    )
  }

  const directionLabel = config.higherIsBetter
    ? t('coverageField.directionHigher')
    : t('coverageField.directionLower')
  const fieldLabel = t(`coverageField.labels.${config.field}`, { defaultValue: config.label })
  const withDataCount = rows.filter((r) => r.value !== null).length
  const overTargetCount =
    config.target !== null
      ? rows.filter((r) => r.achievement !== null && r.achievement >= 100).length
      : 0

  return (
    <PageContainer>
      <PageHeader
        title={fieldLabel}
        subtitle={config.target !== null
          ? t('coverageField.subtitleWithTarget', {
              unit: config.unit,
              direction: directionLabel,
              target: config.format(config.target),
            })
          : t('coverageField.subtitleWithoutTarget', {
              unit: config.unit,
              direction: directionLabel,
            })}
        actions={
          <Link to="/" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-amber-700">
            <ArrowLeft size={14} /> {t('coverageField.backToDashboard')}
          </Link>
        }
        kpis={[
          { label: t('coverageField.kpis.withDataCompanies'), value: withDataCount },
          ...(config.target !== null
            ? [{ label: t('coverageField.kpis.onTargetCompanies'), value: overTargetCount }]
            : []),
        ]}
      />

      {isLoading ? (
        <QueryStateCard
          tone="loading"
          title={t('coverageField.states.loadingTitle')}
          body={t('coverageField.states.loadingBody')}
        />
      ) : error ? (
        <QueryStateCard
          tone="error"
          title={t('coverageField.states.errorTitle')}
          body={t('coverageField.states.errorBody')}
        />
      ) : (
        <Panel className="overflow-hidden">
          <div className="hidden overflow-x-auto md:block">
            <table className="min-w-[640px] w-full text-sm">
              <thead className="border-b editorial-table-header">
                <tr>
                  <th className="w-8 px-4 py-3 text-left font-medium text-slate-500">#</th>
                  <th className="px-4 py-3 text-left font-medium text-slate-600">{t('common.company')}</th>
                  <th className="px-4 py-3 text-left font-medium text-slate-600">{t('common.year')}</th>
                  <th className="px-4 py-3 text-right font-medium text-slate-600">
                    {t('coverageField.table.valueWithUnit', { unit: config.unit })}
                  </th>
                  {config.target !== null && (
                    <>
                      <th className="px-4 py-3 text-right font-medium text-slate-600">
                        {t('coverageField.table.targetWithUnit', { unit: config.unit })}
                      </th>
                      <th className="px-4 py-3 text-right font-medium text-slate-600">
                        {t('coverageField.table.achievement')}
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
                      {row.value !== null ? config.format(row.value) : (
                        <span className="text-slate-300">{t('coverageField.table.noData')}</span>
                      )}
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
                      {t('coverageField.mobileTarget', { target: config.format(config.target) })}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Panel>
      )}
    </PageContainer>
  )
}

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listCompanies, getFrameworkComparison } from '@/lib/api'
import type { FrameworkScoreResult, DimensionScore } from '@/lib/types'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { QueryStateCard } from '@/components/QueryStateCard'
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import { useTranslation } from 'react-i18next'
import { localizeErrorMessage, isBackendOffline } from '@/lib/error-utils'
import { BackendOfflineBanner } from '@/components/BackendOfflineBanner'

function GradeBadge({ grade }: { grade: string }) {
  const colors: Record<string, string> = {
    A: 'border-green-300 bg-green-50 text-green-800',
    B: 'border-sky-300 bg-sky-50 text-sky-800',
    C: 'border-amber-300 bg-amber-50 text-amber-800',
    D: 'border-orange-300 bg-orange-50 text-orange-800',
    F: 'border-red-300 bg-red-50 text-red-800',
  }

  return (
    <span
      className={`inline-flex h-10 w-10 items-center justify-center rounded-full border-2 font-bold text-lg ${colors[grade] ?? colors.F}`}
    >
      {grade}
    </span>
  )
}

function ScoreBar({ value, max = 1 }: { value: number; max?: number }) {
  const pct = Math.round((value / max) * 100)
  const color =
    pct >= 80 ? 'bg-green-600' : pct >= 60 ? 'bg-amber-600' : pct >= 40 ? 'bg-orange-500' : 'bg-red-500'

  return (
    <div className="flex items-center gap-2">
      <div className="h-2 flex-1 rounded-full bg-stone-200">
        <div className={`${color} h-2 rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-8 text-right text-xs text-slate-500">{pct}%</span>
    </div>
  )
}

const FRAMEWORK_COLORS: Record<string, string> = {
  eu_taxonomy: '#b45309',
  csrc_2023: '#9a3412',
  csrd: '#3f6212',
}

function FrameworkCard({ fw }: { fw: FrameworkScoreResult }) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)
  const color = FRAMEWORK_COLORS[fw.framework_id] ?? '#b45309'
  const radarData = fw.dimensions.map((d: DimensionScore) => ({
    subject: d.name.split(' ')[0],
    score: Math.round(d.score * 100),
  }))

  return (
    <div className="surface-card space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="mb-1 flex items-center gap-2">
            <span className="inline-block h-3 w-3 rounded-full" style={{ background: color }} />
            <h3 className="font-semibold text-slate-800">{fw.framework}</h3>
          </div>
          <p className="text-xs text-slate-400">{t('frameworks.coverage', { pct: fw.coverage_pct })}</p>
        </div>
        <GradeBadge grade={fw.grade} />
      </div>

      <div>
        <p className="mb-1 text-xs text-slate-500">{t('frameworks.totalScore')}</p>
        <ScoreBar value={fw.total_score} />
      </div>

      <div className="h-44">
        <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
          <RadarChart data={radarData}>
            <PolarGrid />
            <PolarAngleAxis dataKey="subject" tick={{ fontSize: 9 }} tickFormatter={(v: string) => v.length > 8 ? v.slice(0, 7) + '…' : v} />
            <Radar dataKey="score" fill={color} fillOpacity={0.25} stroke={color} strokeWidth={2} />
            <Tooltip formatter={(v) => [`${v}%`, '']} />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div className="space-y-2">
        {fw.dimensions.map((d: DimensionScore) => (
          <div key={d.name}>
            <div className="mb-0.5 flex justify-between text-xs text-slate-600">
              <span>{d.name}</span>
              <span>{t('frameworks.disclosed', { n: d.disclosed, total: d.total })}</span>
            </div>
            <ScoreBar value={d.score} />
          </div>
        ))}
      </div>

      <button
        className="text-xs text-amber-800 hover:underline"
        onClick={() => setExpanded(!expanded)}
        type="button"
      >
        {expanded
          ? t('frameworks.collapse')
          : t('frameworks.viewGaps', {
              count: fw.gaps.length,
              recs: fw.recommendations.length,
            })}
      </button>

      {expanded && (
        <div className="space-y-3 border-t border-stone-200 pt-2">
          {fw.gaps.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-medium text-slate-700">{t('common.gaps')}</p>
              <ul className="space-y-1">
                {fw.gaps.map((g, i) => (
                  <li key={i} className="flex gap-2 text-xs text-slate-600">
                    <Badge variant="outline" className="shrink-0 px-1 text-[10px]">
                      {t('common.missing')}
                    </Badge>
                    {g}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {fw.recommendations.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-medium text-slate-700">
                {t('common.recommendations')}
              </p>
              <ul className="space-y-1">
                {fw.recommendations.map((r, i) => (
                  <li key={i} className="text-xs text-slate-600">
                    • {r}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function FrameworksPage() {
  const { t } = useTranslation()
  const [selected, setSelected] = useState('')

  const {
    data: companies = [],
    isLoading: companiesLoading,
    error: companiesError,
    refetch: refetchCompanies,
  } = useQuery({
    queryKey: ['companies'],
    queryFn: listCompanies,
  })

  const [companyName, companyYear] = selected ? selected.split('|') : [null, null]

  const { data: report, isLoading, error: reportError, refetch: refetchReport } = useQuery({
    queryKey: ['frameworks', companyName, companyYear],
    queryFn: () => getFrameworkComparison(companyName!, Number(companyYear)),
    enabled: !!companyName && !!companyYear,
  })

  const backendOffline = isBackendOffline(companiesError) || isBackendOffline(reportError)

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <p className="section-kicker">{t('frameworks.kicker')}</p>
        <h1 className="text-3xl font-semibold text-slate-900">{t('frameworks.title')}</h1>
        <p className="max-w-3xl text-sm leading-6 text-slate-600">
          {t('frameworks.subtitle')}
        </p>
      </div>

      {backendOffline ? (
        <BackendOfflineBanner />
      ) : (companiesError || reportError) ? (
        <QueryStateCard
          tone="error"
          title={t('common.error')}
          body={localizeErrorMessage(t, reportError ?? companiesError, 'common.error')}
          actionLabel={t('errorBoundary.retry')}
          onAction={() => {
            if (reportError) void refetchReport()
            else void refetchCompanies()
          }}
          className="max-w-2xl"
        />
      ) : null}

      {companiesLoading ? (
        <QueryStateCard
          tone="loading"
          title={t('common.loading')}
          body={t('frameworks.subtitle')}
          className="max-w-2xl"
        />
      ) : null}

      <div className="surface-card max-w-xl">
        <p id="frameworks-company-select-label" className="mb-3 text-xs uppercase tracking-[0.2em] text-stone-500">
          {t('common.company')} & {t('common.year')}
        </p>
        <Select value={selected} onValueChange={setSelected}>
          <SelectTrigger
            className="w-full border-stone-300 bg-white/90"
            aria-label={t('common.selectCompany')}
            aria-labelledby="frameworks-company-select-label"
          >
            <SelectValue placeholder={t('common.selectCompany')} />
          </SelectTrigger>
          <SelectContent>
            {companies.map((c) => (
              <SelectItem
                key={`${c.company_name}|${c.report_year}`}
                value={`${c.company_name}|${c.report_year}`}
              >
                {c.company_name} ({c.report_year})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {companies.length === 0 && !companiesLoading && !companiesError && !backendOffline ? (
        <QueryStateCard
          tone="empty"
          title={t('common.noData')}
          body={t('dashboard.noCompanies')}
          className="max-w-2xl"
        />
      ) : null}

      {isLoading ? (
        <QueryStateCard
          tone="loading"
          title={t('common.loading')}
          body={t('frameworks.calculating')}
          className="max-w-2xl"
        />
      ) : null}

      {report && (
        <div className="space-y-4">
          <div className="rounded-2xl border border-amber-200 bg-amber-50/90 px-5 py-4 text-sm leading-6 text-amber-900">
            {report.summary}
          </div>

          <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
            {report.frameworks.map((fw) => (
              <FrameworkCard key={fw.framework_id} fw={fw} />
            ))}
          </div>
        </div>
      )}

      {!selected && companies.length > 0 ? (
        <QueryStateCard
          tone="empty"
          title={t('common.selectCompany')}
          body={t('frameworks.selectPrompt')}
          className="max-w-2xl py-8"
        />
      ) : null}
    </div>
  )
}

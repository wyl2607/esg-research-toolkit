import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listCompaniesWithYearCoverage, getFrameworkComparison } from '@/lib/api'
import type { FrameworkScoreResult, DimensionScore } from '@/lib/types'
import { CompanyYearPicker, type CompanyYearSelection } from '@/components/CompanyYearPicker'
import { Badge } from '@/components/ui/badge'
import { QueryStateCard } from '@/components/QueryStateCard'
import { PageContainer } from '@/components/layout/PageContainer'
import { PageHeader } from '@/components/layout/PageHeader'
import { Panel } from '@/components/layout/Panel'
import { NoticeBanner } from '@/components/NoticeBanner'
import { FilterBar } from '@/components/FilterBar'
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
import { FRAMEWORK_COMPARABILITY, type ComparabilityLevel } from '@/lib/framework-comparability-config'

// ---------------------------------------------------------------------------
// Comparability badge
// ---------------------------------------------------------------------------
const COMPARABILITY_COLORS: Record<ComparabilityLevel, string> = {
  comparable: 'bg-green-100 text-green-800 border-green-300',
  partial: 'bg-amber-100 text-amber-800 border-amber-300',
  not_comparable: 'bg-stone-100 text-stone-500 border-stone-300',
}

function ComparabilityBadge({ level }: { level: ComparabilityLevel }) {
  const { t } = useTranslation()
  const label = t(`frameworks.comparabilityMatrix.${level}`)
  return (
    <span
      className={`inline-block rounded border px-1.5 py-0.5 text-[10px] font-medium ${COMPARABILITY_COLORS[level]}`}
    >
      {label}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Comparability matrix table
// ---------------------------------------------------------------------------
function ComparabilityMatrixPanel() {
  const { t } = useTranslation()

  return (
    <Panel>
      <div className="mb-2">
        <p className="text-sm font-semibold text-slate-800">
          {t('frameworks.comparabilityMatrix.title')}
        </p>
        <p className="mt-0.5 text-xs text-slate-500">
          {t('frameworks.comparabilityMatrix.subtitle')}
        </p>
      </div>

      {/* Legend */}
      <div className="mb-3 flex flex-wrap gap-3 rounded-md bg-stone-50 p-2 text-xs text-slate-600">
        <span className="font-medium text-slate-700">{t('frameworks.comparabilityMatrix.legend')}:</span>
        <span className="flex items-center gap-1">
          <ComparabilityBadge level="comparable" />
          <span>{t('frameworks.comparabilityMatrix.legendComparable')}</span>
        </span>
        <span className="flex items-center gap-1">
          <ComparabilityBadge level="partial" />
          <span>{t('frameworks.comparabilityMatrix.legendPartial')}</span>
        </span>
        <span className="flex items-center gap-1">
          <ComparabilityBadge level="not_comparable" />
          <span>{t('frameworks.comparabilityMatrix.legendNotComparable')}</span>
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-stone-200 text-slate-500">
              <th className="py-1.5 pr-3 text-left font-medium">
                {t('frameworks.comparabilityMatrix.dimension')}
              </th>
              <th className="py-1.5 pr-2 text-left font-medium" style={{ color: FRAMEWORK_COLORS.eu_taxonomy }}>
                EU Taxonomy
              </th>
              <th className="py-1.5 pr-2 text-left font-medium" style={{ color: FRAMEWORK_COLORS.csrc_2023 }}>
                CSRC 2023
              </th>
              <th className="py-1.5 pr-3 text-left font-medium" style={{ color: FRAMEWORK_COLORS.csrd }}>
                CSRD/ESRS
              </th>
              <th className="py-1.5 text-left font-medium">
                {t('frameworks.comparabilityMatrix.notes')}
              </th>
            </tr>
          </thead>
          <tbody>
            {FRAMEWORK_COMPARABILITY.map((row) => (
              <tr
                key={row.dimensionKey}
                className="border-b border-stone-100 last:border-0"
              >
                <td className="py-2 pr-3 font-medium text-slate-700">
                  {t(`frameworks.dim.${row.labelKey}`, { defaultValue: row.dimensionKey })}
                </td>
                <td className="py-2 pr-2">
                  <ComparabilityBadge level={row.eu_taxonomy} />
                </td>
                <td className="py-2 pr-2">
                  <ComparabilityBadge level={row.csrc_2023} />
                </td>
                <td className="py-2 pr-3">
                  <ComparabilityBadge level={row.csrd} />
                </td>
                <td className="max-w-[240px] py-2 text-slate-500">
                  {t(`frameworks.comparabilityMatrix.dimensionNotes.${row.notesKey}`)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}

// ---------------------------------------------------------------------------
// Score diff explanation — derived purely from API data already returned
// ---------------------------------------------------------------------------
function ScoreDiffPanel({ frameworks }: { frameworks: FrameworkScoreResult[] }) {
  const { t } = useTranslation()

  if (frameworks.length === 0) return null

  const FRAMEWORK_DISPLAY: Record<string, string> = {
    eu_taxonomy: 'EU Taxonomy',
    csrc_2023: 'CSRC 2023',
    csrd: 'CSRD/ESRS',
  }

  const sorted = [...frameworks].sort((a, b) => b.total_score - a.total_score)
  const highest = sorted[0]
  const lowest = sorted[sorted.length - 1]
  const spread = Math.round((highest.total_score - lowest.total_score) * 100)
  const allEqual = spread < 5 // within 5 pp — treat as "similar"

  const lowestCoverage = [...frameworks].sort((a, b) => a.coverage_pct - b.coverage_pct)[0]

  return (
    <Panel>
      <p className="mb-2 text-sm font-semibold text-slate-800">
        {t('frameworks.diffExplanation.title')}
      </p>
      <div className="space-y-1.5 text-xs text-slate-600">
        {allEqual ? (
          <p>{t('frameworks.diffExplanation.allEqual')}</p>
        ) : (
          <>
            <p>
              {t('frameworks.diffExplanation.highestScore', {
                framework: FRAMEWORK_DISPLAY[highest.framework_id] ?? highest.framework,
                score: Math.round(highest.total_score * 100),
              })}
            </p>
            <p>
              {t('frameworks.diffExplanation.lowestScore', {
                framework: FRAMEWORK_DISPLAY[lowest.framework_id] ?? lowest.framework,
                score: Math.round(lowest.total_score * 100),
              })}
            </p>
            <p>
              {t('frameworks.diffExplanation.spread', { spread })}
            </p>
          </>
        )}
        {lowestCoverage.coverage_pct < 80 && (
          <p className="mt-1 text-amber-700">
            {t('frameworks.diffExplanation.coverageGap', {
              framework: FRAMEWORK_DISPLAY[lowestCoverage.framework_id] ?? lowestCoverage.framework,
              pct: Math.round(lowestCoverage.coverage_pct),
            })}
          </p>
        )}
      </div>
    </Panel>
  )
}

// ---------------------------------------------------------------------------
// GradeBadge
// ---------------------------------------------------------------------------
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
    subject: t(`frameworks.dim.${d.name}`, { defaultValue: d.name }).split(' ')[0],
    score: Math.round(d.score * 100),
  }))

  return (
    <Panel className="space-y-4">
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
              <span>{t(`frameworks.dim.${d.name}`, { defaultValue: d.name })}</span>
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
    </Panel>
  )
}

export function FrameworksPage() {
  const { t } = useTranslation()
  const [selection, setSelection] = useState<CompanyYearSelection>({
    company: null,
    year: null,
  })

  const {
    data: companies = [],
    isLoading: companiesLoading,
    error: companiesError,
    refetch: refetchCompanies,
  } = useQuery({
    queryKey: ['companies-v2'],
    queryFn: listCompaniesWithYearCoverage,
  })

  const { data: report, isLoading, error: reportError, refetch: refetchReport } = useQuery({
    queryKey: ['frameworks', selection.company, selection.year],
    queryFn: () => getFrameworkComparison(selection.company!, selection.year!),
    enabled: !!selection.company && !!selection.year,
  })

  const backendOffline = isBackendOffline(companiesError) || isBackendOffline(reportError)

  return (
    <PageContainer>
      <PageHeader title={t('frameworks.title')} subtitle={t('frameworks.subtitle')} />

      {backendOffline ? (
        <NoticeBanner
          tone="info"
          title={t('dashboard.backendOfflineTitle')}
          className="max-w-2xl"
        >
          {t('dashboard.backendOfflineBody')}
        </NoticeBanner>
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

      <FilterBar>
        <FilterBar.Field
          label={`${t('common.company')} & ${t('common.year')}`}
          htmlFor="frameworks-company-year-picker-company"
        >
          <CompanyYearPicker
            idPrefix="frameworks-company-year-picker"
            companies={companies}
            value={selection}
            onChange={setSelection}
          />
        </FilterBar.Field>
      </FilterBar>

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
          <NoticeBanner tone="warning">{report.summary}</NoticeBanner>

          <ScoreDiffPanel frameworks={report.frameworks} />

          <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
            {report.frameworks.map((fw) => (
              <FrameworkCard key={fw.framework_id} fw={fw} />
            ))}
          </div>

          <ComparabilityMatrixPanel />
        </div>
      )}

      {!selection.year && companies.length > 0 ? (
        <QueryStateCard
          tone="empty"
          title={t('common.selectCompany')}
          body={t('frameworks.selectPrompt')}
          className="max-w-2xl py-8"
        />
      ) : null}
    </PageContainer>
  )
}

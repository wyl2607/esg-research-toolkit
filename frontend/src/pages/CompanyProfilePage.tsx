import { lazy, Suspense, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, CheckCircle2, Download, FileText, Sparkles, TrendingUp, TriangleAlert } from 'lucide-react'

import { DataQualityCard } from '@/components/company-profile/DataQualityCard'
import { FrameworkResultsCard } from '@/components/company-profile/FrameworkResultsCard'
import { IdentityCard } from '@/components/company-profile/IdentityCard'
import { PeriodHistoryCard } from '@/components/company-profile/PeriodHistoryCard'
import { EvidenceBadge } from '@/components/EvidenceBadge'
import { MetricCard } from '@/components/MetricCard'
import { NoticeBanner } from '@/components/NoticeBanner'
import { PeerComparisonCard } from '@/components/company-profile/PeerComparisonCard'
import { PageContainer } from '@/components/layout/PageContainer'
import { PageHeader } from '@/components/layout/PageHeader'
import { Panel } from '@/components/layout/Panel'
import { QueryStateCard } from '@/components/QueryStateCard'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { getCompanyProfile } from '@/lib/api'
import type {
  CompanyDataQualitySummary,
  CompanyIdentityProvenanceSummary,
  EvidenceAnchor,
  CompanyNarrativeSummary,
  FrameworkMetadata,
} from '@/lib/types'
import { useTranslation } from 'react-i18next'
import { localizeErrorMessage } from '@/lib/error-utils'
import { exportCompanyProfileCSV, exportToJSON } from '@/lib/export'
import {
  asDate,
  asNum,
  asPct,
  buildCompanyTrendData,
  compactList,
  deltaNumber,
  deltaPctLabel,
  deltaPercent,
  deltaPercentLabel,
  deltaToneClass,
  evidenceRichness,
  frameworkRunKey,
  mergeEvidenceAnchor,
  metricDisclosureLabel,
  metricLabelsFromKeys,
  normalizeProfileEvidenceAnchor,
  parseCompanyReportId,
  prettifyToken,
  sourceOriginLabel,
  type FrameworkDisplayResult,
} from './company-profile/utils'

const CompanyProfileHeavyCharts = lazy(() =>
  import('@/components/company-profile/CompanyProfileHeavyCharts').then((module) => ({
    default: module.CompanyProfileHeavyCharts,
  }))
)

function DeferredHeavyCharts({
  ready,
  fallback,
  children,
}: {
  ready: boolean
  fallback: ReactNode
  children: ReactNode
}) {
  const [revealed, setRevealed] = useState(false)

  useEffect(() => {
    if (!ready || revealed) return

    const timer = window.setTimeout(() => setRevealed(true), 180)
    return () => window.clearTimeout(timer)
  }, [ready, revealed])

  return ready && revealed ? children : fallback
}

export function CompanyProfilePage() {
  const { t, i18n } = useTranslation()
  const locale = i18n.resolvedLanguage ?? i18n.language ?? 'de'
  const { companyName = '' } = useParams<{ companyName: string }>()
  const decodedName = decodeURIComponent(companyName)

  const { data: profile, isLoading, error, refetch } = useQuery({
    queryKey: ['company-profile', decodedName],
    queryFn: () => getCompanyProfile(decodedName),
    enabled: !!decodedName,
  })

  const trendData = useMemo(
    () => buildCompanyTrendData(profile?.trend ?? []),
    [profile]
  )
  const sortedTrendPoints = useMemo(
    () => [...(profile?.trend ?? [])].sort((a, b) => a.year - b.year),
    [profile]
  )
  const periodMetricsByYear = useMemo(() => {
    const entries = (profile?.periods ?? []).map((period) => [
      period.report_year,
      period.merged_result.merged_metrics,
    ] as const)
    return new Map(entries)
  }, [profile])

  const frameworkScores: FrameworkDisplayResult[] = useMemo(() => {
    if (!profile) return []

    const merged = new Map<string, FrameworkDisplayResult>()

    for (const framework of profile.framework_scores ?? []) {
      merged.set(frameworkRunKey(framework), framework)
    }

    for (const framework of profile.framework_results ?? []) {
      const key = frameworkRunKey(framework)
      const existing = merged.get(key)
      merged.set(key, {
        ...(existing ?? framework),
        ...framework,
        framework_version:
          framework.framework_version ?? existing?.framework_version,
        analyzed_at: framework.analyzed_at ?? existing?.analyzed_at ?? null,
        stored_at: framework.stored_at ?? existing?.stored_at ?? null,
      })
    }

    return Array.from(merged.values())
  }, [profile])

  const frameworkMetaMap = useMemo(() => {
    const map = new Map<string, FrameworkMetadata>()
    for (const metadata of profile?.framework_metadata ?? []) {
      map.set(metadata.framework_id, metadata)
    }
    return map
  }, [profile])

  const identitySummary: CompanyIdentityProvenanceSummary | null = useMemo(() => {
    if (!profile) return null
    return (
      profile.identity_provenance_summary ?? {
        canonical_company_name: profile.company_name,
        requested_company_name: decodedName,
        has_alias_consolidation: false,
        consolidated_aliases: [],
        latest_source_document_type: profile.latest_period.source_document_type,
        source_priority_preview: null,
        merge_priority_preview: null,
      }
    )
  }, [decodedName, profile])

  const frameworkRadarData = useMemo(
    () =>
      frameworkScores.map((f) => ({
        framework: f.framework,
        score: Math.round(f.total_score * 100),
      })),
    [frameworkScores]
  )

  const previousTrendPoint = useMemo(() => {
    if (sortedTrendPoints.length < 2) return null
    return sortedTrendPoints[sortedTrendPoints.length - 2]
  }, [sortedTrendPoints])

  const yoyDeltaCard = useMemo(() => {
    if (!profile || sortedTrendPoints.length < 2) return null
    const latestTrendPoint = sortedTrendPoints[sortedTrendPoints.length - 1]
    const previous = sortedTrendPoints[sortedTrendPoints.length - 2]
    const latestMetrics =
      periodMetricsByYear.get(latestTrendPoint.year) ?? profile.latest_metrics
    const previousMetrics = periodMetricsByYear.get(previous.year)

    const co2eDeltaPct = deltaPercent(
      latestMetrics.scope1_co2e_tonnes ?? latestTrendPoint.scope1,
      previousMetrics?.scope1_co2e_tonnes ?? previous.scope1
    )
    const revenueDeltaPct = deltaPercent(
      latestMetrics.total_revenue_eur,
      previousMetrics?.total_revenue_eur ?? null
    )
    const alignmentDeltaPct = deltaPercent(
      latestMetrics.taxonomy_aligned_revenue_pct ??
        latestTrendPoint.taxonomy_aligned_revenue_pct,
      previousMetrics?.taxonomy_aligned_revenue_pct ??
        previous.taxonomy_aligned_revenue_pct
    )

    return {
      previousYear: previous.year,
      co2eDeltaPct,
      revenueDeltaPct,
      alignmentDeltaPct,
      hasAnyDelta:
        co2eDeltaPct != null ||
        revenueDeltaPct != null ||
        alignmentDeltaPct != null,
    }
  }, [periodMetricsByYear, profile, sortedTrendPoints])

  const yoySummary = useMemo(() => {
    if (!profile) return null
    const latest = profile.latest_metrics
    const previous = previousTrendPoint
    const renewableDelta = deltaNumber(latest.renewable_energy_pct, previous?.renewable_pct)
    const taxonomyDelta = deltaNumber(
      latest.taxonomy_aligned_revenue_pct,
      previous?.taxonomy_aligned_revenue_pct
    )
    const scope1Delta = deltaNumber(latest.scope1_co2e_tonnes, previous?.scope1)

    return {
      previousYear: previous?.year ?? null,
      renewableDelta,
      taxonomyDelta,
      scope1Delta,
      hasAnyDelta:
        renewableDelta != null || taxonomyDelta != null || scope1Delta != null,
    }
  }, [previousTrendPoint, profile])

  const heroInsight = useMemo(() => {
    if (!profile) return { title: '', body: '', tone: 'indigo' as const }

    const scores = frameworkScores.map((f) => f.total_score)
    const maxScore = scores.length > 0 ? Math.max(...scores) : null
    const minScore = scores.length > 0 ? Math.min(...scores) : null
    const spread = maxScore != null && minScore != null ? maxScore - minScore : null

    if (yoySummary?.renewableDelta != null && yoySummary.renewableDelta > 0 && yoySummary.scope1Delta != null && yoySummary.scope1Delta < 0) {
      return {
        title: t('profile.heroImprovingTitle'),
        body: t('profile.heroImprovingBody', {
          renewableDelta: deltaPctLabel(yoySummary.renewableDelta),
          scope1Delta: Math.abs(yoySummary.scope1Delta).toLocaleString(locale),
        }),
        tone: 'green' as const,
      }
    }

    if (spread != null && spread >= 0.2) {
      return {
        title: t('profile.heroDivergenceTitle'),
        body: t('profile.heroDivergenceBody', {
          spread: `${Math.round(spread * 100)}%`,
        }),
        tone: 'amber' as const,
      }
    }

    return {
      title: t('profile.heroCoverageTitle'),
      body: t('profile.heroCoverageBody', {
        periods: profile.periods.length,
        frameworks: frameworkScores.length,
      }),
      tone: 'indigo' as const,
    }
  }, [frameworkScores, locale, profile, t, yoySummary])

  const dataQualitySummary: CompanyDataQualitySummary | null = useMemo(() => {
    if (!profile) return null
    if (profile.data_quality_summary) return profile.data_quality_summary
    return {
      total_key_metrics_count: 0,
      present_metrics_count: 0,
      present_metrics: [],
      missing_metrics: [],
      completion_percentage: 0,
      readiness_label: 'draft',
    }
  }, [profile])

  const narrativeSummary: CompanyNarrativeSummary | null = useMemo(() => {
    if (!profile || !dataQualitySummary) return null
    if (profile.narrative_summary) return profile.narrative_summary
    const previousYear =
      profile.trend.length >= 2 ? profile.trend[profile.trend.length - 2].year : null
    return {
      snapshot: {
        periods_count: profile.periods.length,
        years_count: profile.years_available.length,
        latest_year: profile.latest_year,
        framework_count: frameworkScores.length,
        readiness_label: dataQualitySummary.readiness_label,
      },
      has_previous_period: profile.trend.length >= 2,
      previous_year: previousYear,
      improved_metrics: [],
      weakened_metrics: [],
      stable_metrics: [],
      disclosure_strength_metrics: dataQualitySummary.present_metrics,
      disclosure_gap_metrics: dataQualitySummary.missing_metrics,
    }
  }, [dataQualitySummary, frameworkScores.length, profile])

  const missingDisclosureLabels = (dataQualitySummary?.missing_metrics ?? []).map((metricKey) => ({
    metricKey,
    label: metricDisclosureLabel(t, metricKey),
  }))
  const presentDisclosureLabels = (dataQualitySummary?.present_metrics ?? []).map((metricKey) => ({
    metricKey,
    label: metricDisclosureLabel(t, metricKey),
  }))
  const improvedMetricLabels = metricLabelsFromKeys(t, narrativeSummary?.improved_metrics ?? [])
  const weakenedMetricLabels = metricLabelsFromKeys(t, narrativeSummary?.weakened_metrics ?? [])
  const strengthMetricLabels = metricLabelsFromKeys(t, narrativeSummary?.disclosure_strength_metrics ?? [])
  const gapMetricLabels = metricLabelsFromKeys(t, narrativeSummary?.disclosure_gap_metrics ?? [])
  const readinessLabel = dataQualitySummary
    ? t(`profile.readinessLabel.${dataQualitySummary.readiness_label}`)
    : '—'
  const readinessToneClass = dataQualitySummary
    ? {
        draft: 'bg-slate-100 text-slate-700 border-slate-200',
        usable: 'bg-amber-100 text-amber-800 border-amber-200',
        'showcase-ready': 'bg-emerald-100 text-emerald-800 border-emerald-200',
      }[dataQualitySummary.readiness_label]
    : 'bg-slate-100 text-slate-700 border-slate-200'

  if (isLoading) {
    return (
      <QueryStateCard
        tone="loading"
        title={t('common.loading')}
        body={t('companies.companyCardHint')}
        className="max-w-2xl"
      />
    )
  }
  if (error) {
    return (
      <QueryStateCard
        tone="error"
        title={t('common.error')}
        body={localizeErrorMessage(t, error, 'common.error')}
        actionLabel={t('errorBoundary.retry')}
        onAction={() => void refetch()}
        className="max-w-2xl"
      />
    )
  }
  if (!profile || !dataQualitySummary || !narrativeSummary) {
    return (
      <QueryStateCard
        tone="empty"
        title={t('common.noData')}
        body={t('companies.companyCardHint')}
        actionLabel={t('errorBoundary.retry')}
        onAction={() => void refetch()}
        className="max-w-2xl"
      />
    )
  }

  const m = profile.latest_metrics
  const latestSources = profile.latest_sources ?? []
  const latestSourceTypes = compactList(
    latestSources.map((source) => prettifyToken(source.source_document_type))
  )
  const latestEvidenceSummary = [
    ...latestSources.flatMap((source) => source.evidence_anchors ?? []),
    ...(profile.evidence_summary ?? []),
  ]
    .map((entry) =>
      normalizeProfileEvidenceAnchor(
        entry,
        latestSources,
        profile.latest_period.reporting_period_label,
        profile.latest_period.source_document_type
      )
    )
    .sort((a, b) => evidenceRichness(b) - evidenceRichness(a))
    .reduce<EvidenceAnchor[]>((acc, normalized) => {
      const key =
        normalized.metric ??
        `${normalized.document_title ?? normalized.source ?? 'evidence'}-${acc.length}`
      const existingIndex = acc.findIndex((item) => item.metric === key)

      if (existingIndex === -1) {
        acc.push({ ...normalized, metric: normalized.metric ?? key })
        return acc
      }

      acc[existingIndex] = mergeEvidenceAnchor(acc[existingIndex], normalized)
      return acc
    }, [])
  const evidenceByMetric = latestEvidenceSummary.reduce<Map<string, EvidenceAnchor>>((map, entry) => {
    if (entry.metric) {
      map.set(entry.metric, entry)
    }
    return map
  }, new Map())
  const latestSourceOrigin = sourceOriginLabel(latestSources[0])
  const latestCompanyReportId = parseCompanyReportId(latestSources[0]?.source_id)
  const latestMergeCue = (() => {
    const preferredMetrics = [
      'renewable_energy_pct',
      'scope1_co2e_tonnes',
      'taxonomy_aligned_revenue_pct',
      'scope2_co2e_tonnes',
    ]

    for (const metricKey of preferredMetrics) {
      const mergeMetric = profile.latest_merged_result?.metrics?.[metricKey]
      if (mergeMetric?.chosen_source_document_type) {
        return {
          metricKey,
          chosenSourceDocumentType: mergeMetric.chosen_source_document_type,
          mergeReason: mergeMetric.merge_reason,
        }
      }
    }

    return null
  })()
  const heroInsightTone = {
    green: 'success' as const,
    amber: 'warning' as const,
    indigo: 'info' as const,
  }[heroInsight.tone]
  const chartFallback = (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="h-[360px] rounded-2xl border bg-stone-100/70 animate-pulse" />
      <div className="h-[360px] rounded-2xl border bg-stone-100/70 animate-pulse" />
    </div>
  )

  return (
    <PageContainer>
      <Link
        to="/companies"
        className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-900"
      >
        <ArrowLeft size={14} />
        {t('profile.backToCompanies')}
      </Link>

      <PageHeader
        title={profile.company_name}
        subtitle={`${profile.latest_period.source_document_type ?? '—'} · ${profile.latest_year}`}
        actions={(
          <div className="flex flex-col items-start gap-3">
            <Badge variant="secondary" className="rounded-full">
              {profile.latest_period.reporting_period_label}
            </Badge>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => exportCompanyProfileCSV(profile)}
                aria-label={t('profile.exportCSV')}
              >
                <Download size={14} className="mr-1 shrink-0" aria-hidden="true" />
                {t('profile.exportCSV')}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  exportToJSON(
                    profile,
                    `${profile.company_name.replace(/[^a-z0-9]/gi, '_')}_esg_${profile.latest_year}.json`
                  )
                }
                aria-label={t('profile.exportJSON')}
              >
                <Download size={14} className="mr-1 shrink-0" aria-hidden="true" />
                {t('profile.exportJSON')}
              </Button>
            </div>
          </div>
        )}
        kpis={[
          {
            label: t('profile.heroStatPeriods'),
            value: profile.periods.length,
          },
          {
            label: t('profile.heroStatFrameworks'),
            value: frameworkScores.length,
          },
        ]}
      />

      <NoticeBanner
        tone={heroInsightTone}
        title={(
          <span className="inline-flex items-center gap-2">
            <Sparkles size={14} />
            {t('profile.heroLabel')} · {heroInsight.title}
          </span>
        )}
      >
        <p>{heroInsight.body}</p>
      </NoticeBanner>

      <IdentityCard
        companyName={profile.company_name}
        identitySummary={identitySummary}
      />

      <Panel
        title={(
          <span className="flex items-center gap-2 text-base">
            <FileText size={16} className="text-indigo-600" />
            {t('profile.provenanceTitle')}
          </span>
        )}
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-lg border bg-slate-50 px-4 py-3">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {t('profile.provenancePeriodLabel')}
            </p>
            <p className="mt-2 text-sm font-semibold text-slate-900">
              {profile.latest_period.period?.label ??
                profile.latest_period.reporting_period_label}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              {t('profile.provenancePeriodSummary', {
                type:
                  profile.latest_period.period?.type ??
                  profile.latest_period.reporting_period_type ??
                  '—',
                year:
                  profile.latest_period.period?.legacy_report_year ??
                  profile.latest_period.report_year,
              })}
            </p>
          </div>

          <div className="rounded-lg border bg-slate-50 px-4 py-3">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {t('profile.provenanceSourcesLabel')}
            </p>
            <p
              className="mt-2 text-sm font-semibold text-slate-900"
              data-testid="profile-provenance-source-summary"
            >
              {t('profile.provenanceSourceSummary', { count: latestSources.length })}
            </p>
            <p
              className="mt-1 text-xs text-slate-500"
              data-testid="profile-provenance-source-types"
            >
              {[latestSourceTypes, latestSourceOrigin].filter(Boolean).join(' · ') || '—'}
            </p>
          </div>

          <div className="rounded-lg border bg-slate-50 px-4 py-3">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {t('profile.provenanceMergeLabel')}
            </p>
            <p
              className="mt-2 text-sm font-semibold text-slate-900"
              data-testid="profile-provenance-merge-summary"
            >
              {t('profile.provenanceMergeSummary', {
                count:
                  profile.latest_merged_result?.source_count ?? latestSources.length,
              })}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              {latestMergeCue
                ? t('profile.provenanceMergeMetricCue', {
                    metric: metricDisclosureLabel(t, latestMergeCue.metricKey),
                    sourceType: prettifyToken(latestMergeCue.chosenSourceDocumentType),
                    reason: prettifyToken(latestMergeCue.mergeReason),
                  })
                : '—'}
            </p>
          </div>

          <div className="rounded-lg border bg-slate-50 px-4 py-3">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {t('profile.provenanceFrameworkLabel')}
            </p>
            {frameworkScores.length === 0 ? (
              <p className="mt-2 text-sm text-slate-500">{t('profile.noFrameworkResults')}</p>
            ) : (
              <div className="mt-2 space-y-2">
                {frameworkScores.slice(0, 2).map((framework) => (
                  <div key={`${framework.framework_id}-${framework.framework_version ?? 'unknown'}-${framework.analyzed_at ?? framework.stored_at ?? 'none'}`}>
                    <p className="text-sm font-semibold text-slate-900">
                      {t('profile.provenanceFrameworkVersion', {
                        framework: framework.framework,
                        version: framework.framework_version ?? '—',
                      })}
                    </p>
                    <p className="text-xs text-slate-500">
                      {t('profile.provenanceFrameworkTimestamp', {
                        date: asDate(
                          framework.analyzed_at ?? framework.stored_at ?? null,
                          locale
                        ),
                      })}
                    </p>
                  </div>
                ))}
                {frameworkScores.length > 2 ? (
                  <p className="text-xs text-slate-500">
                    {t('profile.provenanceFrameworkMore', {
                      count: frameworkScores.length - 2,
                    })}
                  </p>
                ) : null}
              </div>
            )}
          </div>
        </div>
      </Panel>

      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard
          label={t('companies.scope1')}
          value={asNum(m.scope1_co2e_tonnes, locale)}
          unit="tCO2e"
          footer={
            <EvidenceBadge
              evidence={evidenceByMetric.get('scope1_co2e_tonnes')}
              metricLabel={metricDisclosureLabel(t, 'scope1_co2e_tonnes')}
              fallbackFramework={profile.latest_period.source_document_type}
              fallbackPeriodLabel={profile.latest_period.reporting_period_label}
              testId="evidence-badge-scope1_co2e_tonnes"
            />
          }
        />
        <MetricCard
          label={t('companies.scope2')}
          value={asNum(m.scope2_co2e_tonnes, locale)}
          unit="tCO2e"
          footer={
            <EvidenceBadge
              evidence={evidenceByMetric.get('scope2_co2e_tonnes')}
              metricLabel={metricDisclosureLabel(t, 'scope2_co2e_tonnes')}
              fallbackFramework={profile.latest_period.source_document_type}
              fallbackPeriodLabel={profile.latest_period.reporting_period_label}
              testId="evidence-badge-scope2_co2e_tonnes"
            />
          }
        />
        <MetricCard
          label={t('companies.employees')}
          value={asNum(m.total_employees, locale)}
          unit={t('companies.unitPeople')}
          footer={
            <EvidenceBadge
              evidence={evidenceByMetric.get('total_employees')}
              metricLabel={metricDisclosureLabel(t, 'total_employees')}
              fallbackFramework={profile.latest_period.source_document_type}
              fallbackPeriodLabel={profile.latest_period.reporting_period_label}
              testId="evidence-badge-total_employees"
            />
          }
        />
        <MetricCard
          label={t('companies.renewable')}
          value={asPct(m.renewable_energy_pct)}
          unit={t('companies.unitPercent')}
          color="green"
          footer={
            <EvidenceBadge
              evidence={evidenceByMetric.get('renewable_energy_pct')}
              metricLabel={metricDisclosureLabel(t, 'renewable_energy_pct')}
              fallbackFramework={profile.latest_period.source_document_type}
              fallbackPeriodLabel={profile.latest_period.reporting_period_label}
              testId="evidence-badge-renewable_energy_pct"
            />
          }
        />
      </div>

      <PeerComparisonCard
        companyReportId={latestCompanyReportId}
        industryCode={profile.latest_period?.industry_code ?? null}
        reportYear={profile.latest_year}
        metrics={profile.latest_metrics}
      />

      <DataQualityCard
        dataQualitySummary={dataQualitySummary}
        readinessLabel={readinessLabel}
        readinessToneClass={readinessToneClass}
        presentDisclosureLabels={presentDisclosureLabels}
        missingDisclosureLabels={missingDisclosureLabels}
        evidenceByMetric={evidenceByMetric}
        latestPeriod={profile.latest_period}
      />

      <DeferredHeavyCharts key={decodedName} ready={!isLoading} fallback={chartFallback}>
        {trendData.length < 2 && (
          <NoticeBanner tone="warning" title={t('profile.trendInsufficientDataTitle')}>
            <p>{t('profile.trendInsufficientDataBody')}</p>
          </NoticeBanner>
        )}
        <Suspense
          fallback={chartFallback}
        >
          <CompanyProfileHeavyCharts
            frameworkRadarData={frameworkRadarData}
            trendData={trendData}
            radarTitle={t('profile.radarTitle')}
            trendTitle={t('profile.trendTitle')}
            radarLegend={t('profile.radarLegend')}
            trendLegend={t('profile.trendLegend')}
            noFrameworkResultsLabel={t('profile.noFrameworkResults')}
            scoreLabel={t('common.score')}
            scope1Label={t('companies.scope1')}
            renewableLabel={t('companies.renewable')}
          />
        </Suspense>
      </DeferredHeavyCharts>

      {yoyDeltaCard && (
        <div data-testid="yoy-delta-card">
          <Panel
            title={(
              <span className="flex items-center gap-2 text-base">
                <TrendingUp size={16} className="text-indigo-600" />
                {t('profile.yoyTitle')}
              </span>
            )}
          >
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-lg border bg-slate-50 px-4 py-4">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  YoY CO2e
                </p>
                <p className={`mt-2 text-2xl font-semibold ${deltaToneClass(yoyDeltaCard.co2eDeltaPct)}`}>
                  {deltaPercentLabel(yoyDeltaCard.co2eDeltaPct)}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  {t('profile.yoyComparedTo', { year: yoyDeltaCard.previousYear ?? '—' })}
                </p>
              </div>
              <div className="rounded-lg border bg-slate-50 px-4 py-4">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  YoY Revenue
                </p>
                <p className={`mt-2 text-2xl font-semibold ${deltaToneClass(yoyDeltaCard.revenueDeltaPct)}`}>
                  {deltaPercentLabel(yoyDeltaCard.revenueDeltaPct)}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  {t('profile.yoyComparedTo', { year: yoyDeltaCard.previousYear ?? '—' })}
                </p>
              </div>
              <div className="rounded-lg border bg-slate-50 px-4 py-4">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  YoY Alignment
                </p>
                <p className={`mt-2 text-2xl font-semibold ${deltaToneClass(yoyDeltaCard.alignmentDeltaPct)}`}>
                  {deltaPercentLabel(yoyDeltaCard.alignmentDeltaPct)}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  {t('profile.yoyComparedTo', { year: yoyDeltaCard.previousYear ?? '—' })}
                </p>
              </div>
              <div className="rounded-lg border bg-white px-4 py-4 md:col-span-3">
                <p className="text-sm leading-6 text-slate-700">
                  {yoySummary?.hasAnyDelta
                    ? t('profile.yoyNarrativeReady', {
                        year: yoySummary.previousYear ?? '—',
                        renewableDelta: yoySummary.renewableDelta != null ? `${yoySummary.renewableDelta >= 0 ? '+' : ''}${yoySummary.renewableDelta.toFixed(1)}%` : '—',
                        taxonomyDelta: yoySummary.taxonomyDelta != null ? `${yoySummary.taxonomyDelta >= 0 ? '+' : ''}${yoySummary.taxonomyDelta.toFixed(1)}%` : '—',
                      })
                    : t('profile.yoyNarrativeMissing')}
                </p>
              </div>
            </div>
          </Panel>
        </div>
      )}

      <FrameworkResultsCard
        frameworkScores={frameworkScores}
        frameworkMetaMap={frameworkMetaMap}
        locale={locale}
      />

      <PeriodHistoryCard
        periods={profile.periods}
        latestEvidenceSummary={latestEvidenceSummary}
        fallbackFramework={profile.latest_period.source_document_type}
        fallbackPeriodLabel={profile.latest_period.reporting_period_label}
      />

      <Panel
        title={(
          <span className="flex items-center gap-2 text-base">
            <FileText size={16} className="text-indigo-600" />
            {t('profile.narrativeTitle')}
          </span>
        )}
      >
        <div className="space-y-5 text-sm text-slate-700">
          <section className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('profile.narrativeSnapshotTitle')}</p>
            <p className="rounded-lg border bg-white px-4 py-3 leading-6">
              {t('profile.narrativeSnapshotBody', {
                periods: narrativeSummary.snapshot.periods_count,
                years: narrativeSummary.snapshot.years_count,
                frameworks: narrativeSummary.snapshot.framework_count,
                latestYear: narrativeSummary.snapshot.latest_year,
                readiness: t(`profile.readinessLabel.${narrativeSummary.snapshot.readiness_label}`),
              })}
            </p>
          </section>

          <section className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('profile.narrativeChangeTitle')}</p>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-lg border bg-white px-4 py-3">
                <p className="mb-2 inline-flex items-center gap-1 text-xs font-medium text-emerald-700">
                  <CheckCircle2 size={14} />
                  {t('profile.narrativeImprovedLabel')}
                </p>
                {improvedMetricLabels.length === 0 ? (
                  <p className="text-xs text-slate-500">{t('profile.narrativeNoImprovement')}</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {improvedMetricLabels.map((label) => (
                      <span key={label} className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs text-emerald-800">
                        {label}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div className="rounded-lg border bg-white px-4 py-3">
                <p className="mb-2 inline-flex items-center gap-1 text-xs font-medium text-amber-700">
                  <TriangleAlert size={14} />
                  {t('profile.narrativeWeakenedLabel')}
                </p>
                {weakenedMetricLabels.length === 0 ? (
                  <p className="text-xs text-slate-500">{t('profile.narrativeNoWeakening')}</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {weakenedMetricLabels.map((label) => (
                      <span key={label} className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-800">
                        {label}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </section>

          <section className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('profile.narrativeStrengthTitle')}</p>
            {strengthMetricLabels.length === 0 ? (
              <p className="rounded-lg border bg-white px-4 py-3 text-xs text-slate-500">{t('profile.narrativeNoStrengths')}</p>
            ) : (
              <div className="flex flex-wrap gap-2 rounded-lg border bg-white px-4 py-3">
                {strengthMetricLabels.map((label) => (
                  <span key={label} className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs text-emerald-800">
                    {label}
                  </span>
                ))}
              </div>
            )}
          </section>

          <section className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('profile.narrativeGapTitle')}</p>
            {gapMetricLabels.length === 0 ? (
              <p className="rounded-lg border bg-white px-4 py-3 text-xs text-emerald-700">{t('profile.narrativeNoGaps')}</p>
            ) : (
              <div className="flex flex-wrap gap-2 rounded-lg border bg-white px-4 py-3">
                {gapMetricLabels.map((label) => (
                  <span key={label} className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-800">
                    {label}
                  </span>
                ))}
              </div>
            )}
          </section>

          <section className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('profile.narrativePortfolioTitle')}</p>
            <p className="rounded-lg border bg-white px-4 py-3 leading-6">
              {t('profile.narrativePortfolioBody', {
                periods: narrativeSummary.snapshot.periods_count,
                frameworks: narrativeSummary.snapshot.framework_count,
              })}
            </p>
          </section>
        </div>
      </Panel>
    </PageContainer>
  )
}

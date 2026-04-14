import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Building2, CheckCircle2, Clock3, FileText, Leaf, ShieldCheck, Sparkles, TrendingUp, TriangleAlert } from 'lucide-react'
import {
  Line,
  LineChart,
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { MetricCard } from '@/components/MetricCard'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { getCompanyProfile } from '@/lib/api'
import type {
  CompanyDataQualitySummary,
  CompanyIdentityProvenanceSummary,
  CompanyNarrativeSummary,
  FrameworkScoreResult,
} from '@/lib/types'
import { useTranslation } from 'react-i18next'
import { localizeErrorMessage } from '@/lib/error-utils'

function asPct(v: number | null | undefined) {
  return v == null ? '—' : `${v.toFixed(1)}%`
}

function asNum(v: number | null | undefined, locale: string) {
  return v == null ? '—' : v.toLocaleString(locale)
}

function deltaNumber(current: number | null | undefined, previous: number | null | undefined) {
  if (current == null || previous == null) return null
  return current - previous
}

function deltaPctLabel(value: number | null | undefined) {
  if (value == null) return '—'
  const prefix = value > 0 ? '+' : ''
  return `${prefix}${value.toFixed(1)}`
}

function metricDisclosureLabel(t: (key: string) => string, metricKey: string) {
  return t(`profile.metricLabels.${metricKey}`)
}

function metricLabelsFromKeys(t: (key: string) => string, metricKeys: string[]) {
  return metricKeys.map((metricKey) => metricDisclosureLabel(t, metricKey))
}

export function CompanyProfilePage() {
  const { t, i18n } = useTranslation()
  const locale = i18n.resolvedLanguage ?? i18n.language ?? 'de'
  const { companyName = '' } = useParams<{ companyName: string }>()
  const decodedName = decodeURIComponent(companyName)

  const { data: profile, isLoading, error } = useQuery({
    queryKey: ['company-profile', decodedName],
    queryFn: () => getCompanyProfile(decodedName),
    enabled: !!decodedName,
  })

  const trendData = useMemo(
    () =>
      (profile?.trend ?? []).map((d) => ({
        year: d.year,
        scope1: d.scope1 ?? 0,
        renewable: d.renewable_pct ?? 0,
        taxonomy: d.taxonomy_aligned_revenue_pct ?? 0,
      })),
    [profile]
  )

  const frameworkScores: FrameworkScoreResult[] = useMemo(() => {
    if (!profile) return []
    if (profile.framework_scores && profile.framework_scores.length > 0) {
      return profile.framework_scores
    }
    return profile.framework_results
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
    if (!profile || profile.trend.length < 2) return null
    return profile.trend[profile.trend.length - 2]
  }, [profile])

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

  const missingDisclosureLabels = metricLabelsFromKeys(t, dataQualitySummary?.missing_metrics ?? [])
  const presentDisclosureLabels = metricLabelsFromKeys(t, dataQualitySummary?.present_metrics ?? [])
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

  if (isLoading) return <p className="text-slate-400">{t('common.loading')}</p>
  if (error) return <p className="text-red-500">{localizeErrorMessage(t, error, 'common.error')}</p>
  if (!profile) return <p className="text-red-500">{t('common.error')}</p>
  if (!dataQualitySummary || !narrativeSummary) return <p className="text-red-500">{t('common.error')}</p>

  const m = profile.latest_metrics
  const heroToneClasses = {
    green: 'border-emerald-200 bg-emerald-50 text-emerald-900',
    amber: 'border-amber-200 bg-amber-50 text-amber-900',
    indigo: 'border-indigo-200 bg-indigo-50 text-indigo-900',
  }[heroInsight.tone]

  return (
    <div className="space-y-6">
      <div className="surface-card overflow-hidden">
        <div className="flex flex-col gap-4 p-5 md:flex-row md:items-start md:justify-between md:p-6">
        <div className="space-y-3 min-w-0">
          <Link
            to="/companies"
            className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-900"
          >
            <ArrowLeft size={14} />
            {t('profile.backToCompanies')}
          </Link>
          <div className="flex flex-wrap items-start gap-2">
            <Building2 size={20} className="text-indigo-600" />
            <h1 className="max-w-4xl text-3xl font-semibold leading-tight text-slate-900 break-words">
              {profile.company_name}
            </h1>
            <Badge variant="secondary" className="rounded-full">
              {profile.latest_period.reporting_period_label}
            </Badge>
          </div>
          <p className="max-w-3xl text-sm leading-6 text-slate-500">
            {profile.latest_period.source_document_type ?? '—'} · {profile.latest_year}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-3 text-sm md:min-w-80">
          <div className="rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-4">
            <p className="section-kicker">{t('profile.heroStatPeriods')}</p>
            <p className="mt-2 numeric-mono text-2xl font-semibold text-slate-900">{profile.periods.length}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-4">
            <p className="section-kicker">{t('profile.heroStatFrameworks')}</p>
            <p className="mt-2 numeric-mono text-2xl font-semibold text-slate-900">{frameworkScores.length}</p>
          </div>
        </div>
        </div>
      </div>

      <Card className={heroToneClasses}>
        <CardContent className="flex flex-col gap-3 pt-6 md:flex-row md:items-start md:justify-between">
          <div className="space-y-2">
            <p className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] opacity-80">
              <Sparkles size={14} />
              {t('profile.heroLabel')}
            </p>
            <h2 className="text-xl font-semibold">{heroInsight.title}</h2>
            <p className="max-w-3xl text-sm leading-6 opacity-90">{heroInsight.body}</p>
          </div>
          <div className="hidden md:block md:min-w-48" />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Building2 size={16} className="text-indigo-600" />
            {t('profile.identityTitle')}
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="rounded-lg border bg-slate-50 px-4 py-3">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {t('profile.canonicalNameLabel')}
            </p>
            <p className="mt-2 text-sm font-semibold text-slate-900">
              {identitySummary?.canonical_company_name ?? profile.company_name}
            </p>
            {identitySummary?.requested_company_name &&
            identitySummary.requested_company_name !==
              (identitySummary?.canonical_company_name ?? profile.company_name) ? (
              <p className="mt-1 text-xs text-slate-500">
                {identitySummary.requested_company_name} →{' '}
                {identitySummary?.canonical_company_name ?? profile.company_name}
              </p>
            ) : null}
          </div>
          <div className="rounded-lg border bg-slate-50 px-4 py-3">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {t('profile.latestSourceTypeLabel')}
            </p>
            <p className="mt-2 text-sm font-semibold text-slate-900">
              {identitySummary?.latest_source_document_type ?? '—'}
            </p>
          </div>
          <div className="rounded-lg border bg-slate-50 px-4 py-3">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {t('profile.aliasConsolidationLabel')}
            </p>
            <p className="mt-2 text-sm font-semibold text-slate-900">
              {identitySummary?.has_alias_consolidation
                ? t('profile.aliasConsolidationYes')
                : t('profile.aliasConsolidationNo')}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              {identitySummary?.consolidated_aliases?.length
                ? identitySummary.consolidated_aliases.join(', ')
                : t('profile.aliasListNone')}
            </p>
          </div>
          <div className="rounded-lg border bg-slate-50 px-4 py-3">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {t('profile.sourceMergePriorityLabel')}
            </p>
            <p className="mt-2 text-sm text-slate-700">
              {identitySummary?.merge_priority_preview ?? t('profile.sourceMergePriorityReserved')}
            </p>
            {identitySummary?.source_priority_preview ? (
              <p className="mt-1 text-xs text-amber-700">{identitySummary.source_priority_preview}</p>
            ) : null}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label={t('companies.scope1')} value={asNum(m.scope1_co2e_tonnes, locale)} unit="tCO2e" />
        <MetricCard label={t('companies.scope2')} value={asNum(m.scope2_co2e_tonnes, locale)} unit="tCO2e" />
        <MetricCard label={t('companies.employees')} value={asNum(m.total_employees, locale)} unit={t('companies.unitPeople')} />
        <MetricCard label={t('companies.renewable')} value={asPct(m.renewable_energy_pct)} unit={t('companies.unitPercent')} color="green" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheck size={16} className="text-indigo-600" />
            {t('profile.dataQualityTitle')}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-3 rounded-lg border bg-slate-50 px-4 py-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                {t('profile.dataQualityCompletion')}
              </p>
              <p className="mt-1 text-2xl font-semibold text-slate-900">
                {dataQualitySummary.completion_percentage.toFixed(1)}%
              </p>
            </div>
            <Badge className={`border ${readinessToneClass}`}>
              {t('profile.dataQualityReadiness')}: {readinessLabel}
            </Badge>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg border bg-white px-4 py-3">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('profile.dataQualityTotal')}</p>
              <p className="mt-2 text-xl font-semibold text-slate-900">{dataQualitySummary.total_key_metrics_count}</p>
            </div>
            <div className="rounded-lg border bg-white px-4 py-3">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('profile.dataQualityPresent')}</p>
              <p className="mt-2 text-xl font-semibold text-emerald-700">{dataQualitySummary.present_metrics_count}</p>
            </div>
            <div className="rounded-lg border bg-white px-4 py-3">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('profile.dataQualityMissing')}</p>
              <p className="mt-2 text-xl font-semibold text-amber-700">{dataQualitySummary.missing_metrics.length}</p>
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {t('profile.dataQualityPresentList')}
            </p>
            {presentDisclosureLabels.length === 0 ? (
              <p className="text-sm text-slate-500">{t('profile.dataQualityNoPresent')}</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {presentDisclosureLabels.map((label) => (
                  <span key={label} className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs text-emerald-800">
                    {label}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {t('profile.dataQualityMissingList')}
            </p>
            {missingDisclosureLabels.length === 0 ? (
              <p className="text-sm text-emerald-700">{t('profile.dataQualityNoMissing')}</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {missingDisclosureLabels.map((label) => (
                  <span key={label} className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-800">
                    {label}
                  </span>
                ))}
              </div>
            )}
          </div>

          <p className="text-xs text-slate-500">{t('profile.dataQualityMissingHint')}</p>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ShieldCheck size={16} className="text-indigo-600" />
              {t('profile.radarTitle')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {frameworkRadarData.length === 0 ? (
              <p className="text-sm text-slate-400">{t('profile.noFrameworkResults')}</p>
            ) : (
              <>
                <ResponsiveContainer width="100%" height={260}>
                  <RadarChart data={frameworkRadarData}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="framework" tick={{ fontSize: 11 }} />
                    <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10 }} />
                    <Radar
                      name={t('common.score')}
                      dataKey="score"
                      stroke="#4f46e5"
                      fill="#4f46e5"
                      fillOpacity={0.35}
                    />
                    <Tooltip formatter={(value) => [`${value}%`, t('common.score')]} />
                  </RadarChart>
                </ResponsiveContainer>
                <p className="mt-2 text-xs text-slate-500">{t('profile.radarLegend')}</p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <TrendingUp size={16} className="text-indigo-600" />
              {t('profile.trendTitle')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={trendData}>
                <XAxis dataKey="year" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="scope1" stroke="#ef4444" strokeWidth={2} dot name="Scope 1" />
                <Line
                  type="monotone"
                  dataKey="renewable"
                  stroke="#16a34a"
                  strokeWidth={2}
                  dot
                  name="Renewable %"
                />
              </LineChart>
            </ResponsiveContainer>
            <p className="mt-2 text-xs text-slate-500">{t('profile.trendLegend')}</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <TrendingUp size={16} className="text-indigo-600" />
            {t('profile.yoyTitle')}
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <div className="rounded-lg border bg-slate-50 px-4 py-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {t('profile.yoyRenewable')}
            </p>
            <p className="mt-2 text-2xl font-semibold text-emerald-600">
              {yoySummary?.renewableDelta != null ? `${yoySummary.renewableDelta >= 0 ? '+' : ''}${yoySummary.renewableDelta.toFixed(1)}%` : '—'}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              {t('profile.yoyComparedTo', { year: yoySummary?.previousYear ?? '—' })}
            </p>
          </div>
          <div className="rounded-lg border bg-slate-50 px-4 py-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {t('profile.yoyScope1')}
            </p>
            <p className={`mt-2 text-2xl font-semibold ${yoySummary?.scope1Delta != null && yoySummary.scope1Delta <= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
              {yoySummary?.scope1Delta != null ? `${yoySummary.scope1Delta >= 0 ? '+' : ''}${yoySummary.scope1Delta.toLocaleString(locale)}` : '—'}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              {t('profile.yoyScope1Hint')}
            </p>
          </div>
          <div className="rounded-lg border bg-slate-50 px-4 py-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {t('profile.yoyTaxonomy')}
            </p>
            <p className="mt-2 text-2xl font-semibold text-indigo-600">
              {yoySummary?.taxonomyDelta != null ? `${yoySummary.taxonomyDelta >= 0 ? '+' : ''}${yoySummary.taxonomyDelta.toFixed(1)}%` : '—'}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              {t('profile.yoyTaxonomyHint')}
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
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheck size={16} className="text-indigo-600" />
            {t('profile.detailTitle')}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {frameworkScores.length === 0 ? (
            <p className="text-sm text-slate-400">{t('profile.noFrameworkResults')}</p>
          ) : (
            frameworkScores.map((framework) => (
              <details
                key={`${framework.framework_id}-${framework.framework_version ?? 'v1'}`}
                className="rounded-md border p-3 open:bg-slate-50"
              >
                <summary className="cursor-pointer list-none">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium text-slate-900">{framework.framework}</p>
                      <p className="text-xs text-slate-500">
                        {t('common.score')}: {(framework.total_score * 100).toFixed(1)}% · {t('profile.detailCoverage')}:{' '}
                        {framework.coverage_pct.toFixed(1)}%
                      </p>
                    </div>
                    <Badge>{framework.grade}</Badge>
                  </div>
                </summary>
                <div className="mt-3 space-y-3">
                  <div className="space-y-2">
                    {framework.dimensions.map((dimension) => (
                      <div key={dimension.name}>
                        <div className="mb-1 flex items-center justify-between text-xs text-slate-600">
                          <span>{dimension.name}</span>
                          <span>
                            {dimension.disclosed}/{dimension.total}
                          </span>
                        </div>
                        <div className="h-2 rounded-full bg-slate-100">
                          <div
                            className="h-2 rounded-full bg-indigo-500"
                            style={{ width: `${Math.round(dimension.score * 100)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                  {framework.gaps.length > 0 && (
                    <div>
                      <p className="mb-1 text-xs font-medium text-slate-700">{t('profile.detailGaps')}</p>
                      <ul className="list-disc space-y-1 pl-5 text-xs text-slate-600">
                        {framework.gaps.map((gap, index) => (
                          <li key={index}>{gap}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {framework.recommendations.length > 0 && (
                    <div>
                      <p className="mb-1 text-xs font-medium text-slate-700">
                        {t('profile.detailRecommendations')}
                      </p>
                      <ul className="list-disc space-y-1 pl-5 text-xs text-slate-600">
                        {framework.recommendations.map((recommendation, index) => (
                          <li key={index}>{recommendation}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <p className="text-xs text-slate-500">
                    {t('profile.frameworkVersion')}: {framework.framework_version ?? 'v1'}
                  </p>
                </div>
              </details>
            ))
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Clock3 size={16} className="text-indigo-600" />
              {t('profile.periodTitle')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {profile.periods.map((p) => (
              <div key={`${p.report_year}-${p.reporting_period_label}`} className="flex items-center justify-between rounded-md border px-3 py-2">
                <div>
                  <p className="text-sm font-medium text-slate-900">{p.reporting_period_label}</p>
                  <p className="text-xs text-slate-500">{p.source_document_type ?? '—'}</p>
                </div>
                <Badge variant="secondary">{p.report_year}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Leaf size={16} className="text-indigo-600" />
              {t('profile.evidenceTitle')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {(profile.evidence_summary ?? []).length === 0 ? (
              <p className="text-sm text-slate-400">{t('profile.noEvidence')}</p>
            ) : (
              profile.evidence_summary.map((e, i) => (
                <div key={i} className="rounded-md border px-3 py-2 text-sm text-slate-700">
                  {String(e.metric ?? t('profile.metricFallback'))} · {String(e.source_type ?? t('profile.sourceFallback'))}
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="border-slate-200 bg-slate-50/70">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileText size={16} className="text-indigo-600" />
            {t('profile.narrativeTitle')}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-5 text-sm text-slate-700">
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
        </CardContent>
      </Card>
    </div>
  )
}

import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Building2, Clock3, Leaf, ShieldCheck, TrendingUp } from 'lucide-react'
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
import type { FrameworkScoreResult } from '@/lib/types'
import { useTranslation } from 'react-i18next'
import { localizeErrorMessage } from '@/lib/error-utils'

function asPct(v: number | null | undefined) {
  return v == null ? '—' : `${v.toFixed(1)}%`
}

function asNum(v: number | null | undefined, locale: string) {
  return v == null ? '—' : v.toLocaleString(locale)
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

  const frameworkRadarData = useMemo(
    () =>
      frameworkScores.map((f) => ({
        framework: f.framework,
        score: Math.round(f.total_score * 100),
      })),
    [frameworkScores]
  )

  if (isLoading) return <p className="text-slate-400">{t('common.loading')}</p>
  if (error) return <p className="text-red-500">{localizeErrorMessage(t, error, 'common.error')}</p>
  if (!profile) return <p className="text-red-500">{t('common.error')}</p>

  const m = profile.latest_metrics

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Link
            to="/companies"
            className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-900"
          >
            <ArrowLeft size={14} />
            {t('profile.backToCompanies')}
          </Link>
          <div className="flex items-center gap-2">
            <Building2 size={20} className="text-indigo-600" />
            <h1 className="text-2xl font-bold text-slate-900">{profile.company_name}</h1>
            <Badge variant="secondary">
              {profile.latest_period.reporting_period_label}
            </Badge>
          </div>
          <p className="text-sm text-slate-500">
            {profile.latest_period.source_document_type ?? '—'} · {profile.latest_year}
          </p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label={t('companies.scope1')} value={asNum(m.scope1_co2e_tonnes, locale)} />
        <MetricCard label={t('companies.scope2')} value={asNum(m.scope2_co2e_tonnes, locale)} />
        <MetricCard label={t('companies.employees')} value={asNum(m.total_employees, locale)} />
        <MetricCard label={t('companies.renewable')} value={asPct(m.renewable_energy_pct)} color="green" />
      </div>

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
    </div>
  )
}

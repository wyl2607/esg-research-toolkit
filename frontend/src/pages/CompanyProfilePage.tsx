import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Building2, Clock3, Leaf, ShieldCheck, TrendingUp } from 'lucide-react'
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { MetricCard } from '@/components/MetricCard'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { getCompanyProfile } from '@/lib/api'
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
        <MetricCard label={t('companies.employees')} value={asNum(m.total_employees, locale)} />
        <MetricCard label={t('companies.renewable')} value={asPct(m.renewable_energy_pct)} color="green" />
        <MetricCard
          label={t('upload.taxonomyAligned')}
          value={asPct(m.taxonomy_aligned_revenue_pct)}
          color="blue"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <TrendingUp size={16} className="text-indigo-600" />
              {t('profile.trendTitle')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={trendData}>
                <XAxis dataKey="year" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="scope1" stroke="#ef4444" strokeWidth={2} dot />
                <Line type="monotone" dataKey="renewable" stroke="#16a34a" strokeWidth={2} dot />
                <Line type="monotone" dataKey="taxonomy" stroke="#4f46e5" strokeWidth={2} dot />
              </LineChart>
            </ResponsiveContainer>
            <p className="mt-2 text-xs text-slate-500">{t('profile.trendLegend')}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ShieldCheck size={16} className="text-indigo-600" />
              {t('profile.frameworkTitle')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {profile.framework_results.length === 0 ? (
              <p className="text-sm text-slate-400">{t('profile.noFrameworkResults')}</p>
            ) : (
              profile.framework_results.map((f) => (
                <div key={`${f.framework_id}-${f.analysis_result_id ?? f.framework_version}`} className="rounded-md border p-3">
                  <div className="flex items-center justify-between">
                    <p className="font-medium text-slate-900">{f.framework}</p>
                    <Badge>{f.grade}</Badge>
                  </div>
                  <p className="mt-1 text-sm text-slate-600">
                    {t('common.score')}: {(f.total_score * 100).toFixed(1)}% · {t('common.coverage')}: {f.coverage_pct.toFixed(1)}%
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {t('profile.frameworkVersion')}: {f.framework_version ?? 'v1'}
                  </p>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

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

import { useMemo } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getCompanyProfile } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Legend,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useTranslation } from 'react-i18next'

function fmtNum(v: number | null | undefined): string {
  return v == null ? '—' : v.toLocaleString()
}

function fmtPct(v: number | null | undefined): string {
  return v == null ? '—' : `${v.toFixed(1)}%`
}

export function CompanyProfilePage() {
  const { t } = useTranslation()
  const nav = useNavigate()
  const { companyName } = useParams<{ companyName: string }>()
  const decodedName = decodeURIComponent(companyName ?? '')

  const { data: profile, isLoading } = useQuery({
    queryKey: ['profile', decodedName],
    queryFn: () => getCompanyProfile(decodedName),
    enabled: !!decodedName,
  })

  const frameworkRadar = useMemo(
    () =>
      (profile?.framework_scores ?? []).map((score) => ({
        framework: score.framework_id.toUpperCase(),
        score: Math.round(score.total_score * 100),
      })),
    [profile]
  )

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12 rounded-lg" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((k) => (
            <Skeleton key={k} className="h-24 rounded-lg" />
          ))}
        </div>
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <Skeleton className="h-80 rounded-lg" />
          <Skeleton className="h-80 rounded-lg" />
        </div>
      </div>
    )
  }

  if (!profile) {
    return <p className="text-slate-400">{t('common.noData')}</p>
  }

  const metrics = profile.latest_metrics

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            {profile.company_name} · {profile.latest_year}
          </h1>
          <p className="text-sm text-slate-500">
            {t('profile.yearsAvailable')}: {profile.years_available.join(', ')}
          </p>
        </div>
        <button
          type="button"
          onClick={() => nav('/companies')}
          className="self-start rounded border bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
        >
          {t('profile.backToList')}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-slate-500">{t('companies.scope1')}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{fmtNum(metrics.scope1_co2e_tonnes)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-slate-500">{t('companies.scope2')}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{fmtNum(metrics.scope2_co2e_tonnes)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-slate-500">{t('companies.renewable')}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{fmtPct(metrics.renewable_energy_pct)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-slate-500">{t('companies.employees')}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{fmtNum(metrics.total_employees)}</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">{t('profile.frameworkRadar')}</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={frameworkRadar}>
                <PolarGrid />
                <PolarAngleAxis dataKey="framework" tick={{ fontSize: 11 }} />
                <Radar
                  name={t('common.score')}
                  dataKey="score"
                  stroke="#2563eb"
                  fill="#2563eb"
                  fillOpacity={0.24}
                />
                <Tooltip formatter={(v) => [`${v}%`, t('common.score')]} />
              </RadarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">{t('profile.trendChart')}</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={profile.trend}>
                <XAxis dataKey="year" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="scope1" stroke="#ef4444" name="Scope 1" dot />
                <Line
                  type="monotone"
                  dataKey="renewable_pct"
                  stroke="#22c55e"
                  name="Renewable %"
                  dot
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{t('profile.frameworkDetails')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {profile.framework_scores.map((fw) => (
            <details key={fw.framework_id} className="rounded border bg-slate-50 px-3 py-2">
              <summary className="flex cursor-pointer items-center justify-between gap-3 font-medium text-slate-800">
                <span>{fw.framework}</span>
                <Badge variant="secondary">{fw.grade}</Badge>
              </summary>
              <div className="mt-3 space-y-3 text-sm">
                <div>
                  <div className="text-xs text-slate-500 mb-1">{t('profile.totalScore')}</div>
                  <div className="font-semibold">{Math.round(fw.total_score * 100)}%</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mb-1">{t('profile.dimensions')}</div>
                  <ul className="space-y-1">
                    {fw.dimensions.map((dim) => (
                      <li key={dim.name} className="flex justify-between">
                        <span>{dim.name}</span>
                        <span>{Math.round(dim.score * 100)}%</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </details>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

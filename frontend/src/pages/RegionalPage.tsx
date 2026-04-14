import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { Globe, TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react'

import { listCompanies, getRegionalComparison } from '@/lib/api'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { QueryStateCard } from '@/components/QueryStateCard'
import { localizeErrorMessage, isBackendOffline } from '@/lib/error-utils'
import { BackendOfflineBanner } from '@/components/BackendOfflineBanner'

export function RegionalPage() {
  const { t } = useTranslation()
  const [selected, setSelected] = useState('')

  const {
    data: companies = [],
    error: companiesError,
    refetch: refetchCompanies,
  } = useQuery({ queryKey: ['companies'], queryFn: listCompanies })

  const [companyName, companyYear] = selected ? selected.split('|') : [null, null]

  const {
    data: report,
    isLoading,
    error: reportError,
    refetch: refetchReport,
  } = useQuery({
    queryKey: ['regional', companyName, companyYear],
    queryFn: () => getRegionalComparison(companyName!, Number(companyYear)),
    enabled: !!companyName && !!companyYear,
  })

  const backendOffline = isBackendOffline(companiesError) || isBackendOffline(reportError)

  const radarData =
    report?.cross_matrix.map((m) => ({
      dimension: m.dimension_name,
      EU: m.eu_score != null ? Math.round(m.eu_score * 100) : 0,
      CN: m.cn_score != null ? Math.round(m.cn_score * 100) : 0,
      US: m.us_score != null ? Math.round(m.us_score * 100) : 0,
    })) ?? []

  const readinessBorderClass =
    report?.overall_readiness === 'Leading'
      ? 'border-green-500'
      : report?.overall_readiness === 'High'
        ? 'border-blue-500'
        : report?.overall_readiness === 'Medium'
          ? 'border-yellow-500'
          : 'border-red-500'

  return (
    <div className="space-y-8">
      <section className="editorial-panel space-y-4">
        <div className="flex items-center gap-3">
          <Globe className="text-amber-700" size={28} />
          <div>
            <p className="section-kicker">{t('regional.kicker')}</p>
            <h1 className="text-4xl text-slate-900">{t('regional.title')}</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              {t('regional.subtitle')}
            </p>
          </div>
        </div>
      </section>

      {backendOffline ? (
        <BackendOfflineBanner />
      ) : (companiesError || reportError) ? (
        <QueryStateCard
          tone="error"
          title={t('common.error')}
          body={localizeErrorMessage(t, reportError ?? companiesError, 'common.error')}
          actionLabel={t('errorBoundary.retry')}
          onAction={() => {
            if (reportError) {
              void refetchReport()
            } else {
              void refetchCompanies()
            }
          }}
          className="max-w-2xl"
        />
      ) : null}

      <div className="surface-card max-w-xl">
        <Select value={selected} onValueChange={setSelected}>
          <SelectTrigger className="w-full border-stone-300 bg-white/90">
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

      {companies.length === 0 && !companiesError && !backendOffline ? (
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
          body={t('regional.subtitle')}
          className="max-w-2xl"
        />
      ) : null}

      {report && (
        <div className="space-y-6">
          <Card className={`surface-card border-l-4 ${readinessBorderClass}`}>
            <CardContent className="flex items-center justify-between pt-4">
              <div>
                <p className="text-sm text-slate-500">{t('regional.overallReadiness')}</p>
                <p className="text-2xl font-bold text-slate-900">{report.overall_readiness}</p>
              </div>
              <div className="text-right text-sm text-slate-500">
                {report.company_name} · {report.report_year}
              </div>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {report.regional_groups.map((g) => (
              <Card key={g.region} className="surface-card">
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <span
                      className="inline-block h-3 w-3 rounded-full"
                      style={{
                        backgroundColor:
                          g.region === 'EU'
                            ? '#b45309'
                            : g.region === 'CN'
                              ? '#dc2626'
                              : g.region === 'US'
                                ? '#65a30d'
                                : '#d97706',
                      }}
                    />
                    {g.region}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold text-slate-900">{g.avg_grade}</p>
                  <p className="text-lg text-slate-600">{Math.round(g.avg_score * 100)}%</p>
                  <p className="mt-1 text-xs text-slate-400">↑ {g.strongest_area}</p>
                  <p className="text-xs text-red-400">↓ {g.weakest_area}</p>
                  <div className="mt-2 space-y-1">
                    {g.frameworks.map((f) => (
                      <div key={f.framework_id} className="flex justify-between gap-2 text-xs">
                        <span className="truncate text-slate-600">{f.framework}</span>
                        <span className="shrink-0 font-medium">{f.grade}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card className="editorial-panel">
              <CardHeader>
                <CardTitle className="text-base">{t('regional.dimensionRadar')}</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={280}>
                  <RadarChart data={radarData}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 9 }} tickFormatter={(v: string) => v.length > 10 ? v.slice(0, 9) + '…' : v} />
                    <Radar name="EU" dataKey="EU" stroke="#b45309" fill="#d97706" fillOpacity={0.16} />
                    <Radar name="CN" dataKey="CN" stroke="#b91c1c" fill="#dc2626" fillOpacity={0.12} />
                    <Radar name="US" dataKey="US" stroke="#4d7c0f" fill="#65a30d" fillOpacity={0.12} />
                    <Legend />
                  </RadarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card className="editorial-panel">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <TrendingUp size={16} className="text-amber-700" />
                  {t('regional.keyInsights')}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {report.key_insights.map((insight, i) => (
                  <div key={`${insight}-${i}`} className="flex gap-2 text-sm">
                    <CheckCircle size={14} className="mt-0.5 shrink-0 text-green-500" />
                    <span className="text-slate-600">{insight}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          <Card className="editorial-panel">
            <CardHeader>
              <CardTitle className="text-base">{t('regional.crossMatrix')}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-stone-200 text-slate-500">
                      <th className="py-2 pr-4 text-left font-medium">{t('regional.dimension')}</th>
                      <th className="py-2 pr-4 text-left font-medium text-amber-700">EU</th>
                      <th className="py-2 pr-4 text-left font-medium text-red-600">CN</th>
                      <th className="py-2 pr-4 text-left font-medium text-green-700">US</th>
                      <th className="py-2 text-left font-medium">{t('regional.gapAnalysis')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.cross_matrix.map((row, i) => (
                      <tr
                        key={`${row.dimension_name}-${i}`}
                        className="align-top border-b border-stone-200 last:border-0"
                      >
                        <td className="py-3 pr-4 font-medium text-slate-800">{row.dimension_name}</td>
                        <td className="max-w-[160px] py-3 pr-4 text-xs text-slate-600">
                          {row.eu_requirement}
                        </td>
                        <td className="max-w-[160px] py-3 pr-4 text-xs text-slate-600">
                          {row.cn_requirement}
                        </td>
                        <td className="max-w-[160px] py-3 pr-4 text-xs text-slate-600">
                          {row.us_requirement}
                        </td>
                        <td className="py-3 text-xs text-slate-500">{row.gap_analysis}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {report.compliance_priority.length > 0 && (
            <Card className="rounded-2xl border-orange-200 bg-orange-50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base text-orange-700">
                  <AlertTriangle size={16} />
                  {t('regional.compliancePriority')}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {report.compliance_priority.map((item, i) => (
                  <div key={`${item}-${i}`} className="flex items-start gap-2 text-sm text-orange-800">
                    <span className="shrink-0 font-bold">{i + 1}.</span>
                    <span>{item}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {!selected && <p className="py-12 text-center text-slate-400">{t('regional.selectPrompt')}</p>}
    </div>
  )
}

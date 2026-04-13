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
import { localizeErrorMessage } from '@/lib/error-utils'

export function RegionalPage() {
  const { t } = useTranslation()
  const [selected, setSelected] = useState('')

  const {
    data: companies = [],
    error: companiesError,
  } = useQuery({ queryKey: ['companies'], queryFn: listCompanies })

  const [companyName, companyYear] = selected ? selected.split('|') : [null, null]

  const {
    data: report,
    isLoading,
    error: reportError,
  } = useQuery({
    queryKey: ['regional', companyName, companyYear],
    queryFn: () => getRegionalComparison(companyName!, Number(companyYear)),
    enabled: !!companyName && !!companyYear,
  })

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
      <div className="flex items-center gap-3">
        <Globe className="text-indigo-500" size={28} />
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{t('regional.title')}</h1>
          <p className="text-slate-500 text-sm">{t('regional.subtitle')}</p>
        </div>
      </div>

      {(companiesError || reportError) && (
        <p className="text-red-500 text-sm">
          {localizeErrorMessage(t, reportError ?? companiesError, 'common.error')}
        </p>
      )}

      <Select value={selected} onValueChange={setSelected}>
        <SelectTrigger className="w-72">
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

      {isLoading && <p className="text-slate-400">{t('common.loading')}</p>}

      {report && (
        <div className="space-y-6">
          <Card className={`border-l-4 ${readinessBorderClass}`}>
            <CardContent className="pt-4 flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">{t('regional.overallReadiness')}</p>
                <p className="text-2xl font-bold text-slate-900">{report.overall_readiness}</p>
              </div>
              <div className="text-right text-sm text-slate-500">
                {report.company_name} · {report.report_year}
              </div>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {report.regional_groups.map((g) => (
              <Card key={g.region}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base flex items-center gap-2">
                    <span
                      className="w-3 h-3 rounded-full inline-block"
                      style={{
                        backgroundColor:
                          g.region === 'EU'
                            ? '#6366f1'
                            : g.region === 'CN'
                              ? '#ef4444'
                              : g.region === 'US'
                                ? '#22c55e'
                                : '#f59e0b',
                      }}
                    />
                    {g.region}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold text-slate-900">{g.avg_grade}</p>
                  <p className="text-lg text-slate-600">{Math.round(g.avg_score * 100)}%</p>
                  <p className="text-xs text-slate-400 mt-1">↑ {g.strongest_area}</p>
                  <p className="text-xs text-red-400">↓ {g.weakest_area}</p>
                  <div className="mt-2 space-y-1">
                    {g.frameworks.map((f) => (
                      <div key={f.framework_id} className="flex justify-between text-xs gap-2">
                        <span className="text-slate-600 truncate">{f.framework}</span>
                        <span className="font-medium shrink-0">{f.grade}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">{t('regional.dimensionRadar')}</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={280}>
                  <RadarChart data={radarData}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 11 }} />
                    <Radar name="EU" dataKey="EU" stroke="#6366f1" fill="#6366f1" fillOpacity={0.2} />
                    <Radar name="CN" dataKey="CN" stroke="#ef4444" fill="#ef4444" fillOpacity={0.2} />
                    <Radar name="US" dataKey="US" stroke="#22c55e" fill="#22c55e" fillOpacity={0.2} />
                    <Legend />
                  </RadarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <TrendingUp size={16} className="text-indigo-500" />
                  {t('regional.keyInsights')}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {report.key_insights.map((insight, i) => (
                  <div key={`${insight}-${i}`} className="flex gap-2 text-sm">
                    <CheckCircle size={14} className="text-green-500 mt-0.5 shrink-0" />
                    <span className="text-slate-600">{insight}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t('regional.crossMatrix')}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-slate-500">
                      <th className="text-left py-2 pr-4 font-medium">{t('regional.dimension')}</th>
                      <th className="text-left py-2 pr-4 font-medium text-indigo-600">🇪🇺 EU</th>
                      <th className="text-left py-2 pr-4 font-medium text-red-600">🇨🇳 CN</th>
                      <th className="text-left py-2 pr-4 font-medium text-green-600">🇺🇸 US</th>
                      <th className="text-left py-2 font-medium">{t('regional.gapAnalysis')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.cross_matrix.map((row, i) => (
                      <tr key={`${row.dimension_name}-${i}`} className="border-b last:border-0 align-top">
                        <td className="py-3 pr-4 font-medium text-slate-800">{row.dimension_name}</td>
                        <td className="py-3 pr-4 text-slate-600 text-xs max-w-[160px]">{row.eu_requirement}</td>
                        <td className="py-3 pr-4 text-slate-600 text-xs max-w-[160px]">{row.cn_requirement}</td>
                        <td className="py-3 pr-4 text-slate-600 text-xs max-w-[160px]">{row.us_requirement}</td>
                        <td className="py-3 text-xs text-slate-500">{row.gap_analysis}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {report.compliance_priority.length > 0 && (
            <Card className="border-orange-200 bg-orange-50">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2 text-orange-700">
                  <AlertTriangle size={16} />
                  {t('regional.compliancePriority')}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {report.compliance_priority.map((item, i) => (
                  <div key={`${item}-${i}`} className="flex items-start gap-2 text-sm text-orange-800">
                    <span className="font-bold shrink-0">{i + 1}.</span>
                    <span>{item}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {!selected && <p className="text-slate-400 text-center py-12">{t('regional.selectPrompt')}</p>}
    </div>
  )
}

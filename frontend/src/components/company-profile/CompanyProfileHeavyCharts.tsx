import { ShieldCheck, TrendingUp } from 'lucide-react'
import {
  Legend,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

type FrameworkRadarDatum = {
  framework: string
  score: number
}

type TrendDatum = {
  year: number
  scope1: number | null
  renewable: number | null
  taxonomy: number | null
}

interface CompanyProfileHeavyChartsProps {
  frameworkRadarData: FrameworkRadarDatum[]
  trendData: TrendDatum[]
  radarTitle: string
  trendTitle: string
  radarLegend: string
  trendLegend: string
  noFrameworkResultsLabel: string
  scoreLabel: string
  scope1Label: string
  renewableLabel: string
}

export function CompanyProfileHeavyCharts({
  frameworkRadarData,
  trendData,
  radarTitle,
  trendTitle,
  radarLegend,
  trendLegend,
  noFrameworkResultsLabel,
  scoreLabel,
  scope1Label,
  renewableLabel,
}: CompanyProfileHeavyChartsProps) {
  const tooltipValueLabel = (value: unknown) => {
    if (Array.isArray(value)) return value.map((item) => String(item)).join(', ')
    if (value == null) return '—'
    if (typeof value === 'string') return value
    if (typeof value === 'number') {
      if (Number.isNaN(value)) return '—'
      return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(1)
    }
    return String(value)
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheck size={16} className="text-indigo-600" />
            {radarTitle}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {frameworkRadarData.length === 0 ? (
            <p className="text-sm text-slate-400">{noFrameworkResultsLabel}</p>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={260} minWidth={0} minHeight={0}>
                <RadarChart data={frameworkRadarData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="framework" tick={{ fontSize: 11 }} />
                  <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10 }} />
                  <Radar
                    name={scoreLabel}
                    dataKey="score"
                    stroke="#4f46e5"
                    fill="#4f46e5"
                    fillOpacity={0.35}
                  />
                  <Tooltip formatter={(value) => [`${value}%`, scoreLabel]} />
                </RadarChart>
              </ResponsiveContainer>
              <p className="mt-2 text-xs text-slate-500">{radarLegend}</p>
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <TrendingUp size={16} className="text-indigo-600" />
            {trendTitle}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3" data-testid="company-profile-trend-chart">
          <ResponsiveContainer width="100%" height={260} minWidth={0} minHeight={0}>
            <LineChart data={trendData}>
              <XAxis dataKey="year" type="number" allowDecimals={false} />
              <YAxis domain={['auto', 'auto']} />
              <Tooltip
                labelFormatter={(year) => `Year ${year}`}
                formatter={(value: unknown, name: unknown) => [
                  tooltipValueLabel(value),
                  String(name ?? ''),
                ]}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="scope1"
                stroke="#ef4444"
                strokeWidth={2}
                dot={{ r: 4 }}
                connectNulls={false}
                name={scope1Label}
              />
              <Line
                type="monotone"
                dataKey="renewable"
                stroke="#16a34a"
                strokeWidth={2}
                dot={{ r: 4 }}
                connectNulls={false}
                name={renewableLabel}
              />
            </LineChart>
          </ResponsiveContainer>
          <p className="mt-2 text-xs text-slate-500">{trendLegend}</p>
        </CardContent>
      </Card>
    </div>
  )
}

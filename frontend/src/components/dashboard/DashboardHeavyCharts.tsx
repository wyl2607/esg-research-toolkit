import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { UploadCloud } from 'lucide-react'

import { CHART, CHART_TICK, CHART_TICK_STRONG, CHART_TOOLTIP_STYLE } from '@/lib/chart-theme'
import { useFormatters } from '@/lib/use-formatters'
import { UNITS } from '@/lib/units'

type YearlyTrendItem = { year: number; count: number }
type TopEmitterItem = { company: string; year: number; scope1: number }
type TopEmitterChartItem = TopEmitterItem & { label: string }

interface DashboardHeavyChartsProps {
  yearlyTrend: YearlyTrendItem[]
  topEmitters: TopEmitterItem[]
  yearlyTrendLabel: string
  topEmittersLabel: string
  uploadsLabel: string
  chartsEmptyTitle: string
  chartsEmptyBody: string
}

/**
 * Company labels are truncated by character count because the Y axis has a
 * fixed pixel width. The year suffix is always kept — two rows for the same
 * company are only distinguishable by it.
 */
function truncateCompanyLabel(value: string) {
  const yearSuffix = value.match(/(.*)( ·\d{2})$/)
  if (yearSuffix) {
    const [, company, suffix] = yearSuffix
    const maxCompanyLength = 13
    const companyLabel =
      company.length > maxCompanyLength ? `${company.slice(0, maxCompanyLength)}…` : company
    return `${companyLabel}${suffix}`
  }
  return value.length > 18 ? `${value.slice(0, 17)}…` : value
}

function formatEmitterLabel(item: TopEmitterItem) {
  return `${item.company} ·${String(item.year).slice(-2)}`
}

function ChartEmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="flex h-64 flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-stone-300 bg-stone-50/60 px-6 text-center dark:border-slate-600 dark:bg-slate-800/40">
      <UploadCloud size={32} className="text-stone-400 dark:text-slate-500" aria-hidden="true" />
      <p className="text-sm font-medium text-stone-600 dark:text-slate-300">{title}</p>
      <p className="max-w-xs text-xs leading-5 text-stone-400 dark:text-slate-400">{body}</p>
    </div>
  )
}

/**
 * Both chart cards use this header so their plot areas start at the same
 * height. Previously only the emitters card carried a unit line, which pushed
 * the two charts in the same row out of alignment by exactly one line.
 */
function ChartCardHeader({ title, unit, id }: { title: string; unit: string; id: string }) {
  return (
    <div className="mb-4 space-y-1">
      <h2
        id={id}
        className="text-lg font-semibold leading-tight text-stone-900 dark:text-slate-100"
      >
        {title}
      </h2>
      <p className="numeric-mono text-xs text-stone-500 dark:text-slate-400">{unit}</p>
    </div>
  )
}

export function DashboardHeavyCharts({
  yearlyTrend,
  topEmitters,
  yearlyTrendLabel,
  topEmittersLabel,
  uploadsLabel,
  chartsEmptyTitle,
  chartsEmptyBody,
}: DashboardHeavyChartsProps) {
  const fmt = useFormatters()
  const topEmitterChartData: TopEmitterChartItem[] = topEmitters.map((item) => ({
    ...item,
    label: formatEmitterLabel(item),
  }))

  // One divisor for the whole axis: every tick then reads in the same form,
  // and the magnitude is named once in the axis unit instead of appearing on
  // some ticks but not others.
  const emitterScale = fmt.axisScale(
    topEmitterChartData.reduce((max, item) => Math.max(max, item.scope1 ?? 0), 0)
  )
  const emitterUnit = emitterScale.suffix
    ? `${emitterScale.suffix} ${UNITS.tco2e}`
    : UNITS.tco2e

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <section className="editorial-panel p-6" aria-labelledby="yearly-trend-title">
        <ChartCardHeader id="yearly-trend-title" title={yearlyTrendLabel} unit={uploadsLabel} />
        {yearlyTrend.length === 0 ? (
          <ChartEmptyState title={chartsEmptyTitle} body={chartsEmptyBody} />
        ) : (
          <div className="h-56 md:h-64">
            <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
              <BarChart data={yearlyTrend} role="img" aria-label={yearlyTrendLabel}>
                <CartesianGrid stroke={CHART.grid} strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="year"
                  tickFormatter={(value: number) => fmt.year(value)}
                  tick={CHART_TICK}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  allowDecimals={false}
                  tickFormatter={(value: number) => fmt.number(value)}
                  tick={CHART_TICK}
                  axisLine={false}
                  tickLine={false}
                  width={32}
                />
                <Tooltip
                  cursor={{ fill: CHART.grid, fillOpacity: 0.25 }}
                  formatter={(value) => [fmt.number(Number(value)), uploadsLabel]}
                  labelFormatter={(label) => fmt.year(Number(label))}
                  contentStyle={CHART_TOOLTIP_STYLE}
                />
                <Bar
                  dataKey="count"
                  fill={CHART.series1}
                  name={uploadsLabel}
                  radius={[6, 6, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      <section className="editorial-panel p-6" aria-labelledby="top-emitters-title">
        <ChartCardHeader id="top-emitters-title" title={topEmittersLabel} unit={emitterUnit} />
        {topEmitterChartData.length === 0 ? (
          <ChartEmptyState title={chartsEmptyTitle} body={chartsEmptyBody} />
        ) : (
          <div className="h-56 md:h-64">
            <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
              <BarChart
                data={topEmitterChartData}
                layout="vertical"
                margin={{ top: 8, right: 16, left: 8, bottom: 8 }}
                role="img"
                aria-label={topEmittersLabel}
              >
                <CartesianGrid stroke={CHART.grid} strokeDasharray="3 3" horizontal={false} />
                <XAxis
                  type="number"
                  tickFormatter={(value: number) =>
                    fmt.number(value / emitterScale.divisor, { fractionDigits: 1 })
                  }
                  tick={CHART_TICK}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="label"
                  width={140}
                  tickFormatter={truncateCompanyLabel}
                  tick={CHART_TICK_STRONG}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  cursor={{ fill: CHART.grid, fillOpacity: 0.25 }}
                  formatter={(value) => [fmt.measure(Number(value), 'tco2e'), 'Scope 1']}
                  labelFormatter={(label) => String(label)}
                  contentStyle={CHART_TOOLTIP_STYLE}
                />
                <Bar
                  dataKey="scope1"
                  name={`Scope 1 (${UNITS.tco2e})`}
                  fill={CHART.series2}
                  radius={[0, 6, 6, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>
    </div>
  )
}

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { UploadCloud } from 'lucide-react'

type YearlyTrendItem = { year: number; count: number }
type TopEmitterItem = { company: string; year: number; scope1: number }

interface DashboardHeavyChartsProps {
  yearlyTrend: YearlyTrendItem[]
  topEmitters: TopEmitterItem[]
  yearlyTrendLabel: string
  topEmittersLabel: string
  uploadsLabel: string
  chartsEmptyTitle: string
  chartsEmptyBody: string
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

export function DashboardHeavyCharts({
  yearlyTrend,
  topEmitters,
  yearlyTrendLabel,
  topEmittersLabel,
  uploadsLabel,
  chartsEmptyTitle,
  chartsEmptyBody,
}: DashboardHeavyChartsProps) {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <section className="editorial-panel p-4 md:p-5" aria-labelledby="yearly-trend-title">
        <h2 id="yearly-trend-title" className="mb-3 text-2xl font-semibold text-stone-900 dark:text-slate-100">
          {yearlyTrendLabel}
        </h2>
        {yearlyTrend.length === 0 ? (
          <ChartEmptyState title={chartsEmptyTitle} body={chartsEmptyBody} />
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
              <BarChart data={yearlyTrend} role="img" aria-label={yearlyTrendLabel}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="year" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" fill="#b45309" name={uploadsLabel} radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      <section className="editorial-panel p-4 md:p-5" aria-labelledby="top-emitters-title">
        <h2 id="top-emitters-title" className="mb-3 text-2xl font-semibold text-stone-900 dark:text-slate-100">
          {topEmittersLabel}
        </h2>
        {topEmitters.length === 0 ? (
          <ChartEmptyState title={chartsEmptyTitle} body={chartsEmptyBody} />
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
              <BarChart
                data={topEmitters}
                layout="vertical"
                margin={{ top: 8, right: 16, left: 24, bottom: 8 }}
                role="img"
                aria-label={topEmittersLabel}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" />
                <YAxis type="category" dataKey="company" width={100} />
                <Tooltip />
                <Bar dataKey="scope1" name="Scope 1 (tCO₂e)" radius={[0, 6, 6, 0]}>
                  {topEmitters.map((entry) => (
                    <Cell key={`${entry.company}-${entry.year}`} fill="#ef4444" />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>
    </div>
  )
}

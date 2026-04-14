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

type YearlyTrendItem = { year: number; count: number }
type TopEmitterItem = { company: string; year: number; scope1: number }

interface DashboardHeavyChartsProps {
  yearlyTrend: YearlyTrendItem[]
  topEmitters: TopEmitterItem[]
  yearlyTrendLabel: string
  topEmittersLabel: string
  uploadsLabel: string
}

export function DashboardHeavyCharts({
  yearlyTrend,
  topEmitters,
  yearlyTrendLabel,
  topEmittersLabel,
  uploadsLabel,
}: DashboardHeavyChartsProps) {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <section className="editorial-panel p-4 md:p-5" aria-labelledby="yearly-trend-title">
        <h2 id="yearly-trend-title" className="mb-3 text-2xl font-semibold text-stone-900">
          {yearlyTrendLabel}
        </h2>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={yearlyTrend} role="img" aria-label={yearlyTrendLabel}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="year" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#b45309" name={uploadsLabel} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="editorial-panel p-4 md:p-5" aria-labelledby="top-emitters-title">
        <h2 id="top-emitters-title" className="mb-3 text-2xl font-semibold text-stone-900">
          {topEmittersLabel}
        </h2>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
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
      </section>
    </div>
  )
}

import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { calcLcoe, calcSensitivity, getBenchmarks } from '@/lib/api'
import { MetricCard } from '@/components/MetricCard'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import type { LCOEInput } from '@/lib/types'
import { useTranslation } from 'react-i18next'

const TECHNOLOGIES = [
  'solar_pv',
  'wind_onshore',
  'wind_offshore',
  'battery_storage',
]

const DEFAULTS: LCOEInput = {
  technology: 'solar_pv',
  capacity_mw: 100,
  capacity_factor: 0.22,
  capex_eur_per_kw: 800,
  opex_eur_per_kw_year: 16,
  lifetime_years: 25,
  discount_rate: 0.05,
}

const FIELD_CONFIG: [keyof LCOEInput, string, string][] = [
  ['capacity_mw', 'capacity_mw', '0.1'],
  ['capacity_factor', 'lcoe.capacityFactor', '0.01'],
  ['capex_eur_per_kw', 'lcoe.capex', '1'],
  ['opex_eur_per_kw_year', 'lcoe.opex', '0.1'],
  ['lifetime_years', 'lcoe.lifetime', '1'],
  ['discount_rate', 'lcoe.discountRate', '0.001'],
]

const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444']

export function LcoePage() {
  const { t } = useTranslation()
  const [form, setForm] = useState<LCOEInput>(DEFAULTS)

  const lcoeMutation = useMutation({ mutationFn: calcLcoe })
  const sensitivityMutation = useMutation({ mutationFn: calcSensitivity })

  const { data: benchmarks } = useQuery({
    queryKey: ['benchmarks'],
    queryFn: getBenchmarks,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    lcoeMutation.mutate(form)
    sensitivityMutation.mutate(form)
  }

  const loadBenchmark = () => {
    if (benchmarks?.[form.technology]) setForm(benchmarks[form.technology])
  }

  // Build chart data: merge sensitivity series by index
  const sensitivityChartData = sensitivityMutation.data
    ? sensitivityMutation.data[0]?.values.map((_, idx) => {
        const point: Record<string, number> = { idx }
        sensitivityMutation.data!.forEach((s) => {
          point[s.parameter] = s.lcoe_results[idx]
          point[`${s.parameter}_x`] = s.values[idx]
        })
        return point
      })
    : []

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-slate-900">{t('lcoe.title')}</h1>

      <div className="grid grid-cols-2 gap-8">
        {/* Input form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4 items-end">
            <div>
              <Label>{t('lcoe.technology')}</Label>
              <Select
                value={form.technology}
                onValueChange={(v) => setForm((f) => ({ ...f, technology: v }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TECHNOLOGIES.map((t) => (
                    <SelectItem key={t} value={t}>
                      {t.replace(/_/g, ' ')}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button type="button" variant="outline" onClick={loadBenchmark}>
              {t('lcoe.loadBenchmark')}
            </Button>
          </div>

          {FIELD_CONFIG.map(([key, labelKey, step]) => (
            <div key={key}>
              <Label>{labelKey === 'capacity_mw' ? 'Capacity (MW)' : t(labelKey)}</Label>
              <Input
                type="number"
                step={step}
                value={form[key] as number}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    [key]: parseFloat(e.target.value) || 0,
                  }))
                }
              />
            </div>
          ))}

          <Button
            type="submit"
            disabled={lcoeMutation.isPending}
            className="w-full"
          >
            {lcoeMutation.isPending ? t('lcoe.calculating') : t('lcoe.calculate')}
          </Button>
        </form>

        {/* Results */}
        <div className="space-y-4">
          {lcoeMutation.data ? (
            <div className="grid grid-cols-2 gap-3">
              <MetricCard
                label={t('lcoe.lcoe')}
                value={`€${lcoeMutation.data.lcoe_eur_per_mwh.toFixed(1)}/MWh`}
                color="blue"
              />
              <MetricCard
                label={t('lcoe.npv')}
                value={`€${(lcoeMutation.data.npv_eur / 1e6).toFixed(1)}M`}
                color={lcoeMutation.data.npv_eur > 0 ? 'green' : 'red'}
              />
              <MetricCard
                label={t('lcoe.irr')}
                value={`${(lcoeMutation.data.irr * 100).toFixed(1)}%`}
                color="blue"
              />
              <MetricCard
                label={t('lcoe.payback')}
                value={`${lcoeMutation.data.payback_years.toFixed(1)} ${t('lcoe.years')}`}
              />
            </div>
          ) : (
            <p className="text-slate-400 text-center py-8">
              {t('common.noData')}
            </p>
          )}
        </div>
      </div>

      {sensitivityMutation.data && sensitivityChartData.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">{t('lcoe.sensitivityAnalysis')}</h2>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={sensitivityChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="idx" hide />
              <YAxis
                label={{
                  value: '€/MWh',
                  angle: -90,
                  position: 'insideLeft',
                }}
              />
              <Tooltip />
              <Legend />
              {sensitivityMutation.data.map((s, i) => (
                <Line
                  key={s.parameter}
                  type="monotone"
                  dataKey={s.parameter}
                  stroke={COLORS[i % COLORS.length]}
                  dot={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

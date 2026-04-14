import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { calcLcoe, calcSensitivity, getBenchmarks } from '@/lib/api'
import { MetricCard } from '@/components/MetricCard'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
import { localizeErrorMessage } from '@/lib/error-utils'
import { Badge } from '@/components/ui/badge'
import { CircleAlert, FlaskConical, LineChart as LineChartIcon } from 'lucide-react'

const TECHNOLOGIES = [
  'solar_pv',
  'wind_onshore',
  'wind_offshore',
  'battery_storage',
]

const TECH_LABEL_KEYS: Record<string, string> = {
  solar_pv: 'lcoe.technologyOptions.solarPv',
  wind_onshore: 'lcoe.technologyOptions.windOnshore',
  wind_offshore: 'lcoe.technologyOptions.windOffshore',
  battery_storage: 'lcoe.technologyOptions.batteryStorage',
}

const DEFAULTS: LCOEInput = {
  technology: 'solar_pv',
  capacity_mw: 100,
  capacity_factor: 0.22,
  capex_eur_per_kw: 800,
  opex_eur_per_kw_year: 16,
  lifetime_years: 25,
  discount_rate: 0.05,
  electricity_price_eur_per_mwh: 95,
  currency: 'EUR',
  reference_fx_to_eur: 1.0,
}

// Reference FX rates (annual avg 2023, EUR as base)
const FX_PRESETS: Record<'EUR' | 'USD' | 'CNY', { label: string; fx: number }> = {
  EUR: { label: '1 EUR = 1.000 EUR', fx: 1.0 },
  USD: { label: '1 USD ≈ 0.920 EUR (2023 avg)', fx: 0.920 },
  CNY: { label: '1 CNY ≈ 0.127 EUR (2023 avg)', fx: 0.127 },
}

// German EPEX SPOT annual average day-ahead prices (€/MWh)
const DE_MARKET_PRICES: { year: number; price: number; note?: string }[] = [
  { year: 2021, price: 96 },
  { year: 2022, price: 235, note: '⚡ energy crisis' },
  { year: 2023, price: 95 },
  { year: 2024, price: 65 },
]

// China wholesale annual avg electricity prices (¥/MWh, source: CEPCI / NEA)
const CN_MARKET_PRICES: { year: number; price: number }[] = [
  { year: 2021, price: 346 },
  { year: 2022, price: 382 },
  { year: 2023, price: 363 },
  { year: 2024, price: 370 },
]

const FIELD_CONFIG: [keyof LCOEInput, string, string][] = [
  ['capacity_mw', 'capacity_mw', '0.1'],
  ['capacity_factor', 'lcoe.capacityFactor', '0.01'],
  ['capex_eur_per_kw', 'lcoe.capex', '1'],
  ['opex_eur_per_kw_year', 'lcoe.opex', '0.1'],
  ['lifetime_years', 'lcoe.lifetime', '1'],
  ['discount_rate', 'lcoe.discountRate', '0.001'],
  ['electricity_price_eur_per_mwh', 'lcoe.electricityPrice', '1'],
]

const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444']

const FIELD_UNIT_KEYS: Partial<Record<keyof LCOEInput, string>> = {
  capacity_mw: 'lcoe.unitMw',
  capacity_factor: 'lcoe.unitRatio',
  capex_eur_per_kw: 'lcoe.unitEurPerKw',
  opex_eur_per_kw_year: 'lcoe.unitEurPerKwYear',
  lifetime_years: 'lcoe.unitYears',
  discount_rate: 'lcoe.unitPercentApprox',
  electricity_price_eur_per_mwh: 'lcoe.unitEurPerMwh',
}

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

  const validationMessages = [
    form.capacity_mw > 0 ? null : t('lcoe.validation.capacity'),
    form.capacity_factor > 0 && form.capacity_factor <= 1 ? null : t('lcoe.validation.capacityFactor'),
    form.capex_eur_per_kw > 0 ? null : t('lcoe.validation.capex'),
    form.opex_eur_per_kw_year >= 0 ? null : t('lcoe.validation.opex'),
    form.lifetime_years > 0 ? null : t('lcoe.validation.lifetime'),
    form.discount_rate >= 0 && form.discount_rate < 1 ? null : t('lcoe.validation.discountRate'),
    form.electricity_price_eur_per_mwh > 0 ? null : t('lcoe.validation.electricityPrice'),
  ].filter(Boolean) as string[]
  const isValid = validationMessages.length === 0

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
      <div className="space-y-2">
        <p className="section-kicker">{t('lcoe.kicker')}</p>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <h1 className="text-3xl font-semibold text-slate-900">{t('lcoe.title')}</h1>
            <p className="max-w-3xl text-sm leading-6 text-slate-600">{t('lcoe.subtitle')}</p>
          </div>
          <Badge variant="outline" className="w-fit rounded-full border-slate-300 bg-white/80 px-3 py-1 text-slate-600">
            <FlaskConical size={13} className="mr-1.5" />
            {t('lcoe.analysisBadge')}
          </Badge>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="surface-card">
          <CardHeader>
            <CardTitle className="text-lg">{t('lcoe.formTitle')}</CardTitle>
          </CardHeader>
          <CardContent>
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid gap-4 md:grid-cols-[1.4fr_auto] md:items-end">
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
                  {TECHNOLOGIES.map((tech) => (
                    <SelectItem key={tech} value={tech}>
                      {t(TECH_LABEL_KEYS[tech] ?? tech)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button type="button" variant="outline" className="rounded-xl" onClick={loadBenchmark}>
              {t('lcoe.loadBenchmark')}
            </Button>
          </div>

          {/* Currency + FX section */}
          <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50/60 dark:bg-slate-800/40 p-4 space-y-3">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
              {t('lcoe.currencySection')}
            </p>
            <div className="grid gap-3 sm:grid-cols-[1fr_1fr]">
              <div className="space-y-1.5">
                <Label className="text-sm">{t('lcoe.inputCurrency')}</Label>
                <Select
                  value={form.currency}
                  onValueChange={(v: 'EUR' | 'USD' | 'CNY') =>
                    setForm((f) => ({ ...f, currency: v, reference_fx_to_eur: FX_PRESETS[v].fx }))
                  }
                >
                  <SelectTrigger className="rounded-xl">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="EUR">EUR — Euro</SelectItem>
                    <SelectItem value="USD">USD — US Dollar</SelectItem>
                    <SelectItem value="CNY">CNY — 人民币</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-sm">{t('lcoe.fxToEur')}</Label>
                <Input
                  type="number"
                  step="0.001"
                  className="h-10 rounded-xl border-slate-200 bg-white dark:bg-slate-700"
                  value={form.reference_fx_to_eur}
                  onChange={(e) => setForm((f) => ({ ...f, reference_fx_to_eur: parseFloat(e.target.value) || 1 }))}
                />
              </div>
            </div>
            <p className="text-[11px] text-slate-400 dark:text-slate-500">
              {FX_PRESETS[form.currency]?.label} — {t('lcoe.fxNote')}
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
          {FIELD_CONFIG.map(([key, labelKey, step]) => (
            <div key={key} className="space-y-2 rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
              <div className="flex items-center justify-between gap-2">
                <Label className="text-sm font-medium text-slate-700">
                  {labelKey === 'capacity_mw' ? t('lcoe.capacityMw') : t(labelKey)}
                </Label>
                {FIELD_UNIT_KEYS[key] ? <span className="metric-unit">{t(FIELD_UNIT_KEYS[key]!)}</span> : null}
              </div>
              <Input
                type="number"
                step={step}
                className="h-11 rounded-xl border-slate-200 bg-white"
                value={form[key] as number}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    [key]: parseFloat(e.target.value) || 0,
                  }))
                }
              />
              <p className="text-xs leading-5 text-slate-500">{t(`lcoe.fieldHelp.${key}`)}</p>
            </div>
          ))}
          </div>

          {/* Germany market reference price presets */}
          {form.currency === 'EUR' && (
          <div className="rounded-2xl border border-slate-200 bg-slate-50/60 dark:border-slate-700 dark:bg-slate-800/40 px-4 py-3 space-y-2">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
              {t('lcoe.deMarketRef')}
            </p>
            <div className="flex flex-wrap gap-2">
              {DE_MARKET_PRICES.map(({ year, price, note }) => (
                <button
                  key={year}
                  type="button"
                  onClick={() => setForm((f) => ({ ...f, electricity_price_eur_per_mwh: price }))}
                  style={{ minHeight: 'unset', minWidth: 'unset' }}
                  className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-600 ${
                    form.electricity_price_eur_per_mwh === price
                      ? 'bg-amber-100 border-amber-300 text-amber-900 dark:bg-amber-900/40 dark:border-amber-600 dark:text-amber-300'
                      : 'bg-white border-stone-200 text-stone-600 hover:bg-stone-50 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-300'
                  }`}
                >
                  {year} — {price} €/MWh{note ? ` ${note}` : ''}
                </button>
              ))}
            </div>
            <p className="text-[11px] text-slate-400 dark:text-slate-500">
              {t('lcoe.deMarketRefNote')}
            </p>
          </div>
          )}

          {/* China market reference price presets */}
          {form.currency === 'CNY' && (
          <div className="rounded-2xl border border-red-100 dark:border-red-900/40 bg-red-50/60 dark:bg-red-900/10 px-4 py-3 space-y-2">
            <p className="text-xs font-medium text-red-500 dark:text-red-400 uppercase tracking-wide">
              {t('lcoe.cnMarketRef')}
            </p>
            <div className="flex flex-wrap gap-2">
              {CN_MARKET_PRICES.map(({ year, price }: { year: number; price: number }) => (
                <button
                  key={year}
                  type="button"
                  onClick={() => setForm((f) => ({ ...f, electricity_price_eur_per_mwh: price }))}
                  style={{ minHeight: 'unset', minWidth: 'unset' }}
                  className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 ${
                    form.electricity_price_eur_per_mwh === price
                      ? 'bg-red-100 border-red-300 text-red-900 dark:bg-red-800/40 dark:border-red-600 dark:text-red-300'
                      : 'bg-white border-stone-200 text-stone-600 hover:bg-stone-50 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-300'
                  }`}
                >
                  {year} — ¥{price}/MWh
                </button>
              ))}
            </div>
            <p className="text-[11px] text-slate-400 dark:text-slate-500">
              {t('lcoe.cnMarketRefNote')}
            </p>
          </div>
          )}

          {validationMessages.length > 0 ? (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              <div className="flex items-start gap-2">
                <CircleAlert size={16} className="mt-0.5 shrink-0" />
                <div className="space-y-1">
                  <p className="font-medium">{t('lcoe.validationTitle')}</p>
                  {validationMessages.map((message) => (
                    <p key={message}>{message}</p>
                  ))}
                </div>
              </div>
            </div>
          ) : null}

          <Button
            type="submit"
            disabled={lcoeMutation.isPending || !isValid}
            className="h-11 w-full rounded-xl"
          >
            {lcoeMutation.isPending ? t('lcoe.calculating') : t('lcoe.calculate')}
          </Button>
          {(lcoeMutation.error || sensitivityMutation.error) && (
            <p className="text-sm text-red-500">
              {localizeErrorMessage(t, lcoeMutation.error ?? sensitivityMutation.error, 'common.error')}
            </p>
          )}
        </form>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="surface-card">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2 text-lg">
                <LineChartIcon size={18} className="text-indigo-600" />
                {t('lcoe.resultTitle')}
              </CardTitle>
            </CardHeader>
            <CardContent>
          {lcoeMutation.data ? (
            <div className="grid grid-cols-2 gap-3">
              <MetricCard
                label={t('lcoe.lcoe')}
                value={lcoeMutation.data.lcoe_eur_per_mwh.toFixed(1)}
                unit={t('lcoe.unitEurPerMwh')}
                sub={t('lcoe.resultHintLcoe')}
                color="blue"
              />
              {lcoeMutation.data.currency !== 'EUR' && (
                <MetricCard
                  label={t('lcoe.lcoeLocal', { currency: lcoeMutation.data.currency })}
                  value={lcoeMutation.data.lcoe_local_per_mwh.toFixed(1)}
                  unit={`${lcoeMutation.data.currency}/MWh`}
                  sub={t('lcoe.resultHintLcoeLocal')}
                  color="blue"
                />
              )}
              <MetricCard
                label={t('lcoe.npv')}
                value={`€${(lcoeMutation.data.npv_eur / 1e6).toFixed(1)}M`}
                sub={t('lcoe.resultHintNpv')}
                color={lcoeMutation.data.npv_eur > 0 ? 'green' : 'red'}
              />
              <MetricCard
                label={t('lcoe.irr')}
                value={`${(lcoeMutation.data.irr * 100).toFixed(1)}%`}
                sub={t('lcoe.resultHintIrr')}
                color="blue"
              />
              <MetricCard
                label={t('lcoe.payback')}
                value={`${lcoeMutation.data.payback_years.toFixed(1)} ${t('lcoe.years')}`}
                sub={t('lcoe.resultHintPayback')}
              />
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/80 px-4 py-8 text-center">
            <p className="text-slate-400 text-center">
              {t('common.noData')}
            </p>
            </div>
          )}
          {lcoeMutation.data && (
            <p className="mt-3 text-[11px] text-slate-400 dark:text-slate-500 italic">
              {t('lcoe.priceUsedNote', { price: lcoeMutation.data.electricity_price_eur_per_mwh })}
              {lcoeMutation.data.currency !== 'EUR' && (
                <> · {t('lcoe.fxUsedNote', { fx: lcoeMutation.data.reference_fx_to_eur, currency: lcoeMutation.data.currency })}</>
              )}
            </p>
          )}
            </CardContent>
          </Card>
        </div>
      </div>

      {sensitivityMutation.data && sensitivityChartData.length > 0 && (
        <Card className="surface-card">
          <CardHeader>
            <CardTitle className="text-lg">{t('lcoe.sensitivityAnalysis')}</CardTitle>
          </CardHeader>
          <CardContent>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={sensitivityChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="idx" hide />
              <YAxis
                label={{
                  value: t('lcoe.axisEurPerMwh'),
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
          </CardContent>
        </Card>
      )}
    </div>
  )
}

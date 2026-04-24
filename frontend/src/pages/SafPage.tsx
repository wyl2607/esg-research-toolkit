import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { calcSafCost, getSafBenchmarks } from '@/lib/api'
import type { SAFInput, SAFCostResult } from '@/lib/api'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { useTranslation } from 'react-i18next'
import { TrendingDown, TrendingUp, Fuel } from 'lucide-react'
import { PageContainer } from '@/components/layout/PageContainer'
import { PageHeader } from '@/components/layout/PageHeader'
import { Panel } from '@/components/layout/Panel'
import { MetricCard } from '@/components/MetricCard'
import { NoticeBanner } from '@/components/NoticeBanner'

const PATHWAY_KEYS: Record<string, string> = {
  HEFA: 'saf.pathways.HEFA',
  'FT-biomass': 'saf.pathways.FTBiomass',
  ATJ: 'saf.pathways.ATJ',
  PtL: 'saf.pathways.PtL',
  'co-processing': 'saf.pathways.coProcessing',
}

const REGION_KEYS: Record<string, string> = {
  DE: 'saf.regions.DE',
  EU: 'saf.regions.EU',
  US: 'saf.regions.US',
  BR: 'saf.regions.BR',
  INTL: 'saf.regions.INTL',
}

const DEFAULT_INPUT: SAFInput = {
  pathway: 'HEFA',
  region: 'EU',
  production_capacity_tonnes_year: 50_000,
  capex_eur_per_tonne_year: 1_800,
  lifetime_years: 20,
  discount_rate: 0.08,
  feedstock_cost_eur_per_tonne: 600,
  feedstock_to_saf_ratio: 1.25,
  opex_eur_per_tonne: 250,
  policy_credit_eur_per_tonne: 0,
  jet_fuel_price_eur_per_litre: 0.60,
  saf_density_kg_per_litre: 0.8,
}

function fmt(n: number, decimals = 2) {
  return n.toFixed(decimals)
}

function CostBreakdownChart({ result }: { result: SAFCostResult }) {
  const data = [
    { name: 'CAPEX', value: result.capex_component_eur_per_tonne, fill: '#6366f1' },
    { name: 'Feedstock', value: result.feedstock_component_eur_per_tonne, fill: '#f59e0b' },
    { name: 'OPEX', value: result.opex_component_eur_per_tonne, fill: '#22c55e' },
    {
      name: 'Policy Credit',
      value: -result.policy_credit_eur_per_tonne,
      fill: result.policy_credit_eur_per_tonne > 0 ? '#10b981' : '#e5e7eb',
    },
    { name: 'TOTAL', value: result.levelized_cost_eur_per_tonne, fill: '#0ea5e9' },
  ]

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="name" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} unit=" €/t" />
        <Tooltip formatter={(v) => [`€${fmt(Number(v ?? 0))}/t`, '']} />
        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

function CompetitivenessBar({ result }: { result: SAFCostResult }) {
  const jetPrice = result.jet_fuel_reference_eur_per_litre
  const safPrice = result.levelized_cost_eur_per_litre
  const max = Math.max(jetPrice, safPrice) * 1.3

  const data = [
    { name: 'Jet A-1 (kerosene)', value: jetPrice, fill: '#94a3b8' },
    { name: `SAF (${result.pathway})`, value: safPrice, fill: result.is_cost_competitive ? '#22c55e' : '#f59e0b' },
  ]

  return (
    <ResponsiveContainer width="100%" height={120}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 40, bottom: 0, left: 120 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" domain={[0, max]} tick={{ fontSize: 12 }} unit=" €/L" />
        <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} width={120} />
        <Tooltip formatter={(v) => [`€${fmt(Number(v ?? 0))}/L`, '']} />
        <ReferenceLine x={jetPrice} stroke="#ef4444" strokeDasharray="4 2" label={{ value: 'Breakeven', position: 'insideTopRight', fontSize: 11, fill: '#ef4444' }} />
        <Bar dataKey="value" radius={[0, 4, 4, 0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

export function SafPage() {
  const { t } = useTranslation()
  const [form, setForm] = useState<SAFInput>(DEFAULT_INPUT)

  const safMutation = useMutation({ mutationFn: calcSafCost })

  const { data: benchmarks, isLoading: benchmarksLoading } = useQuery({
    queryKey: ['saf-benchmarks'],
    queryFn: getSafBenchmarks,
  })

  const result: SAFCostResult | undefined = safMutation.data

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    safMutation.mutate(form)
  }

  const loadBenchmark = (key: string) => {
    if (benchmarks?.[key]) setForm(benchmarks[key])
  }

  const numField = (
    label: string,
    key: keyof SAFInput,
    opts?: { step?: number; min?: number; max?: number; unit?: string }
  ) => (
    <div className="space-y-1">
      <label className="block text-xs font-medium text-stone-600 dark:text-slate-400">
        {label}
        {opts?.unit && <span className="ml-1 text-stone-400">({opts.unit})</span>}
      </label>
      <input
        type="number"
        step={opts?.step ?? 1}
        min={opts?.min ?? 0}
        max={opts?.max}
        value={form[key] as number}
        onChange={(e) => setForm((f) => ({ ...f, [key]: parseFloat(e.target.value) || 0 }))}
        className="w-full rounded-md border border-stone-200 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
      />
    </div>
  )

  return (
    <PageContainer>
      <div className="space-y-2">
        <p className="section-kicker">{t('saf.kicker')}</p>
        <PageHeader
          title={t('saf.title')}
          subtitle={t('saf.subtitle')}
        />
      </div>

      <NoticeBanner tone="warning">
        {t('saf.notice')}
      </NoticeBanner>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[380px_1fr]">
        {/* Input panel */}
        <div className="space-y-4">
          <Panel title={t('saf.benchmarkPresets')}>
            <div className="grid grid-cols-2 gap-2">
              {benchmarksLoading && (
                <p className="col-span-2 text-sm text-stone-500">{t('common.loading')}</p>
              )}
              {benchmarks && Object.keys(benchmarks).map((key) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => loadBenchmark(key)}
                  className="rounded-md border border-stone-200 dark:border-slate-600 bg-white dark:bg-slate-800 px-2 py-1.5 text-left text-xs font-medium text-stone-700 dark:text-slate-300 hover:bg-amber-50 dark:hover:bg-amber-900/20 hover:border-amber-400 transition-colors"
                >
                  {key.replace(/_/g, ' ')}
                </button>
              ))}
            </div>
          </Panel>

          <Panel title={t('saf.inputParams')}>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1">
                <label className="block text-xs font-medium text-stone-600 dark:text-slate-400">
                  {t('saf.pathway')}
                </label>
                <select
                  value={form.pathway}
                  onChange={(e) => setForm((f) => ({ ...f, pathway: e.target.value as SAFInput['pathway'] }))}
                  className="w-full rounded-md border border-stone-200 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                >
                  {Object.entries(PATHWAY_KEYS).map(([k, translationKey]) => (
                    <option key={k} value={k}>{t(translationKey)}</option>
                  ))}
                </select>
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-medium text-stone-600 dark:text-slate-400">
                  {t('saf.region')}
                </label>
                <select
                  value={form.region}
                  onChange={(e) => setForm((f) => ({ ...f, region: e.target.value as SAFInput['region'] }))}
                  className="w-full rounded-md border border-stone-200 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
                >
                  {Object.entries(REGION_KEYS).map(([k, translationKey]) => (
                    <option key={k} value={k}>{t(translationKey)}</option>
                  ))}
                </select>
              </div>

              {numField(t('saf.capacity'), 'production_capacity_tonnes_year', { unit: 't/yr', step: 1000 })}
              {numField(t('saf.capex'), 'capex_eur_per_tonne_year', { unit: '€/t/yr', step: 100 })}
              {numField(t('saf.lifetime'), 'lifetime_years', { unit: t('saf.unitYears'), step: 1, min: 5, max: 40 })}
              {numField(t('saf.discountRate'), 'discount_rate', { unit: t('saf.unitDiscountRateExample'), step: 0.01, min: 0.01, max: 0.30 })}
              {numField(t('saf.feedstockCost'), 'feedstock_cost_eur_per_tonne', { unit: '€/t feedstock', step: 10 })}
              {numField(t('saf.feedstockRatio'), 'feedstock_to_saf_ratio', { unit: 't/t', step: 0.05, min: 1 })}
              {numField(t('saf.opex'), 'opex_eur_per_tonne', { unit: '€/t SAF', step: 10 })}
              {numField(t('saf.policyCredit'), 'policy_credit_eur_per_tonne', { unit: t('saf.unitEurPerTonneNegative'), step: 10, max: 0 })}
              {numField(t('saf.jetFuelRef'), 'jet_fuel_price_eur_per_litre', { unit: '€/L', step: 0.01 })}

              <button
                type="submit"
                disabled={safMutation.isPending}
                className="w-full rounded-md bg-amber-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-amber-800 disabled:opacity-60 transition-colors"
              >
                {safMutation.isPending ? t('common.loading') : t('saf.calculate')}
              </button>

              {safMutation.isError && (
                <p className="text-xs text-red-600">{String(safMutation.error)}</p>
              )}
            </form>
          </Panel>
        </div>

        {/* Results panel */}
        <div className="space-y-4">
          {!result && (
            <div className="flex h-48 items-center justify-center rounded-xl border border-dashed border-stone-200 dark:border-slate-700 text-sm text-stone-400">
              <div className="text-center space-y-2">
                <Fuel size={32} className="mx-auto text-stone-300" />
                <p>{t('saf.emptyState')}</p>
              </div>
            </div>
          )}

          {result && (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <MetricCard
                  label={t('saf.lcosTonne')}
                  value={`€${fmt(result.levelized_cost_eur_per_tonne, 0)}`}
                  color="blue"
                />
                <MetricCard
                  label={t('saf.lcosLitre')}
                  value={`€${fmt(result.levelized_cost_eur_per_litre, 3)}/L`}
                  color="blue"
                />
                <MetricCard
                  label={t('saf.premium')}
                  value={`+${fmt(result.premium_vs_conventional_pct, 1)}%`}
                  color={result.is_cost_competitive ? 'green' : 'default'}
                />
                <MetricCard
                  label={t('saf.breakeven')}
                  value={`€${fmt(result.breakeven_jet_fuel_price_eur_per_litre, 3)}/L`}
                />
              </div>

              <Panel title={t('saf.competitiveness')}>
                {result.is_cost_competitive ? (
                  <div className="mb-3 flex items-center gap-2 rounded-lg bg-green-50 dark:bg-green-900/20 px-4 py-2 text-sm text-green-700 dark:text-green-300">
                    <TrendingDown size={16} />
                    {t('saf.competitive')}
                  </div>
                ) : (
                  <div className="mb-3 flex items-center gap-2 rounded-lg bg-amber-50 dark:bg-amber-900/20 px-4 py-2 text-sm text-amber-700 dark:text-amber-300">
                    <TrendingUp size={16} />
                    {t('saf.notCompetitive', {
                      premium: fmt(result.premium_vs_conventional_pct, 1),
                      breakeven: fmt(result.breakeven_jet_fuel_price_eur_per_litre, 3),
                    })}
                  </div>
                )}
                <CompetitivenessBar result={result} />
              </Panel>

              <Panel title={t('saf.costBreakdown')}>
                <CostBreakdownChart result={result} />
              </Panel>

              <Panel title={t('saf.projectFinance')}>
                <div className="grid grid-cols-3 gap-4">
                  <MetricCard
                    label={t('saf.npv')}
                    value={`${result.npv_eur >= 0 ? '+' : ''}€${fmt(result.npv_eur / 1_000_000, 1)}M`}
                    color={result.npv_eur >= 0 ? 'green' : 'red'}
                  />
                  <MetricCard
                    label={t('saf.irr')}
                    value={result.irr > 0 ? `${fmt(result.irr * 100, 1)}%` : t('saf.notAvailable')}
                    color="blue"
                  />
                  <MetricCard
                    label={t('saf.payback')}
                    value={result.payback_years != null ? fmt(result.payback_years, 1) : t('saf.greaterThanLifetime')}
                  />
                </div>
                <p className="mt-3 text-xs text-stone-400 dark:text-slate-500">
                  {t('saf.financeNote')}
                </p>
              </Panel>

              <Panel title={t('saf.marketContext')}>
                <ul className="space-y-2 text-sm text-stone-600 dark:text-slate-300">
                  <li>{t('saf.marketContextItems.refuelEu')}</li>
                  <li>{t('saf.marketContextItems.jetFuelPrice')}</li>
                  <li>{t('saf.marketContextItems.hefaMaturity')}</li>
                  <li>{t('saf.marketContextItems.brazilAtj')}</li>
                  <li>{t('saf.marketContextItems.ptlTrajectory')}</li>
                  <li>{t('saf.marketContextItems.germanProduction')}</li>
                </ul>
              </Panel>
            </>
          )}
        </div>
      </div>
    </PageContainer>
  )
}

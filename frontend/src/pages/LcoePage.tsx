import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { calcLcoe, calcSensitivity, getBenchmarks } from '@/lib/api'
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
import { Badge } from '@/components/ui/badge'
import { FlaskConical, LineChart as LineChartIcon } from 'lucide-react'
import { PageContainer } from '@/components/layout/PageContainer'
import { PageHeader } from '@/components/layout/PageHeader'
import { Panel } from '@/components/layout/Panel'
import { NoticeBanner } from '@/components/NoticeBanner'
import { MetricCard } from '@/components/MetricCard'
import { LcoeInputForm } from '@/components/lcoe/LcoeInputForm'
import { createInitialLcoeInput } from '@/components/lcoe/utils'

const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444']

export function LcoePage() {
  const { t, i18n } = useTranslation()
  const [form, setForm] = useState<LCOEInput>(() =>
    createInitialLcoeInput(i18n.language || 'de')
  )

  const lcoeMutation = useMutation({ mutationFn: calcLcoe })
  const sensitivityMutation = useMutation({ mutationFn: calcSensitivity })

  const {
    data: benchmarks,
    isLoading: benchmarksLoading,
    error: benchmarksError,
    refetch: refetchBenchmarks,
  } = useQuery({
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
    <PageContainer>
      <NoticeBanner tone="mode">{t('projectAnalysis.modeBanner')}</NoticeBanner>
      <div className="space-y-2">
        <p className="section-kicker">{t('lcoe.kicker')}</p>
        <PageHeader
          title={t('lcoe.title')}
          subtitle={t('lcoe.subtitle')}
          actions={
            <Badge variant="outline" className="w-fit rounded-full border-slate-300 bg-white/80 px-3 py-1 text-slate-600">
              <FlaskConical size={13} className="mr-1.5" />
              {t('lcoe.analysisBadge')}
            </Badge>
          }
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <LcoeInputForm
          form={form}
          setForm={setForm}
          onSubmit={handleSubmit}
          onLoadBenchmark={loadBenchmark}
          benchmarksLoading={benchmarksLoading}
          benchmarksError={benchmarksError}
          onRefetchBenchmarks={refetchBenchmarks}
          validationMessages={validationMessages}
          isValid={isValid}
          lcoePending={lcoeMutation.isPending}
          lcoeError={lcoeMutation.error}
          sensitivityError={sensitivityMutation.error}
        />

        <div className="space-y-4">
          <Panel
            title={
              <span className="flex items-center gap-2 text-lg">
                <LineChartIcon size={18} className="text-indigo-600" />
                {t('lcoe.resultTitle')}
              </span>
            }
          >
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
                  value={
                    lcoeMutation.data.payback_years == null
                      ? '—'
                      : `${lcoeMutation.data.payback_years.toFixed(1)} ${t('lcoe.years')}`
                  }
                  sub={t('lcoe.resultHintPayback')}
                />
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/80 px-4 py-8 text-center">
                <p className="text-center text-slate-400">{t('common.noData')}</p>
              </div>
            )}
            {lcoeMutation.data && (
              <p className="mt-3 text-[11px] italic text-slate-400 dark:text-slate-500">
                {t('lcoe.priceUsedNote', { price: lcoeMutation.data.electricity_price_eur_per_mwh })}
                {lcoeMutation.data.currency !== 'EUR' && (
                  <>
                    {' '}
                    ·{' '}
                    {t('lcoe.fxUsedNote', {
                      fx: lcoeMutation.data.reference_fx_to_eur,
                      currency: lcoeMutation.data.currency,
                    })}
                  </>
                )}
              </p>
            )}
          </Panel>
        </div>
      </div>

      {sensitivityMutation.data && sensitivityChartData.length > 0 && (
        <Panel title={t('lcoe.sensitivityAnalysis')}>
          <ResponsiveContainer width="100%" height={280} minWidth={0} minHeight={0}>
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
        </Panel>
      )}
    </PageContainer>
  )
}

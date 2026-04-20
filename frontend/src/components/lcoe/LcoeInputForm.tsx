import type { Dispatch, FormEvent, SetStateAction } from 'react'
import { useTranslation } from 'react-i18next'

import { FilterBar } from '@/components/FilterBar'
import { NoticeBanner } from '@/components/NoticeBanner'
import { QueryStateCard } from '@/components/QueryStateCard'
import { FormCard } from '@/components/layout/Panel'
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
import { localizeErrorMessage } from '@/lib/error-utils'
import type { LCOEInput } from '@/lib/types'
import {
  CN_MARKET_PRICES,
  DE_MARKET_PRICES,
  FIELD_CONFIG,
  FIELD_UNIT_KEYS,
  FX_PRESETS,
  TECH_LABEL_KEYS,
  TECHNOLOGIES,
  US_MARKET_PRICES,
} from './utils'

interface LcoeInputFormProps {
  form: LCOEInput
  setForm: Dispatch<SetStateAction<LCOEInput>>
  onSubmit: (e: FormEvent) => void
  onLoadBenchmark: () => void
  benchmarksLoading: boolean
  benchmarksError: unknown
  onRefetchBenchmarks: () => void
  validationMessages: string[]
  isValid: boolean
  lcoePending: boolean
  lcoeError: unknown
  sensitivityError: unknown
}

export function LcoeInputForm(props: LcoeInputFormProps) {
  const {
    form,
    setForm,
    onSubmit,
    onLoadBenchmark,
    benchmarksLoading,
    benchmarksError,
    onRefetchBenchmarks,
    validationMessages,
    isValid,
    lcoePending,
    lcoeError,
    sensitivityError,
  } = props
  const { t } = useTranslation()

  return (
    <FormCard>
      <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{t('lcoe.formTitle')}</h2>
      <form onSubmit={onSubmit} className="mt-5 space-y-5">
        <FilterBar>
          <FilterBar.Field label={t('lcoe.technology')} htmlFor="lcoe-technology">
            <Select
              value={form.technology}
              onValueChange={(v) =>
                setForm((f) => ({
                  ...f,
                  technology: v as LCOEInput['technology'],
                }))
              }
            >
              <SelectTrigger id="lcoe-technology">
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
          </FilterBar.Field>
          <FilterBar.Actions>
            <Button type="button" variant="outline" onClick={onLoadBenchmark}>
              {t('lcoe.loadBenchmark')}
            </Button>
          </FilterBar.Actions>
        </FilterBar>

        {benchmarksLoading ? (
          <QueryStateCard
            tone="loading"
            title={t('common.loading')}
            body={t('lcoe.subtitle')}
          />
        ) : benchmarksError ? (
          <QueryStateCard
            tone="error"
            title={t('common.error')}
            body={localizeErrorMessage(t, benchmarksError, 'common.error')}
            actionLabel={t('errorBoundary.retry')}
            onAction={() => void onRefetchBenchmarks()}
          />
        ) : null}

        <div className="space-y-3 rounded-2xl border border-slate-200 bg-slate-50/60 p-4 dark:border-slate-700 dark:bg-slate-800/40">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
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
                <SelectTrigger>
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
              <Label htmlFor="lcoe-fx" className="text-sm">
                {t('lcoe.fxToEur')}
              </Label>
              <Input
                id="lcoe-fx"
                type="number"
                step="0.001"
                className="h-10 border-slate-200 bg-white dark:bg-slate-700"
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

        {form.currency === 'EUR' && (
          <div className="space-y-2 rounded-2xl border border-slate-200 bg-slate-50/60 px-4 py-3 dark:border-slate-700 dark:bg-slate-800/40">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
              {t('lcoe.deMarketRef')}
            </p>
            <div className="flex flex-wrap gap-2">
              {DE_MARKET_PRICES.map(({ year, price, note }) => (
                <button
                  key={year}
                  type="button"
                  onClick={() => setForm((f) => ({ ...f, electricity_price_eur_per_mwh: price }))}
                  style={{ minHeight: 'unset', minWidth: 'unset' }}
                  className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-600 ${
                    form.electricity_price_eur_per_mwh === price
                      ? 'border-amber-300 bg-amber-100 text-amber-900 dark:border-amber-600 dark:bg-amber-900/40 dark:text-amber-300'
                      : 'border-stone-200 bg-white text-stone-600 hover:bg-stone-50 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-300'
                  }`}
                >
                  {year} — {price} €/MWh{note ? ` ${note}` : ''}
                </button>
              ))}
            </div>
            <p className="text-[11px] text-slate-400 dark:text-slate-500">{t('lcoe.deMarketRefNote')}</p>
          </div>
        )}

        {form.currency === 'USD' && (
          <div className="space-y-2 rounded-2xl border border-sky-100 bg-sky-50/60 px-4 py-3 dark:border-sky-900/40 dark:bg-sky-900/10">
            <p className="text-xs font-medium uppercase tracking-wide text-sky-600 dark:text-sky-400">
              {t('lcoe.usMarketRef')}
            </p>
            <div className="flex flex-wrap gap-2">
              {US_MARKET_PRICES.map(({ year, price, note }) => (
                <button
                  key={year}
                  type="button"
                  onClick={() => setForm((f) => ({ ...f, electricity_price_eur_per_mwh: price }))}
                  style={{ minHeight: 'unset', minWidth: 'unset' }}
                  className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 ${
                    form.electricity_price_eur_per_mwh === price
                      ? 'border-sky-300 bg-sky-100 text-sky-900 dark:border-sky-600 dark:bg-sky-800/40 dark:text-sky-300'
                      : 'border-stone-200 bg-white text-stone-600 hover:bg-stone-50 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-300'
                  }`}
                >
                  {year} — ${price}/MWh{note ? ` ${note}` : ''}
                </button>
              ))}
            </div>
            <p className="text-[11px] text-slate-400 dark:text-slate-500">{t('lcoe.usMarketRefNote')}</p>
          </div>
        )}

        {form.currency === 'CNY' && (
          <div className="space-y-2 rounded-2xl border border-red-100 bg-red-50/60 px-4 py-3 dark:border-red-900/40 dark:bg-red-900/10">
            <p className="text-xs font-medium uppercase tracking-wide text-red-500 dark:text-red-400">
              {t('lcoe.cnMarketRef')}
            </p>
            <div className="flex flex-wrap gap-2">
              {CN_MARKET_PRICES.map(({ year, price }: { year: number; price: number }) => (
                <button
                  key={year}
                  type="button"
                  onClick={() => setForm((f) => ({ ...f, electricity_price_eur_per_mwh: price }))}
                  style={{ minHeight: 'unset', minWidth: 'unset' }}
                  className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 ${
                    form.electricity_price_eur_per_mwh === price
                      ? 'border-red-300 bg-red-100 text-red-900 dark:border-red-600 dark:bg-red-800/40 dark:text-red-300'
                      : 'border-stone-200 bg-white text-stone-600 hover:bg-stone-50 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-300'
                  }`}
                >
                  {year} — ¥{price}/MWh
                </button>
              ))}
            </div>
            <p className="text-[11px] text-slate-400 dark:text-slate-500">{t('lcoe.cnMarketRefNote')}</p>
          </div>
        )}

        {validationMessages.length > 0 ? (
          <NoticeBanner tone="warning" title={t('lcoe.validationTitle')}>
            <div className="space-y-1">
              {validationMessages.map((message) => (
                <p key={message}>{message}</p>
              ))}
            </div>
          </NoticeBanner>
        ) : null}

        <Button type="submit" disabled={lcoePending || !isValid} className="h-11 w-full rounded-xl">
          {lcoePending ? t('lcoe.calculating') : t('lcoe.calculate')}
        </Button>
        {lcoeError || sensitivityError ? (
          <p className="text-sm text-red-500">
            {localizeErrorMessage(t, lcoeError ?? sensitivityError, 'common.error')}
          </p>
        ) : null}
      </form>
    </FormCard>
  )
}

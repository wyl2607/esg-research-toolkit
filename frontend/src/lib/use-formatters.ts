import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'

import {
  axisScale,
  formatCompact,
  formatCurrency,
  formatDate,
  formatDateTime,
  formatDelta,
  formatMeasure,
  formatNumber,
  formatPercent,
  formatYear,
  resolveLocale,
  type FormatMeasureOptions,
  type FormatNumberOptions,
} from './format'
import type { UnitKey } from './units'

/**
 * Formatters bound to the *active UI language*.
 *
 * Components must format through this hook rather than calling `Intl` or
 * `toLocaleString()` directly, so that switching the language switches every
 * number on the page at once. The bug this prevents: chart axes used
 * `navigator.language` while KPI tiles used a hardcoded `en-US`, so a German
 * page showed `1,1 Mio.` on an axis and `29.5%` in the tile above it.
 */
export function useFormatters() {
  const { i18n } = useTranslation()
  const locale = resolveLocale(i18n.resolvedLanguage)

  return useMemo(
    () => ({
      locale,
      number: (value: number | null | undefined, opts: FormatNumberOptions = {}) =>
        formatNumber(value, { ...opts, locale }),
      percent: (value: number | null | undefined, fractionDigits?: number) =>
        formatPercent(value, locale, fractionDigits),
      compact: (value: number | null | undefined, fractionDigits?: number) =>
        formatCompact(value, locale, fractionDigits),
      axisScale: (maxValue: number) => axisScale(maxValue, locale),
      measure: (
        value: number | null | undefined,
        unit: UnitKey,
        opts: FormatMeasureOptions = {}
      ) => formatMeasure(value, locale, unit, opts),
      delta: (value: number | null | undefined, fractionDigits?: number) =>
        formatDelta(value, locale, fractionDigits),
      currency: (value: number | null | undefined, fractionDigits?: number) =>
        formatCurrency(value, locale, fractionDigits),
      year: formatYear,
      date: (value: string | number | Date | null | undefined) => formatDate(value, locale),
      dateTime: (value: string | number | Date | null | undefined) =>
        formatDateTime(value, locale),
    }),
    [locale]
  )
}

export type Formatters = ReturnType<typeof useFormatters>

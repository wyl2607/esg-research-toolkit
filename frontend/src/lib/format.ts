/**
 * Internationalized formatting utilities.
 *
 * Every number the UI renders goes through this module so that one screen can
 * never mix two locales. Before it existed the app formatted numbers three
 * incompatible ways at once: `Intl` defaulted to `en-US`, chart axes used
 * `navigator.language`, and several call sites used bare template literals or
 * `toLocaleString()` with no locale — which is why a German page could show
 * `970.000` next to `63.4%` next to `1.11M`.
 *
 * Rules enforced here:
 *  - the caller always passes the *active UI language*, never a browser default
 *  - unknown is `—`, never 0
 *  - a value and its unit are joined by a no-break space so a measurement can
 *    never wrap mid-number
 *  - magnitude abbreviation has one implementation, used at every threshold
 */
import { UNITS, UNIT_SEPARATOR, UNKNOWN, type UnitKey } from './units'

export { UNKNOWN }

/** UI language codes the app ships. */
export type AppLanguage = 'de' | 'en' | 'zh'

const LOCALES: Record<AppLanguage, string> = {
  de: 'de-DE',
  en: 'en-US',
  zh: 'zh-CN',
}

const CURRENCIES: Record<AppLanguage, string> = {
  de: 'EUR',
  en: 'USD',
  zh: 'CNY',
}

/**
 * Map an i18n language tag onto the BCP-47 locale used for formatting.
 * Accepts anything i18next may report (`de`, `de-AT`, `en-GB`, undefined) and
 * always resolves to a supported locale rather than silently falling back to
 * the browser's.
 */
export function resolveLocale(language: string | undefined | null): string {
  const base = (language ?? 'en').split('-')[0].toLowerCase()
  return LOCALES[base as AppLanguage] ?? LOCALES.en
}

function currencyFor(language: string | undefined | null): string {
  const base = (language ?? 'en').split('-')[0].toLowerCase()
  return CURRENCIES[base as AppLanguage] ?? CURRENCIES.en
}

function isMissing(value: number | null | undefined): value is null | undefined {
  return value === null || value === undefined || !Number.isFinite(value)
}

export interface FormatNumberOptions {
  locale?: string
  /** Maximum fraction digits. Default 0 — counts and magnitudes read cleaner. */
  fractionDigits?: number
  /** Force exactly `fractionDigits` decimals (e.g. money columns). */
  fixed?: boolean
}

/**
 * Plain grouped number: `1.234.567` (de) / `1,234,567` (en).
 * Returns `—` for null, undefined and NaN.
 */
export function formatNumber(
  value: number | null | undefined,
  opts: FormatNumberOptions = {}
): string {
  if (isMissing(value)) return UNKNOWN
  const { locale = LOCALES.en, fractionDigits = 0, fixed = false } = opts
  return new Intl.NumberFormat(locale, {
    maximumFractionDigits: fractionDigits,
    minimumFractionDigits: fixed ? fractionDigits : 0,
  }).format(value)
}

/**
 * Percentage from a 0–100 input (not 0–1).
 * Uses Intl's percent style so the locale decides the separator before `%`:
 * `29,5 %` in German, `29.5%` in English.
 */
export function formatPercent(
  value: number | null | undefined,
  locale: string = LOCALES.en,
  fractionDigits: number = 1
): string {
  if (isMissing(value)) return UNKNOWN
  return new Intl.NumberFormat(locale, {
    style: 'percent',
    maximumFractionDigits: fractionDigits,
    minimumFractionDigits: fractionDigits,
  }).format(value / 100)
}

/**
 * Abbreviated magnitude for axes and dense tables: `1,2 Mio.` (de) /
 * `1.2M` (en) / `120万` (zh).
 *
 * One implementation for every magnitude. The previous per-file helpers
 * abbreviated only above 1e6 and used a *different* locale for the abbreviated
 * branch, so a single column could show `970.000` above `1.11M`.
 */
export function formatCompact(
  value: number | null | undefined,
  locale: string = LOCALES.en,
  fractionDigits: number = 1
): string {
  if (isMissing(value)) return UNKNOWN
  return new Intl.NumberFormat(locale, {
    notation: 'compact',
    compactDisplay: 'short',
    maximumFractionDigits: fractionDigits,
  }).format(value)
}

export interface AxisScale {
  /** Divide every tick by this before formatting. */
  divisor: number
  /**
   * Magnitude word to append to the axis unit (`Mio.` in de, `M` in en).
   * Empty when the axis is unscaled.
   */
  suffix: string
}

/**
 * Pick ONE scale for a whole axis.
 *
 * `Intl` compact notation is per-value, and German has no abbreviation for
 * thousands — so a compact German axis renders `350.000` next to `1,2 Mio.`,
 * mixing a grouped number and an abbreviated one in the same column. Scaling
 * the entire axis by a single divisor and naming the magnitude once, in the
 * axis label, keeps every tick in the same form.
 *
 * Falls back to an unscaled axis when the locale has no magnitude word, so no
 * locale ever ends up with a bare `1,2` and no unit.
 */
export function axisScale(maxValue: number, locale: string): AxisScale {
  if (!Number.isFinite(maxValue) || Math.abs(maxValue) < 1_000_000) {
    return { divisor: 1, suffix: '' }
  }
  const divisor = Math.abs(maxValue) >= 1_000_000_000 ? 1_000_000_000 : 1_000_000
  const suffix =
    new Intl.NumberFormat(locale, { notation: 'compact', compactDisplay: 'short' })
      .formatToParts(divisor)
      .find((part) => part.type === 'compact')?.value ?? ''
  return suffix ? { divisor, suffix } : { divisor: 1, suffix: '' }
}

export interface FormatMeasureOptions extends FormatNumberOptions {
  /** Abbreviate large magnitudes (axes, dense tables). Default false. */
  compact?: boolean
}

/**
 * A number joined to its unit symbol by a no-break space: `970.000 tCO₂e`.
 * Percent is delegated to {@link formatPercent} so it keeps the locale's own
 * percent spacing instead of a hand-built one.
 */
export function formatMeasure(
  value: number | null | undefined,
  locale: string,
  unit: UnitKey,
  opts: FormatMeasureOptions = {}
): string {
  if (isMissing(value)) return UNKNOWN
  if (unit === 'percent') return formatPercent(value, locale, opts.fractionDigits ?? 1)
  const num = opts.compact
    ? formatCompact(value, locale, opts.fractionDigits ?? 1)
    : formatNumber(value, { ...opts, locale })
  return `${num}${UNIT_SEPARATOR}${UNITS[unit]}`
}

/**
 * Signed delta for year-over-year copy: `+8,6` / `−140.000`.
 * Uses the locale's own sign display so the minus is a real minus sign, and
 * never emits a bare `+0`.
 */
export function formatDelta(
  value: number | null | undefined,
  locale: string = LOCALES.en,
  fractionDigits: number = 1
): string {
  if (isMissing(value)) return UNKNOWN
  return new Intl.NumberFormat(locale, {
    signDisplay: 'exceptZero',
    maximumFractionDigits: fractionDigits,
    minimumFractionDigits: 0,
  }).format(value)
}

/** Currency in the locale's own currency: `1.000 €` (de) / `$1,000` (en). */
export function formatCurrency(
  value: number | null | undefined,
  locale: string = LOCALES.en,
  fractionDigits: number = 0
): string {
  if (isMissing(value)) return UNKNOWN
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: currencyFor(locale),
    maximumFractionDigits: fractionDigits,
  }).format(value)
}

/** tCO₂e with the canonical unit symbol. */
export function formatEmissions(
  value: number | null | undefined,
  locale: string = LOCALES.en
): string {
  return formatMeasure(value, locale, 'tco2e')
}

/**
 * A calendar year. Years are identifiers, not quantities: they must never be
 * grouped (`2.024`) or localized into another calendar.
 */
export function formatYear(year: number | null | undefined): string {
  if (isMissing(year)) return UNKNOWN
  return String(Math.trunc(year))
}

/** Date-time in the active locale, for "fetched at" style timestamps. */
export function formatDateTime(
  value: string | number | Date | null | undefined,
  locale: string = LOCALES.en
): string {
  if (value === null || value === undefined) return UNKNOWN
  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) return UNKNOWN
  return new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

/** Date only, for report periods and capture dates. */
export function formatDate(
  value: string | number | Date | null | undefined,
  locale: string = LOCALES.en
): string {
  if (value === null || value === undefined) return UNKNOWN
  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) return UNKNOWN
  return new Intl.DateTimeFormat(locale, { dateStyle: 'medium' }).format(date)
}

/**
 * Get directional indicator for trend values.
 * `↑` always means "improved", regardless of whether the underlying metric is
 * better high (renewables) or better low (emissions).
 */
export function getTrendIndicator(
  current: number | null,
  previous: number | null,
  lowerIsBetter: boolean = true,
  threshold: number = 1
): '↑' | '↓' | '' {
  if (current === null || previous === null || previous === 0) return ''
  const change = ((current - previous) / previous) * 100
  if (Math.abs(change) < threshold) return ''

  if (lowerIsBetter) {
    return change < 0 ? '↑' : '↓'
  }
  return change > 0 ? '↑' : '↓'
}

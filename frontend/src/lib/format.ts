/**
 * Internationalized formatting utilities
 */

export interface FormatNumberOptions {
  type?: 'decimal' | 'percent' | 'currency'
  locale?: string
  fractionDigits?: number
}

/**
 * Format numbers with locale-aware formatting
 * @param value - Number to format (null/undefined returns '—')
 * @param opts - Formatting options
 * @returns Formatted string
 */
export function formatNumber(
  value: number | null | undefined,
  opts: FormatNumberOptions = {}
): string {
  if (value === null || value === undefined) return '—'

  const { type = 'decimal', locale = 'en-US', fractionDigits = type === 'percent' ? 1 : 0 } = opts

  if (type === 'percent') {
    return new Intl.NumberFormat(locale, {
      style: 'percent',
      maximumFractionDigits: fractionDigits,
      minimumFractionDigits: fractionDigits,
    }).format(value / 100)
  }

  if (type === 'currency') {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: locale.includes('de') ? 'EUR' : locale.includes('zh') ? 'CNY' : 'USD',
      maximumFractionDigits: fractionDigits,
    }).format(value)
  }

  return new Intl.NumberFormat(locale, {
    maximumFractionDigits: fractionDigits,
    minimumFractionDigits: 0,
  }).format(value)
}

/**
 * Format year as localized date string
 * @param year - Year number
 * @param locale - Locale string (e.g., 'de-DE')
 * @returns Formatted year string
 */
export function formatYear(year: number, locale: string = 'en-US'): string {
  try {
    return new Intl.DateTimeFormat(locale, {
      year: 'numeric',
    }).format(new Date(year, 0, 1))
  } catch {
    return year.toString()
  }
}

/**
 * Format tCO2e emissions with proper unit
 * @param value - Emissions in tonnes
 * @param locale - Locale string
 * @returns Formatted string with unit
 */
export function formatEmissions(value: number | null, locale: string = 'en-US'): string {
  if (value === null || value === undefined) return '—'
  return `${formatNumber(value, { locale })} tCO₂e`
}

/**
 * Format currency with localized symbol
 * @param value - Amount in EUR
 * @param locale - Locale string
 * @returns Formatted currency string
 */
export function formatCurrency(value: number | null, locale: string = 'en-US'): string {
  if (value === null || value === undefined) return '—'
  return formatNumber(value, { type: 'currency', locale })
}

/**
 * Format percentage value
 * @param value - Value as 0-100 (not 0-1)
 * @param locale - Locale string
 * @param fractionDigits - Number of decimal places
 * @returns Formatted percentage string
 */
export function formatPercent(
  value: number | null,
  locale: string = 'en-US',
  fractionDigits: number = 1
): string {
  if (value === null || value === undefined) return '—'
  return formatNumber(value, { type: 'percent', locale, fractionDigits })
}

/**
 * Get directional indicator for trend values
 * @param current - Current value
 * @param previous - Previous value
 * @param threshold - Minimum change to show indicator (default 1%)
 * @returns Arrow symbol or empty string
 */
export function getTrendIndicator(
  current: number | null,
  previous: number | null,
  threshold: number = 1
): '↑' | '↓' | '' {
  if (current === null || previous === null || previous === 0) return ''
  const change = ((current - previous) / previous) * 100
  if (Math.abs(change) < threshold) return ''
  return change > 0 ? '↑' : '↓'
}

import { describe, expect, it } from 'vitest'
import {
  axisScale,
  formatCompact,
  formatCurrency,
  formatDate,
  formatDateTime,
  formatDelta,
  formatEmissions,
  formatMeasure,
  formatNumber,
  formatPercent,
  formatYear,
  getTrendIndicator,
  resolveLocale,
} from './format'
import { UNITS, UNIT_SEPARATOR } from './units'

const DE = resolveLocale('de')
const EN = resolveLocale('en')
const ZH = resolveLocale('zh')

describe('resolveLocale', () => {
  it('maps app language codes onto BCP-47 locales', () => {
    expect(resolveLocale('de')).toBe('de-DE')
    expect(resolveLocale('en')).toBe('en-US')
    expect(resolveLocale('zh')).toBe('zh-CN')
  })

  it('accepts regional tags and unknown input without leaking a browser default', () => {
    expect(resolveLocale('de-AT')).toBe('de-DE')
    expect(resolveLocale('en-GB')).toBe('en-US')
    expect(resolveLocale(undefined)).toBe('en-US')
    expect(resolveLocale('klingon')).toBe('en-US')
  })
})

describe('formatNumber', () => {
  it('returns em dash for null, undefined and NaN', () => {
    expect(formatNumber(null)).toBe('—')
    expect(formatNumber(undefined)).toBe('—')
    expect(formatNumber(Number.NaN)).toBe('—')
  })

  it('keeps a real zero visible', () => {
    expect(formatNumber(0, { locale: DE })).toBe('0')
  })

  it('groups with the requested locale', () => {
    expect(formatNumber(1234567, { locale: EN })).toBe('1,234,567')
    expect(formatNumber(1234567, { locale: DE })).toBe('1.234.567')
  })
})

describe('formatPercent', () => {
  it('treats input as 0-100, not 0-1', () => {
    expect(formatPercent(42.5, EN)).toBe('42.5%')
  })

  it('uses the locale separator before the percent sign', () => {
    // German writes a space before % (DIN 5008) and a comma decimal mark.
    expect(formatPercent(29.5, DE)).toBe('29,5 %')
    expect(formatPercent(29.5, EN)).toBe('29.5%')
  })

  it('is stable in precision so a row of percentages lines up', () => {
    expect(formatPercent(50, EN)).toBe('50.0%')
    expect(formatPercent(29.5, EN)).toBe('29.5%')
  })

  it('returns em dash for missing values', () => {
    expect(formatPercent(null, DE)).toBe('—')
  })
})

describe('formatCompact', () => {
  it('abbreviates in the requested locale', () => {
    expect(formatCompact(1_240_000, EN)).toBe('1.2M')
    expect(formatCompact(1_240_000, DE)).toContain('Mio')
  })

  it('never mixes locales across the abbreviation threshold', () => {
    // Regression: the old per-file helpers formatted values below 1e6 with the
    // browser locale and values above it with a hardcoded English `M` suffix,
    // so one German column read `970.000` (grouped, dot = thousands) directly
    // above `1.11M` (English magnitude, dot = decimal). Both sides must now
    // come from the same locale.
    expect(formatCompact(970_000, DE)).toBe('970.000')
    expect(formatCompact(1_240_000, DE)).toBe('1,2\u00A0Mio.')
    expect(formatCompact(970_000, EN)).toBe('970K')
    expect(formatCompact(1_240_000, EN)).toBe('1.2M')
  })
})

describe('axisScale', () => {
  it('leaves an axis unscaled below one million', () => {
    expect(axisScale(970_000, DE)).toEqual({ divisor: 1, suffix: '' })
    expect(axisScale(0, DE)).toEqual({ divisor: 1, suffix: '' })
  })

  it('scales the whole axis once and names the magnitude in the locale', () => {
    // Regression: a German compact axis put `350.000` and `1,2 Mio.` in the
    // same column because Intl abbreviates per value and German has no
    // thousands abbreviation.
    expect(axisScale(1_240_000, DE)).toEqual({ divisor: 1_000_000, suffix: 'Mio.' })
    expect(axisScale(1_240_000, EN)).toEqual({ divisor: 1_000_000, suffix: 'M' })
  })

  it('steps up to billions', () => {
    expect(axisScale(4_000_000_000, EN).divisor).toBe(1_000_000_000)
  })

  it('ignores non-finite maxima instead of producing NaN ticks', () => {
    expect(axisScale(Number.NaN, EN)).toEqual({ divisor: 1, suffix: '' })
  })
})

describe('formatMeasure', () => {
  it('joins value and unit with a no-break space', () => {
    expect(formatMeasure(970_000, DE, 'tco2e')).toBe(`970.000${UNIT_SEPARATOR}${UNITS.tco2e}`)
  })

  it('uses the canonical unit spelling, not an ad-hoc one', () => {
    expect(formatMeasure(1, EN, 'tco2e')).toContain('tCO₂e')
    expect(formatMeasure(1, EN, 'tco2e')).not.toContain('tCO2e')
  })

  it('delegates percent so the unit is never appended twice', () => {
    expect(formatMeasure(29.5, DE, 'percent')).toBe('29,5 %')
    expect(formatMeasure(29.5, DE, 'percent')).not.toMatch(/%.*%/)
  })

  it('can abbreviate for axes without changing the unit', () => {
    expect(formatMeasure(1_240_000, EN, 'tco2e', { compact: true })).toBe(
      `1.2M${UNIT_SEPARATOR}${UNITS.tco2e}`
    )
  })

  it('returns em dash for missing values', () => {
    expect(formatMeasure(null, DE, 'mwh')).toBe('—')
  })
})

describe('formatDelta', () => {
  it('signs non-zero values and localizes the decimal mark', () => {
    expect(formatDelta(8.6, EN)).toBe('+8.6')
    expect(formatDelta(8.6, DE)).toBe('+8,6')
  })

  it('does not sign a zero delta', () => {
    expect(formatDelta(0, EN)).toBe('0')
  })

  it('returns em dash for missing values', () => {
    expect(formatDelta(null, EN)).toBe('—')
  })
})

describe('formatCurrency', () => {
  it('picks the currency from the locale', () => {
    expect(formatCurrency(1000, EN)).toContain('$')
    expect(formatCurrency(1000, DE)).toContain('€')
    expect(formatCurrency(1000, ZH)).toContain('¥')
  })

  it('returns em dash for missing values', () => {
    expect(formatCurrency(null, EN)).toBe('—')
  })
})

describe('formatEmissions', () => {
  it('appends the canonical emissions unit', () => {
    expect(formatEmissions(1500, EN)).toBe(`1,500${UNIT_SEPARATOR}${UNITS.tco2e}`)
  })

  it('returns em dash for missing values', () => {
    expect(formatEmissions(null, EN)).toBe('—')
  })
})

describe('formatYear', () => {
  it('never groups a year', () => {
    // Regression: a year run through the number formatter reads as `2.024`.
    expect(formatYear(2024)).toBe('2024')
  })

  it('returns em dash for missing values', () => {
    expect(formatYear(null)).toBe('—')
  })
})

describe('formatDate / formatDateTime', () => {
  it('returns em dash for missing and unparseable values', () => {
    expect(formatDate(null, DE)).toBe('—')
    expect(formatDateTime(undefined, DE)).toBe('—')
    expect(formatDate('not-a-date', DE)).toBe('—')
  })

  it('formats a real timestamp in the requested locale', () => {
    const iso = '2026-08-30T10:56:19Z'
    expect(formatDate(iso, DE)).not.toBe('—')
    expect(formatDateTime(iso, EN)).not.toBe('—')
  })
})

describe('getTrendIndicator', () => {
  it('returns empty when data is missing or previous is zero', () => {
    expect(getTrendIndicator(null, 100)).toBe('')
    expect(getTrendIndicator(100, null)).toBe('')
    expect(getTrendIndicator(100, 0)).toBe('')
  })

  it('treats a fall as improvement when lower is better', () => {
    expect(getTrendIndicator(50, 100, true)).toBe('↑')
    expect(getTrendIndicator(150, 100, true)).toBe('↓')
  })

  it('treats a rise as improvement when higher is better', () => {
    expect(getTrendIndicator(150, 100, false)).toBe('↑')
    expect(getTrendIndicator(50, 100, false)).toBe('↓')
  })

  it('ignores changes below the threshold', () => {
    expect(getTrendIndicator(100.5, 100, true)).toBe('')
  })
})

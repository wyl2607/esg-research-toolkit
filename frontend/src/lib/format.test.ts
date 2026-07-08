import { describe, expect, it } from 'vitest'
import {
  formatCurrency,
  formatEmissions,
  formatNumber,
  formatPercent,
  formatYear,
  getTrendIndicator,
} from './format'

describe('formatNumber', () => {
  it('returns em dash for null and undefined', () => {
    expect(formatNumber(null)).toBe('—')
    expect(formatNumber(undefined)).toBe('—')
  })

  it('formats decimals with locale grouping', () => {
    expect(formatNumber(1234567)).toBe('1,234,567')
    expect(formatNumber(1234567, { locale: 'de-DE' })).toBe('1.234.567')
  })

  it('treats percent input as 0-100, not 0-1', () => {
    expect(formatNumber(42.5, { type: 'percent' })).toBe('42.5%')
    expect(formatNumber(0, { type: 'percent' })).toBe('0.0%')
  })

  it('picks currency by locale language', () => {
    expect(formatNumber(1000, { type: 'currency' })).toContain('$')
    expect(formatNumber(1000, { type: 'currency', locale: 'de-DE' })).toContain('€')
    expect(formatNumber(1000, { type: 'currency', locale: 'zh-CN' })).toContain('¥')
  })
})

describe('formatEmissions / formatCurrency / formatPercent', () => {
  it('returns em dash for null', () => {
    expect(formatEmissions(null)).toBe('—')
    expect(formatCurrency(null)).toBe('—')
    expect(formatPercent(null)).toBe('—')
  })

  it('appends the emissions unit', () => {
    expect(formatEmissions(1500)).toBe('1,500 tCO₂e')
  })

  it('formats percentages with the requested precision', () => {
    expect(formatPercent(33.333, 'en-US', 2)).toBe('33.33%')
  })
})

describe('formatYear', () => {
  it('formats a year and falls back to plain digits on bad locale', () => {
    expect(formatYear(2024)).toBe('2024')
    expect(formatYear(2024, 'not-a-locale')).toBe('2024')
  })
})

describe('getTrendIndicator', () => {
  it('returns empty when data is missing or previous is zero', () => {
    expect(getTrendIndicator(null, 100)).toBe('')
    expect(getTrendIndicator(100, null)).toBe('')
    expect(getTrendIndicator(100, 0)).toBe('')
  })

  it('returns empty below the change threshold', () => {
    expect(getTrendIndicator(100.5, 100)).toBe('')
  })

  it('marks falling emissions as improvement when lower is better', () => {
    expect(getTrendIndicator(80, 100, true)).toBe('↑')
    expect(getTrendIndicator(120, 100, true)).toBe('↓')
  })

  it('marks rising values as improvement when higher is better', () => {
    expect(getTrendIndicator(120, 100, false)).toBe('↑')
    expect(getTrendIndicator(80, 100, false)).toBe('↓')
  })
})

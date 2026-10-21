import { describe, expect, it } from 'vitest'
import { METRIC_UNAVAILABLE, resolveDashboardMetric } from './dashboard-metrics'
import { formatPercent, resolveLocale } from './format'

const DE = resolveLocale('de')
const EN = resolveLocale('en')

const asPercent = (locale: string) => (n: number) => formatPercent(n, locale)

describe('resolveDashboardMetric', () => {
  it('marks request failure as unavailable, never 0', () => {
    expect(resolveDashboardMetric({ kind: 'error' })).toEqual({
      value: METRIC_UNAVAILABLE,
      unavailable: true,
    })
    expect(resolveDashboardMetric({ kind: 'error' }, asPercent(EN))).toEqual({
      value: METRIC_UNAVAILABLE,
      unavailable: true,
    })
  })

  it('renders honest zero when API returns 0', () => {
    expect(resolveDashboardMetric({ kind: 'ready', value: 0 })).toEqual({
      value: 0,
      unavailable: false,
    })
    expect(resolveDashboardMetric({ kind: 'ready', value: 0 }, asPercent(EN))).toEqual({
      value: '0.0%',
      unavailable: false,
    })
  })

  it('renders null averages as unavailable em dash', () => {
    expect(resolveDashboardMetric({ kind: 'ready', value: null }, asPercent(EN))).toEqual({
      value: METRIC_UNAVAILABLE,
      unavailable: true,
    })
    expect(
      resolveDashboardMetric({ kind: 'ready', value: undefined }, asPercent(EN))
    ).toEqual({
      value: METRIC_UNAVAILABLE,
      unavailable: true,
    })
  })

  it('formats real averages without collapsing nulls', () => {
    expect(resolveDashboardMetric({ kind: 'ready', value: 20.5 }, asPercent(EN))).toEqual({
      value: '20.5%',
      unavailable: false,
    })
  })

  it('follows the caller locale so KPI tiles match the rest of the page', () => {
    // Regression: the tile formatter was a bare `${n}%` template, so a German
    // dashboard rendered `29.5%` beside German-formatted chart axes.
    expect(resolveDashboardMetric({ kind: 'ready', value: 29.5 }, asPercent(DE)).value).toBe(
      '29,5\u00A0%'
    )
  })
})

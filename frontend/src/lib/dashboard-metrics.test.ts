import { describe, expect, it } from 'vitest'
import {
  METRIC_UNAVAILABLE,
  formatCountMetric,
  formatPercentMetric,
  resolveDashboardMetric,
} from './dashboard-metrics'

describe('resolveDashboardMetric', () => {
  it('marks request failure as unavailable, never 0', () => {
    expect(resolveDashboardMetric({ kind: 'error' }, formatCountMetric)).toEqual({
      value: METRIC_UNAVAILABLE,
      unavailable: true,
    })
    expect(resolveDashboardMetric({ kind: 'error' }, formatPercentMetric)).toEqual({
      value: METRIC_UNAVAILABLE,
      unavailable: true,
    })
  })

  it('renders honest zero when API returns 0', () => {
    expect(resolveDashboardMetric({ kind: 'ready', value: 0 }, formatCountMetric)).toEqual({
      value: 0,
      unavailable: false,
    })
    expect(resolveDashboardMetric({ kind: 'ready', value: 0 }, formatPercentMetric)).toEqual({
      value: '0%',
      unavailable: false,
    })
  })

  it('renders null averages as unavailable em dash', () => {
    expect(resolveDashboardMetric({ kind: 'ready', value: null }, formatPercentMetric)).toEqual({
      value: METRIC_UNAVAILABLE,
      unavailable: true,
    })
    expect(
      resolveDashboardMetric({ kind: 'ready', value: undefined }, formatPercentMetric)
    ).toEqual({
      value: METRIC_UNAVAILABLE,
      unavailable: true,
    })
  })

  it('formats real averages without collapsing nulls', () => {
    expect(resolveDashboardMetric({ kind: 'ready', value: 20.5 }, formatPercentMetric)).toEqual({
      value: '20.5%',
      unavailable: false,
    })
  })
})

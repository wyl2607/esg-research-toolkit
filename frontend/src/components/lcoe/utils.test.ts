import { describe, expect, it } from 'vitest'
import { createInitialLcoeInput } from './utils'

describe('createInitialLcoeInput', () => {
  it('uses the shared technical defaults and the US price for English', () => {
    const input = createInitialLcoeInput('en')
    expect(input).toMatchObject({
      technology: 'solar_pv',
      capacity_mw: 100,
      capacity_factor: 0.22,
      capex_eur_per_kw: 800,
      opex_eur_per_kw_year: 16,
      lifetime_years: 25,
      discount_rate: 0.05,
      electricity_price_eur_per_mwh: 38,
      currency: 'USD',
      reference_fx_to_eur: 0.92,
    })
  })

  it('uses the latest Chinese market price and FX for Chinese', () => {
    const input = createInitialLcoeInput('zh')
    expect(input.currency).toBe('CNY')
    expect(input.electricity_price_eur_per_mwh).toBe(370)
    expect(input.reference_fx_to_eur).toBe(0.127)
  })

  it('defaults German and unknown languages to the euro market', () => {
    for (const language of ['de', 'de-AT', 'fr', '']) {
      const input = createInitialLcoeInput(language)
      expect(input.currency).toBe('EUR')
      expect(input.electricity_price_eur_per_mwh).toBe(65)
      expect(input.reference_fx_to_eur).toBe(1)
    }
  })

  it('matches language prefixes case-insensitively', () => {
    expect(createInitialLcoeInput('EN-gb').currency).toBe('USD')
    expect(createInitialLcoeInput('ZH-Hans').currency).toBe('CNY')
  })

  it('returns a fresh object on every call', () => {
    const first = createInitialLcoeInput('de')
    first.capacity_mw = 1
    expect(createInitialLcoeInput('de').capacity_mw).toBe(100)
  })
})

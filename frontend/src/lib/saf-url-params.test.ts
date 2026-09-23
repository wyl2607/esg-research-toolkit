import { describe, expect, it } from 'vitest'

import type { SAFInput } from '@/lib/api'
import { formFromUrlParams } from '@/lib/saf-url-params'

const current = { pathway: 'HEFA', jet_fuel_price_eur_per_litre: 0.65 } as SAFInput
const benchmarks: Record<string, SAFInput> = {
  HEFA_EU: { pathway: 'HEFA', feedstock_cost_eur_per_tonne: 1285, jet_fuel_price_eur_per_litre: 0.65, source: 'Fastmarkets' } as SAFInput,
}

describe('formFromUrlParams', () => {
  it('loads a known preset and overrides the jet price', () => {
    const { form, presetKey } = formFromUrlParams(
      new URLSearchParams('preset=HEFA_EU&jet_fuel_price_eur_per_litre=0.95'),
      benchmarks,
      current,
    )
    expect(presetKey).toBe('HEFA_EU')
    expect(form.feedstock_cost_eur_per_tonne).toBe(1285)
    expect(form.jet_fuel_price_eur_per_litre).toBe(0.95)
    expect(benchmarks.HEFA_EU.jet_fuel_price_eur_per_litre).toBe(0.65)
  })

  it('ignores unknown presets and invalid prices', () => {
    for (const query of ['preset=NOPE', 'jet_fuel_price_eur_per_litre=abc', 'jet_fuel_price_eur_per_litre=-1', 'jet_fuel_price_eur_per_litre=', '']) {
      const { form, presetKey } = formFromUrlParams(new URLSearchParams(query), benchmarks, current)
      expect(presetKey).toBeNull()
      expect(form).toBe(current)
    }
  })

  it('applies a jet price without a preset', () => {
    const { form, presetKey } = formFromUrlParams(new URLSearchParams('jet_fuel_price_eur_per_litre=1.1'), benchmarks, current)
    expect(presetKey).toBeNull()
    expect(form).toEqual({ ...current, jet_fuel_price_eur_per_litre: 1.1 })
  })
})

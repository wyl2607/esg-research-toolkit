import type { SAFInput } from '@/lib/api'

/**
 * Initial SAF form from URL parameters, e.g. a link from JetScope:
 * /saf?preset=HEFA_EU&jet_fuel_price_eur_per_litre=0.95
 * Unknown presets and invalid prices are ignored.
 */
export function formFromUrlParams(
  params: URLSearchParams,
  benchmarks: Record<string, SAFInput>,
  current: SAFInput,
): { form: SAFInput; presetKey: string | null } {
  const key = params.get('preset')
  const presetKey = key && benchmarks[key] ? key : null
  let form = presetKey ? benchmarks[presetKey] : current
  const jetPrice = Number(params.get('jet_fuel_price_eur_per_litre'))
  if (params.has('jet_fuel_price_eur_per_litre') && Number.isFinite(jetPrice) && jetPrice > 0) {
    form = { ...form, jet_fuel_price_eur_per_litre: jetPrice }
  }
  return { form, presetKey }
}

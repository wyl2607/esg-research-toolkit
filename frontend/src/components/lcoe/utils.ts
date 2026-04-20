import type { LCOEInput } from '@/lib/types'

export const TECHNOLOGIES = [
  'solar_pv',
  'wind_onshore',
  'wind_offshore',
  'battery_storage',
]

export const TECH_LABEL_KEYS: Record<string, string> = {
  solar_pv: 'lcoe.technologyOptions.solarPv',
  wind_onshore: 'lcoe.technologyOptions.windOnshore',
  wind_offshore: 'lcoe.technologyOptions.windOffshore',
  battery_storage: 'lcoe.technologyOptions.batteryStorage',
}

export const FX_PRESETS: Record<'EUR' | 'USD' | 'CNY', { label: string; fx: number }> = {
  EUR: { label: '1 EUR = 1.000 EUR', fx: 1.0 },
  USD: { label: '1 USD ≈ 0.920 EUR (2023 avg)', fx: 0.920 },
  CNY: { label: '1 CNY ≈ 0.127 EUR (2023 avg)', fx: 0.127 },
}

// Prices are stored in the row's native currency (EUR for DE, USD for US,
// CNY for CN) to stay readable — the LCOE input uses the same field name
// (`electricity_price_eur_per_mwh`) because the backend treats the number as
// "price in input currency" and converts via reference_fx_to_eur.
export const DE_MARKET_PRICES: { year: number; price: number; note?: string }[] = [
  { year: 2021, price: 96 },
  { year: 2022, price: 235, note: '⚡ energy crisis' },
  { year: 2023, price: 95 },
  { year: 2024, price: 65 },
]

export const US_MARKET_PRICES: { year: number; price: number; note?: string }[] = [
  { year: 2021, price: 39 },
  { year: 2022, price: 67, note: '⚡ gas spike' },
  { year: 2023, price: 40 },
  { year: 2024, price: 38 },
]

export const CN_MARKET_PRICES: { year: number; price: number }[] = [
  { year: 2021, price: 346 },
  { year: 2022, price: 382 },
  { year: 2023, price: 363 },
  { year: 2024, price: 370 },
]

export const FIELD_CONFIG: [keyof LCOEInput, string, string][] = [
  ['capacity_mw', 'capacity_mw', '0.1'],
  ['capacity_factor', 'lcoe.capacityFactor', '0.01'],
  ['capex_eur_per_kw', 'lcoe.capex', '1'],
  ['opex_eur_per_kw_year', 'lcoe.opex', '0.1'],
  ['lifetime_years', 'lcoe.lifetime', '1'],
  ['discount_rate', 'lcoe.discountRate', '0.001'],
  ['electricity_price_eur_per_mwh', 'lcoe.electricityPrice', '1'],
]

export const FIELD_UNIT_KEYS: Partial<Record<keyof LCOEInput, string>> = {
  capacity_mw: 'lcoe.unitMw',
  capacity_factor: 'lcoe.unitRatio',
  capex_eur_per_kw: 'lcoe.unitEurPerKw',
  opex_eur_per_kw_year: 'lcoe.unitEurPerKwYear',
  lifetime_years: 'lcoe.unitYears',
  discount_rate: 'lcoe.unitPercentApprox',
  electricity_price_eur_per_mwh: 'lcoe.unitEurPerMwh',
}

// Language ↔ market defaults: en→US, zh→CN, de/fallback→EU
function currencyForLanguage(lng: string): 'EUR' | 'USD' | 'CNY' {
  const tag = lng.toLowerCase()
  if (tag.startsWith('en')) return 'USD'
  if (tag.startsWith('zh')) return 'CNY'
  return 'EUR'
}

function defaultPriceForCurrency(currency: 'EUR' | 'USD' | 'CNY'): number {
  if (currency === 'USD') return US_MARKET_PRICES[US_MARKET_PRICES.length - 1].price
  if (currency === 'CNY') return CN_MARKET_PRICES[CN_MARKET_PRICES.length - 1].price
  return DE_MARKET_PRICES[DE_MARKET_PRICES.length - 1].price
}

function buildDefaults(currency: 'EUR' | 'USD' | 'CNY'): LCOEInput {
  return {
    technology: 'solar_pv',
    capacity_mw: 100,
    capacity_factor: 0.22,
    capex_eur_per_kw: 800,
    opex_eur_per_kw_year: 16,
    lifetime_years: 25,
    discount_rate: 0.05,
    electricity_price_eur_per_mwh: defaultPriceForCurrency(currency),
    currency,
    reference_fx_to_eur: FX_PRESETS[currency].fx,
  }
}

export function createInitialLcoeInput(language: string): LCOEInput {
  return buildDefaults(currencyForLanguage(language))
}

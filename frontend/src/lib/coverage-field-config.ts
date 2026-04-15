/**
 * Per-field metadata for the coverage drill-down page.
 *
 * target        – "ideal" value used to compute achievement %.
 *                 null means no target (absolute metric, rank only).
 * higherIsBetter – true: highest value = best (sort desc).
 *                  false: lowest value = best (sort asc, used for emissions).
 * unit          – display suffix.
 * format        – how to render the raw number.
 */
export interface FieldConfig {
  field: keyof import('./types').CompanyESGData
  label: string
  unit: string
  higherIsBetter: boolean
  /** implicit target value; null = ranking only */
  target: number | null
  format: (v: number) => string
}

const pct = (v: number) => `${v.toFixed(1)}%`
const tonnes = (v: number) =>
  v >= 1_000_000
    ? `${(v / 1_000_000).toFixed(2)}M t`
    : `${v.toLocaleString()} t`
const mwh = (v: number) =>
  v >= 1_000_000
    ? `${(v / 1_000_000).toFixed(2)}M MWh`
    : `${v.toLocaleString()} MWh`
const m3 = (v: number) =>
  v >= 1_000_000
    ? `${(v / 1_000_000).toFixed(2)}M m³`
    : `${v.toLocaleString()} m³`

export const FIELD_CONFIGS: FieldConfig[] = [
  {
    field: 'renewable_energy_pct',
    label: 'Renewable %',
    unit: '%',
    higherIsBetter: true,
    target: 100,
    format: pct,
  },
  {
    field: 'taxonomy_aligned_revenue_pct',
    label: 'Taxonomy %',
    unit: '%',
    higherIsBetter: true,
    target: 100,
    format: pct,
  },
  {
    field: 'taxonomy_aligned_capex_pct',
    label: 'CapEx Align %',
    unit: '%',
    higherIsBetter: true,
    target: 100,
    format: pct,
  },
  {
    field: 'waste_recycled_pct',
    label: 'Waste %',
    unit: '%',
    higherIsBetter: true,
    target: 100,
    format: pct,
  },
  {
    field: 'female_pct',
    label: 'Female %',
    unit: '%',
    higherIsBetter: true,
    /** Gender parity target = 50 % */
    target: 50,
    format: pct,
  },
  {
    field: 'scope1_co2e_tonnes',
    label: 'Scope 1',
    unit: 't CO₂e',
    higherIsBetter: false,
    target: null,
    format: tonnes,
  },
  {
    field: 'scope2_co2e_tonnes',
    label: 'Scope 2',
    unit: 't CO₂e',
    higherIsBetter: false,
    target: null,
    format: tonnes,
  },
  {
    field: 'scope3_co2e_tonnes',
    label: 'Scope 3',
    unit: 't CO₂e',
    higherIsBetter: false,
    target: null,
    format: tonnes,
  },
  {
    field: 'energy_consumption_mwh',
    label: 'Energy',
    unit: 'MWh',
    higherIsBetter: false,
    target: null,
    format: mwh,
  },
  {
    field: 'water_usage_m3',
    label: 'Water',
    unit: 'm³',
    higherIsBetter: false,
    target: null,
    format: m3,
  },
]

export const FIELD_CONFIG_MAP = Object.fromEntries(
  FIELD_CONFIGS.map((c) => [c.field, c])
) as Record<string, FieldConfig>

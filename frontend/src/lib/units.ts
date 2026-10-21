/**
 * Canonical unit symbols — the single source of truth for how a unit is
 * spelled anywhere in the UI.
 *
 * Before this module the same unit appeared as `tCO2e`, `tCO₂e` and `t CO₂e`
 * in different files, and `metric-unit` chips uppercased them into `TCO2E`.
 * Unit symbols are case- and glyph-sensitive, so they are constants here and
 * are never uppercased, translated or re-typed inline.
 */
export const UNITS = {
  /** Tonnes of CO2 equivalent. */
  tco2e: 'tCO₂e',
  /** Tonnes. */
  tonnes: 't',
  /** Megawatt hours. */
  mwh: 'MWh',
  /** Cubic metres. */
  m3: 'm³',
  /** Percent. */
  percent: '%',
  /** Euro per megawatt hour. */
  eurPerMwh: '€/MWh',
  /** Euro per kilowatt. */
  eurPerKw: '€/kW',
  /** Euro per kilowatt per year. */
  eurPerKwYear: '€/kW·a',
  /** Euro per tonne. */
  eurPerTonne: '€/t',
  /** Megawatt. */
  mw: 'MW',
} as const

export type UnitKey = keyof typeof UNITS

/**
 * No-break space (U+00A0) — keeps a value and its unit on one line so a
 * measurement is never split across a line break mid-number.
 * Percent is not assembled this way: Intl's percent style already inserts the
 * locale-correct separator (`29,5 %` in de, `29.5%` in en).
 */
export const UNIT_SEPARATOR = ' '

/** Value shown when a measurement is unknown. Never render 0 for unknown. */
export const UNKNOWN = '—'

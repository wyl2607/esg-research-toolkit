/**
 * Cross-framework comparability matrix.
 *
 * Regulatory basis:
 *  - EU Taxonomy 2020 (Regulation EU 2020/852): activity-based alignment
 *    criteria, mandatory Scope 1+2 for climate objectives, DNSH checks.
 *  - China CSRC 2023 (中国证监会上市公司可持续发展报告指引 2023):
 *    voluntary-first, qualitative ESG narrative, Scope 1+2 encouraged,
 *    no taxonomy alignment concept, social indicators are broad.
 *  - EU CSRD / ESRS 2024 (Corporate Sustainability Reporting Directive,
 *    ESRS E1/E2/E3/E4/S1/G1): mandatory Scope 1+2+3, double-materiality
 *    assessment, detailed workforce + value-chain indicators.
 *
 * comparability values:
 *   "comparable"         – the dimension uses the same or equivalent metric
 *                          definition across frameworks; cross-framework
 *                          numerical comparison is meaningful.
 *   "partial"            – the concept exists in all frameworks but
 *                          methodologies, scope, or thresholds differ;
 *                          directional comparison is possible but requires care.
 *   "not_comparable"     – the concept is absent or fundamentally different in
 *                          at least one framework; do not compare numerically.
 *
 * NOTE: "comparable" and "partial" judgements are based on the framework texts
 * themselves.  For company-level numeric scores, use the data returned by the
 * /frameworks/compare API rather than deriving values from this file.
 */

export type ComparabilityLevel = 'comparable' | 'partial' | 'not_comparable'

export interface DimensionComparability {
  /** Internal dimension key used in API responses (d.name from DimensionScore) */
  dimensionKey: string
  /** i18n key under frameworks.dim.* */
  labelKey: string
  eu_taxonomy: ComparabilityLevel
  csrc_2023: ComparabilityLevel
  csrd: ComparabilityLevel
  /** i18n key under frameworks.comparabilityMatrix.dimensionNotes.* */
  notesKey: string
}

/**
 * Full comparability matrix across EU Taxonomy, CSRC 2023, and CSRD/ESRS.
 *
 * Row order matches the typical radar order in FrameworksPage.
 */
export const FRAMEWORK_COMPARABILITY: DimensionComparability[] = [
  {
    dimensionKey: 'climate_mitigation',
    labelKey: 'climate_mitigation',
    eu_taxonomy: 'comparable',
    csrc_2023: 'partial',
    csrd: 'comparable',
    notesKey: 'climate_mitigation',
  },
  {
    dimensionKey: 'climate_adaptation',
    labelKey: 'climate_adaptation',
    eu_taxonomy: 'comparable',
    csrc_2023: 'not_comparable',
    csrd: 'comparable',
    notesKey: 'climate_adaptation',
  },
  {
    dimensionKey: 'water',
    labelKey: 'water',
    eu_taxonomy: 'partial',
    csrc_2023: 'partial',
    csrd: 'comparable',
    notesKey: 'water',
  },
  {
    dimensionKey: 'circular_economy',
    labelKey: 'circular_economy',
    eu_taxonomy: 'comparable',
    csrc_2023: 'not_comparable',
    csrd: 'comparable',
    notesKey: 'circular_economy',
  },
  {
    dimensionKey: 'pollution',
    labelKey: 'pollution',
    eu_taxonomy: 'comparable',
    csrc_2023: 'partial',
    csrd: 'comparable',
    notesKey: 'pollution',
  },
  {
    dimensionKey: 'biodiversity',
    labelKey: 'biodiversity',
    eu_taxonomy: 'comparable',
    csrc_2023: 'not_comparable',
    csrd: 'comparable',
    notesKey: 'biodiversity',
  },
  // CSRD-specific ESRS dimensions
  {
    dimensionKey: 'e1_climate',
    labelKey: 'e1_climate',
    eu_taxonomy: 'partial',
    csrc_2023: 'partial',
    csrd: 'comparable',
    notesKey: 'e1_climate',
  },
  {
    dimensionKey: 'e2_e5_pollution_circular',
    labelKey: 'e2_e5_pollution_circular',
    eu_taxonomy: 'partial',
    csrc_2023: 'not_comparable',
    csrd: 'comparable',
    notesKey: 'e2_e5_pollution_circular',
  },
  {
    dimensionKey: 'e3_water',
    labelKey: 'e3_water',
    eu_taxonomy: 'partial',
    csrc_2023: 'partial',
    csrd: 'comparable',
    notesKey: 'e3_water',
  },
  {
    dimensionKey: 'e4_biodiversity',
    labelKey: 'e4_biodiversity',
    eu_taxonomy: 'partial',
    csrc_2023: 'not_comparable',
    csrd: 'comparable',
    notesKey: 'e4_biodiversity',
  },
  {
    dimensionKey: 's1_workforce',
    labelKey: 's1_workforce',
    eu_taxonomy: 'not_comparable',
    csrc_2023: 'partial',
    csrd: 'comparable',
    notesKey: 's1_workforce',
  },
  {
    dimensionKey: 'g1_governance',
    labelKey: 'g1_governance',
    eu_taxonomy: 'not_comparable',
    csrc_2023: 'partial',
    csrd: 'comparable',
    notesKey: 'g1_governance',
  },
  // CSRC-specific dimensions
  {
    dimensionKey: 'csrc_environment',
    labelKey: 'csrc_environment',
    eu_taxonomy: 'partial',
    csrc_2023: 'comparable',
    csrd: 'partial',
    notesKey: 'csrc_environment',
  },
  {
    dimensionKey: 'csrc_social',
    labelKey: 'csrc_social',
    eu_taxonomy: 'not_comparable',
    csrc_2023: 'comparable',
    csrd: 'partial',
    notesKey: 'csrc_social',
  },
  {
    dimensionKey: 'csrc_governance',
    labelKey: 'csrc_governance',
    eu_taxonomy: 'not_comparable',
    csrc_2023: 'comparable',
    csrd: 'partial',
    notesKey: 'csrc_governance',
  },
]

/** Look up a single dimension by its API key */
export const COMPARABILITY_MAP = Object.fromEntries(
  FRAMEWORK_COMPARABILITY.map((d) => [d.dimensionKey, d])
) as Record<string, DimensionComparability>

/** Ordered list of framework IDs used throughout the app */
export const FRAMEWORK_IDS = ['eu_taxonomy', 'csrc_2023', 'csrd'] as const
export type FrameworkId = (typeof FRAMEWORK_IDS)[number]

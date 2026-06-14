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
  /** Short rationale explaining the comparability rating */
  notes: string
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
    notes:
      'EU Taxonomy and CSRD both require Scope 1+2 under standardised GHG Protocol methods. ' +
      'CSRC 2023 encourages Scope 1+2 but does not mandate a specific protocol, so methodology may differ.',
  },
  {
    dimensionKey: 'climate_adaptation',
    labelKey: 'climate_adaptation',
    eu_taxonomy: 'comparable',
    csrc_2023: 'not_comparable',
    csrd: 'comparable',
    notes:
      'EU Taxonomy defines six climate-adaptation objectives with DNSH criteria. ' +
      'CSRD (ESRS E1) requires climate-risk disclosures aligned with the same objectives. ' +
      'CSRC 2023 has no equivalent structured climate-adaptation requirement.',
  },
  {
    dimensionKey: 'water',
    labelKey: 'water',
    eu_taxonomy: 'partial',
    csrc_2023: 'partial',
    csrd: 'comparable',
    notes:
      'CSRD (ESRS E3) requires quantitative water-usage and water-stress indicators. ' +
      'EU Taxonomy includes water as a DNSH objective but does not mandate a standalone metric. ' +
      'CSRC 2023 asks for water-usage data on a best-effort basis; comparability depends on what is actually disclosed.',
  },
  {
    dimensionKey: 'circular_economy',
    labelKey: 'circular_economy',
    eu_taxonomy: 'comparable',
    csrc_2023: 'not_comparable',
    csrd: 'comparable',
    notes:
      'Circular economy is a named objective under both EU Taxonomy (CE activities list) and ' +
      'CSRD (ESRS E5). CSRC 2023 does not include a structured circular-economy dimension; ' +
      'waste-recycled % is the closest proxy but is not defined equivalently.',
  },
  {
    dimensionKey: 'pollution',
    labelKey: 'pollution',
    eu_taxonomy: 'comparable',
    csrc_2023: 'partial',
    csrd: 'comparable',
    notes:
      'EU Taxonomy and CSRD (ESRS E2) both define pollution prevention as a standalone objective ' +
      'with specific substance lists. CSRC 2023 requires pollution disclosures mainly for ' +
      'heavy-industry companies; the scope and substance lists differ.',
  },
  {
    dimensionKey: 'biodiversity',
    labelKey: 'biodiversity',
    eu_taxonomy: 'comparable',
    csrc_2023: 'not_comparable',
    csrd: 'comparable',
    notes:
      'EU Taxonomy (objective 6) and CSRD (ESRS E4) both reference biodiversity and ecosystems. ' +
      'CSRC 2023 does not have a biodiversity-specific disclosure requirement; any related ' +
      'disclosures are voluntary and non-standardised.',
  },
  // CSRD-specific ESRS dimensions
  {
    dimensionKey: 'e1_climate',
    labelKey: 'e1_climate',
    eu_taxonomy: 'partial',
    csrc_2023: 'partial',
    csrd: 'comparable',
    notes:
      'ESRS E1 is the primary CSRD climate standard covering Scope 1+2+3 and transition plans. ' +
      'EU Taxonomy addresses climate mitigation/adaptation through activity criteria rather than ' +
      'company-level disclosures. CSRC 2023 covers Scope 1+2 but omits Scope 3 and transition plans.',
  },
  {
    dimensionKey: 'e2_e5_pollution_circular',
    labelKey: 'e2_e5_pollution_circular',
    eu_taxonomy: 'partial',
    csrc_2023: 'not_comparable',
    csrd: 'comparable',
    notes:
      'ESRS E2 (pollution) and E5 (circular economy) are combined here. EU Taxonomy covers both ' +
      'as DNSH objectives. CSRC 2023 lacks equivalent structured requirements for both topics.',
  },
  {
    dimensionKey: 'e3_water',
    labelKey: 'e3_water',
    eu_taxonomy: 'partial',
    csrc_2023: 'partial',
    csrd: 'comparable',
    notes:
      'ESRS E3 (water and marine resources) requires granular disclosure including water-stress ' +
      'areas. EU Taxonomy covers water as a DNSH objective without a dedicated metric. ' +
      'CSRC 2023 asks for water data but without water-stress context.',
  },
  {
    dimensionKey: 'e4_biodiversity',
    labelKey: 'e4_biodiversity',
    eu_taxonomy: 'partial',
    csrc_2023: 'not_comparable',
    csrd: 'comparable',
    notes:
      'ESRS E4 (biodiversity) and EU Taxonomy objective 6 are structurally aligned. ' +
      'CSRC 2023 has no biodiversity-specific requirement.',
  },
  {
    dimensionKey: 's1_workforce',
    labelKey: 's1_workforce',
    eu_taxonomy: 'not_comparable',
    csrc_2023: 'partial',
    csrd: 'comparable',
    notes:
      'ESRS S1 (own workforce) requires headcount, gender pay gap, working conditions, and ' +
      'collective bargaining coverage. EU Taxonomy does not assess social indicators at the ' +
      'dimension level. CSRC 2023 requires gender ratio and employee welfare but at lower granularity.',
  },
  {
    dimensionKey: 'g1_governance',
    labelKey: 'g1_governance',
    eu_taxonomy: 'not_comparable',
    csrc_2023: 'partial',
    csrd: 'comparable',
    notes:
      'ESRS G1 (business conduct) covers anti-corruption, supplier due diligence, and political ' +
      'engagement. EU Taxonomy does not address governance directly. CSRC 2023 includes board ' +
      'composition and anti-corruption items but uses different definitions.',
  },
  // CSRC-specific dimensions
  {
    dimensionKey: 'csrc_environment',
    labelKey: 'csrc_environment',
    eu_taxonomy: 'partial',
    csrc_2023: 'comparable',
    csrd: 'partial',
    notes:
      'CSRC Environment bundles Scope 1+2, energy, and waste into one dimension. ' +
      'EU Taxonomy addresses overlapping indicators via activity criteria and DNSH. ' +
      'CSRD separates these into E1–E5; a direct score comparison with CSRC_ENV is only directional.',
  },
  {
    dimensionKey: 'csrc_social',
    labelKey: 'csrc_social',
    eu_taxonomy: 'not_comparable',
    csrc_2023: 'comparable',
    csrd: 'partial',
    notes:
      'CSRC Social covers workforce, community investment, and product safety. ' +
      'EU Taxonomy has no social scoring dimension. CSRD (S1–S4) is more granular; ' +
      'a combined CSRC Social score is only partially comparable to individual ESRS S-standards.',
  },
  {
    dimensionKey: 'csrc_governance',
    labelKey: 'csrc_governance',
    eu_taxonomy: 'not_comparable',
    csrc_2023: 'comparable',
    csrd: 'partial',
    notes:
      'CSRC Governance covers board structure, ownership transparency, and anti-corruption ' +
      'aligned with Chinese corporate-governance rules (CSRC Code 2023). ' +
      'EU Taxonomy omits governance scoring. CSRD (G1) overlaps partially but uses OECD ' +
      'and UNGP frameworks rather than CSRC rules.',
  },
]

/** Look up a single dimension by its API key */
export const COMPARABILITY_MAP = Object.fromEntries(
  FRAMEWORK_COMPARABILITY.map((d) => [d.dimensionKey, d])
) as Record<string, DimensionComparability>

/** Ordered list of framework IDs used throughout the app */
export const FRAMEWORK_IDS = ['eu_taxonomy', 'csrc_2023', 'csrd'] as const
export type FrameworkId = (typeof FRAMEWORK_IDS)[number]

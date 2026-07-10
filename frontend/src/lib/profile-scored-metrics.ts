/**
 * Prefer CompanyProfile v1 scored_metrics for evidence and framework mappings.
 * Legacy evidence_summary / evidence_anchors remain as fallbacks.
 */

import type {
  CompanyProfile,
  CompanyProfileMetric,
  CompanySourceDocument,
  EvidenceAnchor,
  FrameworkMetricMapping,
} from '@/lib/types'
import {
  evidenceRichness,
  mergeEvidenceAnchor,
  normalizeProfileEvidenceAnchor,
} from '@/pages/company-profile/utils'

export function scoredMetricEvidenceToAnchor(
  metricKey: string,
  scored: CompanyProfileMetric
): EvidenceAnchor | null {
  const evidence = scored.evidence
  if (!evidence) return null

  const sourceDocId = evidence.source_doc_id
  const periodLabel = scored.period?.label ?? null

  return {
    metric: metricKey,
    source: sourceDocId,
    page: evidence.page ?? null,
    page_number: evidence.page ?? null,
    snippet: evidence.snippet ?? null,
    source_doc_id: sourceDocId,
    char_range: evidence.char_range ?? null,
    extraction_method: evidence.extraction_method ?? null,
    confidence: evidence.confidence,
    confidence_score:
      typeof evidence.confidence === 'number' ? evidence.confidence : null,
    source_type: scored.source_document_type ?? null,
    framework: scored.source_document_type ?? null,
    reporting_period_label: periodLabel,
    period_label: periodLabel,
    document_title: sourceDocId,
    document_short_ref: null,
    source_url: null,
    file_hash: null,
    framework_mappings: scored.framework_mappings ?? [],
  }
}

export function collectLegacyEvidenceAnchors(
  profile: Pick<
    CompanyProfile,
    | 'latest_sources'
    | 'evidence_summary'
    | 'evidence_anchors'
    | 'latest_period'
  >
): EvidenceAnchor[] {
  const latestSources = profile.latest_sources ?? []
  const raw = [
    ...latestSources.flatMap((source) => source.evidence_anchors ?? []),
    ...(profile.evidence_summary ?? []),
    ...(profile.evidence_anchors ?? []),
  ]

  return raw
    .map((entry) =>
      normalizeProfileEvidenceAnchor(
        entry,
        latestSources,
        profile.latest_period.reporting_period_label,
        profile.latest_period.source_document_type
      )
    )
    .sort((a, b) => evidenceRichness(b) - evidenceRichness(a))
    .reduce<EvidenceAnchor[]>((acc, normalized) => {
      const key =
        normalized.metric ??
        `${normalized.document_title ?? normalized.source ?? 'evidence'}-${acc.length}`
      const existingIndex = acc.findIndex((item) => item.metric === key)

      if (existingIndex === -1) {
        acc.push({ ...normalized, metric: normalized.metric ?? key })
        return acc
      }

      acc[existingIndex] = mergeEvidenceAnchor(acc[existingIndex], normalized)
      return acc
    }, [])
}

/**
 * Build per-metric evidence preferring scored_metrics (v1), then legacy anchors.
 * Framework mappings from scored_metrics are attached even when legacy evidence wins.
 */
export function buildEvidenceByMetric(
  profile: CompanyProfile
): Map<string, EvidenceAnchor> {
  const latestSources: CompanySourceDocument[] = profile.latest_sources ?? []
  const map = new Map<string, EvidenceAnchor>()

  const scored = profile.scored_metrics ?? {}
  for (const [metricKey, scoredMetric] of Object.entries(scored)) {
    const fromScored = scoredMetricEvidenceToAnchor(metricKey, scoredMetric)
    if (!fromScored) continue

    const normalized = normalizeProfileEvidenceAnchor(
      fromScored,
      latestSources,
      profile.latest_period.reporting_period_label,
      profile.latest_period.source_document_type ??
        scoredMetric.source_document_type
    )
    map.set(metricKey, {
      ...normalized,
      metric: metricKey,
      framework_mappings:
        scoredMetric.framework_mappings ?? normalized.framework_mappings ?? [],
    })
  }

  for (const legacy of collectLegacyEvidenceAnchors(profile)) {
    if (!legacy.metric) continue
    const existing = map.get(legacy.metric)
    if (!existing) {
      map.set(legacy.metric, legacy)
      continue
    }
    // Enrich scored-first anchors with richer legacy document titles / snippets.
    // Prefer human-readable legacy titles when scored evidence only has a doc id.
    const merged = mergeEvidenceAnchor(existing, legacy)
    const scoredTitleLooksLikeId =
      !!existing.document_title &&
      (existing.document_title === existing.source ||
        existing.document_title === existing.source_doc_id ||
        existing.document_title === existing.file_hash)
    if (scoredTitleLooksLikeId && legacy.document_title) {
      merged.document_title = legacy.document_title
      if (legacy.document_short_ref) {
        merged.document_short_ref = legacy.document_short_ref
      }
    }
    map.set(legacy.metric, {
      ...merged,
      framework_mappings:
        existing.framework_mappings ?? legacy.framework_mappings ?? [],
    })
  }

  return map
}

export function formatFrameworkMappingLabel(
  mapping: FrameworkMetricMapping
): string {
  const name = mapping.framework_name || mapping.framework_id
  return mapping.dimension ? `${name} · ${mapping.dimension}` : name
}

export function frameworkMappingsFromScored(
  profile: CompanyProfile | null | undefined,
  metricKey: string
): FrameworkMetricMapping[] {
  return profile?.scored_metrics?.[metricKey]?.framework_mappings ?? []
}

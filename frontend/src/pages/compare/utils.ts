import type { CompanyESGData } from '@/lib/types'

export function prettifyCompareToken(value: string | null | undefined): string | null {
  if (!value) return null
  return value.replace(/[_-]+/g, ' ')
}

export function comparePeriodLabel(company: CompanyESGData): string {
  return (
    company.period?.label ??
    company.reporting_period_label ??
    String(company.report_year)
  )
}

export function compareSourceDocumentType(company: CompanyESGData): string | null {
  return prettifyCompareToken(
    company.period?.source_document_type ?? company.source_document_type ?? null
  )
}

export function compareEvidenceCount(company: CompanyESGData): number {
  return company.evidence_summary?.length ?? 0
}

export function compareSourceContext(company: CompanyESGData): string {
  return [comparePeriodLabel(company), compareSourceDocumentType(company)]
    .filter(Boolean)
    .join(' · ')
}

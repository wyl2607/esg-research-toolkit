/**
 * Type augmentations for API response fields that exist at runtime
 * but are not in the generated OpenAPI types.
 *
 * These fields are returned by the backend API (_source_document_payload,
 * _evidence_anchors_for_record) but not declared in Pydantic response models,
 * so the type generator doesn't include them.
 */

declare module './types' {
  interface EvidenceAnchor {
    source_doc_id?: string | null
    char_range?: [number, number] | number[] | null
  }

  interface CompanyESGData {
    source_url?: string | null
    file_hash?: string | null
    pdf_filename?: string | null
    downloaded_at?: string | null
    period?: CompanyNormalizedPeriod | null
    framework_metadata?: FrameworkMetadata[]
    source_documents?: CompanySourceDocument[]
  }

  interface CompanyNormalizedPeriod {
    fiscal_year?: number
    reporting_standard?: string
    period_start?: string | null
    period_end?: string | null
  }

  interface CompanySourceDocument {
    period?: CompanyNormalizedPeriod | null
    framework_metadata?: FrameworkMetadata[]
  }
}

# CompanyProfile v1 contract

Path: `/api/v1/companies/{company_name}/profile`

Legacy alias for one release:

- `/report/companies/{company_name}/profile`
- response header: `Deprecation: true`

## Stable v1 additions

- `api_version: "v1"`
- `scored_metrics.{metric}` entries with:
  - `value`
  - `unit`
  - `period`
  - `source_document_type`
  - `evidence`
  - `framework_mappings`
- normalized period fields on `latest_period.period` and each `periods[*].period`:
  - `fiscal_year`
  - `reporting_standard`
  - `period_start`
  - `period_end`

## Evidence contract

Canonical per-metric evidence lives at `scored_metrics.{metric}.evidence`.

```json
{
  "source_doc_id": "hash-v1-contract-2024",
  "page": 12,
  "char_range": [420, 441],
  "snippet": "Renewable electricity share increased to 45%.",
  "extraction_method": "regex",
  "confidence": 0.91
}
```

Rules:

- every scored metric with a non-null value must expose a non-null `evidence`
- manual entries use `extraction_method = "manual"`
- legacy `evidence_summary` / `evidence_anchors` remain additive compatibility surfaces

## Period normalization

`reporting_standard` is currently derived from `source_document_type` until an explicit reporting-standard field is stored upstream.

Examples:

- `annual_report -> annual_report`
- `sustainability_report -> sustainability_report`
- `manual_case -> manual_case`

For annual periods the API normalizes dates to the fiscal-year bounds:

- `period_start = YYYY-01-01`
- `period_end = YYYY-12-31`

Quarterly / half-year labels are normalized when the label or type contains quarter / half-year markers.

## Framework mappings

`scored_metrics.{metric}.framework_mappings` is a stable, additive registry of which framework scorers consume or explain a metric.

Example:

```json
[
  {
    "framework_id": "eu_taxonomy",
    "framework_name": "EU Taxonomy 2020",
    "dimension": "Climate"
  }
]
```

## Backward compatibility

- legacy top-level fields remain present (`latest_metrics`, `trend`, `periods`, `framework_results`, `evidence_summary`)
- v1 consumers should prefer:
  - `scored_metrics`
  - `latest_period.period`
  - `periods[*].period`

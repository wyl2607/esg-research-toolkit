# Data Integrity Controls

This document captures runtime data-integrity controls introduced in April 2026.

## 1) DB-Level Uniqueness

### `company_reports`

Uniqueness key:

- `(company_name, report_year, source_doc_key)`

`source_doc_key` is deterministic:

1. `file_hash:<sha256>`
2. `source_url:<url>|type:<source_document_type>`
3. `pdf_filename:<filename>|type:<source_document_type>`
4. `period:<source_document_type>|label:<reporting_period_label_or_year>`

This prevents silent duplicate rows from app-level race conditions or source naming drift.

### `framework_analysis_results`

Uniqueness key:

- `(company_name, report_year, framework_id, framework_version, payload_hash)`

`payload_hash` is SHA-256 over canonical serialized result payload.

This guarantees idempotent persistence for payload-identical framework runs.

## 2) L0 Validation Policy

Environment flags:

- `L0_FAIL_CLOSED` (default: `true`)
- `L0_FAIL_OPEN_BYPASS` (default: `false`)

Behavior:

- when fail-closed is enabled and L0 emits errors, writes are blocked
- bypass is explicit and intended for emergency operations only

API behavior:

- ingestion/manual persistence paths return HTTP 422 when blocked by fail-closed validation

## 3) Migration Gate (Production Option)

Environment flag:

- `ENFORCE_MIGRATION_GATE` (default: `false`)

When enabled together with `APP_ENV=production`:

- service startup requires `alembic_version` table to exist
- `alembic_version.version_num` must be populated

This prevents startup against unmanaged production schemas.

## 4) SQLite Startup Backfill

For legacy SQLite deployments, startup schema routines:

- backfill missing `source_doc_key` / `payload_hash`
- deduplicate rows before unique indexes are created

This keeps existing local databases forward-compatible.

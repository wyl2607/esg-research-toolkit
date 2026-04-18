import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from core.config import settings
from core.database import Base
from core.schemas import CompanyESGData
from core.validation import has_errors, validate_record
from report_parser.company_identity import (
    canonical_company_name,
    collapse_company_records,
    company_name_variants,
    report_quality_score,
)

_logger = logging.getLogger(__name__)

DEFAULT_REPORTING_PERIOD_TYPE = "annual"
DEFAULT_SOURCE_DOCUMENT_TYPE = "sustainability_report"


def _normalized_period_fields(
    data: CompanyESGData,
    *,
    reporting_period_label: str | None = None,
    reporting_period_type: str | None = None,
    source_document_type: str | None = None,
) -> tuple[str, str, str]:
    """
    Transitional contract (Task 27B):
    - legacy report_year stays canonical for compatibility
    - period label/type/document are normalized additively around report_year
    """
    label = reporting_period_label or data.reporting_period_label or str(data.report_year)
    period_type = reporting_period_type or data.reporting_period_type or DEFAULT_REPORTING_PERIOD_TYPE
    document_type = source_document_type or data.source_document_type or DEFAULT_SOURCE_DOCUMENT_TYPE
    return label, period_type, document_type


class CompanyReport(Base):
    __tablename__ = "company_reports"
    __table_args__ = (
        UniqueConstraint("company_name", "report_year", "source_doc_key", name="uq_company_reports_source_key"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String, nullable=False, index=True)
    report_year = Column(Integer, nullable=False)
    reporting_period_label = Column(String, nullable=True)
    reporting_period_type = Column(String, nullable=True)  # annual | quarterly | event
    source_document_type = Column(String, nullable=True)  # annual_report | sustainability_report | filing
    industry_code = Column(String, nullable=True, index=True)
    industry_sector = Column(String, nullable=True)

    # ── ESG metrics ──────────────────────────────────────────────────────────
    scope1_co2e_tonnes = Column(Float, nullable=True)
    scope2_co2e_tonnes = Column(Float, nullable=True)
    scope3_co2e_tonnes = Column(Float, nullable=True)
    energy_consumption_mwh = Column(Float, nullable=True)
    renewable_energy_pct = Column(Float, nullable=True)
    water_usage_m3 = Column(Float, nullable=True)
    waste_recycled_pct = Column(Float, nullable=True)
    total_revenue_eur = Column(Float, nullable=True)
    taxonomy_aligned_revenue_pct = Column(Float, nullable=True)
    total_capex_eur = Column(Float, nullable=True)
    taxonomy_aligned_capex_pct = Column(Float, nullable=True)
    total_employees = Column(Integer, nullable=True)
    female_pct = Column(Float, nullable=True)
    primary_activities = Column(Text, nullable=True)

    # ── Source provenance (compliance requirement) ───────────────────────────
    pdf_filename = Column(String, nullable=True)
    source_url = Column(String, nullable=True)        # 原始 PDF 来源 URL
    file_hash = Column(String, nullable=True)         # SHA-256 of original PDF
    source_doc_key = Column(String, nullable=False, default="")
    downloaded_at = Column(DateTime, nullable=True)   # 下载/上传时间
    evidence_summary = Column(Text, nullable=True)    # JSON-encoded metric evidence summaries
    deletion_requested = Column(Boolean, default=False, nullable=False)  # 来源删除请求标记
    deletion_requested_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


def save_report(
    db: Session,
    data: CompanyESGData,
    pdf_filename: str | None = None,
    source_url: str | None = None,
    file_hash: str | None = None,
    downloaded_at: datetime | None = None,
    reporting_period_label: str | None = None,
    reporting_period_type: str | None = None,
    source_document_type: str | None = None,
    evidence_summary: list[dict[str, str | int | float | None]] | None = None,
) -> CompanyReport:
    """保存企业报告（含来源追溯字段）。同一 company+year 保留多来源，按来源指纹去重更新。"""
    canonical_name = canonical_company_name(data.company_name)
    normalized_data = data.model_copy(update={"company_name": canonical_name})
    period_label, period_type, document_type = _normalized_period_fields(
        normalized_data,
        reporting_period_label=reporting_period_label,
        reporting_period_type=reporting_period_type,
        source_document_type=source_document_type,
    )
    name_variants = [variant.lower() for variant in company_name_variants(canonical_name)]
    source_key = _build_source_doc_key(
        file_hash=file_hash,
        source_url=source_url,
        pdf_filename=pdf_filename,
        source_document_type=document_type,
        reporting_period_label=period_label,
        report_year=normalized_data.report_year,
    )

    candidates = (
        db.query(CompanyReport)
        .filter(
            func.lower(CompanyReport.company_name).in_(name_variants),
            CompanyReport.report_year == normalized_data.report_year,
            CompanyReport.source_doc_key == source_key,
        )
        .all()
    )
    record: CompanyReport | None = None
    if candidates:
        record = max(candidates, key=report_quality_score)
    now = datetime.now(timezone.utc)
    if record is None:
        record = CompanyReport(
            company_name=canonical_name,
            report_year=normalized_data.report_year,
            reporting_period_label=period_label,
            reporting_period_type=period_type,
            source_document_type=document_type,
            pdf_filename=pdf_filename,
            source_url=source_url,
            file_hash=file_hash,
            source_doc_key=source_key,
            downloaded_at=downloaded_at or now,
            evidence_summary=json.dumps(
                evidence_summary if evidence_summary is not None else normalized_data.evidence_summary
            ),
        )
        db.add(record)
    else:
        record.company_name = canonical_name
        if pdf_filename:
            record.pdf_filename = pdf_filename
        if source_url:
            record.source_url = source_url
        if file_hash:
            record.file_hash = file_hash
        record.source_doc_key = source_key
        if downloaded_at:
            record.downloaded_at = downloaded_at
        record.reporting_period_label = period_label
        record.reporting_period_type = period_type
        record.source_document_type = document_type
        if evidence_summary is not None:
            record.evidence_summary = json.dumps(evidence_summary)

    if not record.reporting_period_label:
        record.reporting_period_label = period_label
    if not record.reporting_period_type:
        record.reporting_period_type = period_type
    if not record.source_document_type:
        record.source_document_type = document_type
    if not record.source_doc_key:
        record.source_doc_key = source_key
    if evidence_summary is None and not record.evidence_summary:
        record.evidence_summary = json.dumps(normalized_data.evidence_summary)

    record.scope1_co2e_tonnes = normalized_data.scope1_co2e_tonnes
    record.scope2_co2e_tonnes = normalized_data.scope2_co2e_tonnes
    record.scope3_co2e_tonnes = normalized_data.scope3_co2e_tonnes
    record.industry_code = normalized_data.industry_code
    record.industry_sector = normalized_data.industry_sector
    record.energy_consumption_mwh = normalized_data.energy_consumption_mwh
    record.renewable_energy_pct = normalized_data.renewable_energy_pct
    record.water_usage_m3 = normalized_data.water_usage_m3
    record.waste_recycled_pct = normalized_data.waste_recycled_pct
    record.total_revenue_eur = normalized_data.total_revenue_eur
    record.taxonomy_aligned_revenue_pct = normalized_data.taxonomy_aligned_revenue_pct
    record.total_capex_eur = normalized_data.total_capex_eur
    record.taxonomy_aligned_capex_pct = normalized_data.taxonomy_aligned_capex_pct
    record.total_employees = normalized_data.total_employees
    record.female_pct = normalized_data.female_pct
    record.primary_activities = json.dumps(normalized_data.primary_activities)

    # ── L0 physical-bounds validation (soft fail: log only) ──────────────
    issues = validate_record(normalized_data.model_dump())
    if issues:
        for issue in issues:
            _logger.warning(
                "save_report L0 validation %s: %s",
                issue.severity,
                issue.message,
            )
        if has_errors(issues):
            _logger.error(
                "save_report storing record %s/%s with %d L0 errors — review needed",
                canonical_name,
                normalized_data.report_year,
                sum(1 for i in issues if i.severity == "error"),
            )
            if settings.l0_fail_closed and not settings.l0_fail_open_bypass:
                raise ValueError(
                    "L0 validation failed (fail-closed). "
                    "Set L0_FAIL_OPEN_BYPASS=true for emergency bypass."
                )

    db.commit()
    db.refresh(record)
    return record


def get_report(db: Session, company_name: str, report_year: int) -> CompanyReport | None:
    variants = [variant.lower() for variant in company_name_variants(company_name)]
    records = (
        db.query(CompanyReport)
        .filter(
            func.lower(CompanyReport.company_name).in_(variants),
            CompanyReport.report_year == report_year,
            CompanyReport.deletion_requested.is_(False),
        )
        .all()
    )
    collapsed = collapse_company_records(records)
    return collapsed[0] if collapsed else None


def list_reports(db: Session, skip: int = 0, limit: int = 50) -> list[CompanyReport]:
    return db.query(CompanyReport).offset(skip).limit(limit).all()


def list_reports_for_company(
    db: Session,
    company_name: str,
    *,
    include_deleted: bool = False,
) -> list[CompanyReport]:
    variants = [variant.lower() for variant in company_name_variants(company_name)]
    query = db.query(CompanyReport).filter(func.lower(CompanyReport.company_name).in_(variants))
    if not include_deleted:
        query = query.filter(CompanyReport.deletion_requested.is_(False))
    records = query.order_by(CompanyReport.report_year.asc()).all()
    return collapse_company_records(records)


def list_source_reports_for_company_year(
    db: Session,
    company_name: str,
    report_year: int,
    *,
    include_deleted: bool = False,
    collapse_duplicates: bool = True,
) -> list[CompanyReport]:
    def _collapse_source_duplicates(records: list[CompanyReport]) -> list[CompanyReport]:
        grouped: dict[tuple[str, int, str, str, str, str, str, str], list[CompanyReport]] = {}
        for record in records:
            canonical = canonical_company_name(record.company_name)
            key = (
                canonical.lower(),
                record.report_year,
                (record.source_document_type or "").strip().lower(),
                (record.reporting_period_label or "").strip().lower(),
                (record.reporting_period_type or "").strip().lower(),
                (record.source_url or "").strip().lower(),
                (record.file_hash or "").strip().lower(),
                (record.pdf_filename or "").strip().lower(),
            )
            grouped.setdefault(key, []).append(record)

        collapsed: list[CompanyReport] = []
        for candidates in grouped.values():
            best = max(candidates, key=report_quality_score)
            collapsed.append(best)

        collapsed.sort(
            key=lambda item: (
                item.report_year,
                (item.source_document_type or "").lower(),
                item.id,
            )
        )
        return collapsed

    variants = [variant.lower() for variant in company_name_variants(company_name)]
    query = db.query(CompanyReport).filter(
        func.lower(CompanyReport.company_name).in_(variants),
        CompanyReport.report_year == report_year,
    )
    if not include_deleted:
        query = query.filter(CompanyReport.deletion_requested.is_(False))
    records = query.order_by(
        CompanyReport.updated_at.asc(),
        CompanyReport.created_at.asc(),
        CompanyReport.id.asc(),
    ).all()
    if not collapse_duplicates:
        return records
    return _collapse_source_duplicates(records)


def list_reports_grouped(
    db: Session,
    *,
    include_deleted: bool = False,
) -> list[CompanyReport]:
    query = db.query(CompanyReport)
    if not include_deleted:
        query = query.filter(CompanyReport.deletion_requested.is_(False))
    return collapse_company_records(query.all())


def request_deletion(db: Session, company_name: str, report_year: int) -> CompanyReport | None:
    """标记来源删除请求，同时删除本地 PDF 副本（如存在）。"""
    from pathlib import Path

    variants = [variant.lower() for variant in company_name_variants(company_name)]
    records = (
        db.query(CompanyReport)
        .filter(
            func.lower(CompanyReport.company_name).in_(variants),
            CompanyReport.report_year == report_year,
            CompanyReport.deletion_requested.is_(False),
        )
        .all()
    )
    if not records:
        return None

    for record in records:
        if record.pdf_filename:
            pdf_path = Path("data/reports") / record.pdf_filename
            if pdf_path.exists():
                pdf_path.unlink()
        record.deletion_requested = True
        record.deletion_requested_at = datetime.now(timezone.utc)
        record.pdf_filename = None
    db.commit()
    representative = collapse_company_records(records)[0]
    db.refresh(representative)
    return representative


def hard_delete_report(db: Session, company_name: str, report_year: int) -> bool:
    """彻底删除记录（含所有提取数据），用于响应正式删除请求。"""
    from pathlib import Path

    variants = [variant.lower() for variant in company_name_variants(company_name)]
    records = (
        db.query(CompanyReport)
        .filter(
            func.lower(CompanyReport.company_name).in_(variants),
            CompanyReport.report_year == report_year,
        )
        .all()
    )
    if not records:
        return False

    for record in records:
        if record.pdf_filename:
            pdf_path = Path("data/reports") / record.pdf_filename
            if pdf_path.exists():
                pdf_path.unlink()
        db.delete(record)
    db.commit()
    return True


class ExtractionRun(Base):
    """Append-only audit trail for every extraction / validation pass.

    Each row records one (PDF, model, prompt) triple so that every benchmark
    number can be traced back to: company_report → extraction_run → raw PDF hash.
    """

    __tablename__ = "extraction_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_report_id = Column(Integer, nullable=True, index=True)
    file_hash = Column(String, nullable=True, index=True)         # SHA-256 of source PDF
    run_kind = Column(String, nullable=False, index=True)          # extract | audit | validate | manual
    model = Column(String, nullable=True)                          # gpt-4o, gpt-4o-mini, manual, ...
    prompt_hash = Column(String, nullable=True)                    # SHA-1 of the prompt template (for repro)
    raw_response = Column(Text, nullable=True)                     # JSON blob (truncated at 64KB by writer)
    verdict = Column(String, nullable=True)                        # ok | warn | error | applied
    applied = Column(Boolean, default=False, nullable=False)       # did this run write back to canonical?
    notes = Column(Text, nullable=True)                            # short human/AI summary
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class PendingDisclosure(Base):
    """Queue for auto-fetched disclosures awaiting approval into company_reports."""

    __tablename__ = "pending_disclosures"
    __table_args__ = (
        UniqueConstraint(
            "company_name",
            "report_year",
            "source_url",
            name="uq_pending_disclosures_source",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String, nullable=False, index=True)
    report_year = Column(Integer, nullable=False, index=True)
    source_url = Column(String, nullable=False)
    source_type = Column(String, nullable=False, default="pdf")
    fetched_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    extracted_payload = Column(Text, nullable=False, default="{}")
    status = Column(String, nullable=False, default="pending", index=True)
    review_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


def upsert_pending_disclosure(
    db: Session,
    *,
    company_name: str,
    report_year: int,
    source_url: str,
    source_type: str,
    extracted_payload: dict[str, Any],
    status: str = "pending",
    review_note: str | None = None,
) -> tuple[PendingDisclosure, bool]:
    canonical_name = canonical_company_name(company_name)
    existing = (
        db.query(PendingDisclosure)
        .filter(
            PendingDisclosure.company_name == canonical_name,
            PendingDisclosure.report_year == report_year,
            PendingDisclosure.source_url == source_url,
        )
        .first()
    )
    now = datetime.now(timezone.utc)
    payload_json = json.dumps(extracted_payload)

    if existing is None:
        row = PendingDisclosure(
            company_name=canonical_name,
            report_year=report_year,
            source_url=source_url,
            source_type=source_type,
            fetched_at=now,
            extracted_payload=payload_json,
            status=status,
            review_note=review_note,
        )
        db.add(row)
        created = True
    else:
        row = existing
        row.source_type = source_type
        row.fetched_at = now
        row.extracted_payload = payload_json
        row.status = status
        row.review_note = review_note
        created = False

    db.commit()
    db.refresh(row)
    return row, created


def list_pending_disclosures(
    db: Session,
    *,
    company_name: str | None = None,
    report_year: int | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[PendingDisclosure]:
    query = db.query(PendingDisclosure)
    if company_name:
        variants = [variant.lower() for variant in company_name_variants(company_name)]
        query = query.filter(func.lower(PendingDisclosure.company_name).in_(variants))
    if report_year is not None:
        query = query.filter(PendingDisclosure.report_year == report_year)
    if status:
        query = query.filter(PendingDisclosure.status == status)
    return (
        query.order_by(PendingDisclosure.fetched_at.desc(), PendingDisclosure.id.desc())
        .limit(limit)
        .all()
    )


def get_pending_disclosure(db: Session, pending_id: int) -> PendingDisclosure | None:
    return db.query(PendingDisclosure).filter(PendingDisclosure.id == pending_id).first()


def update_pending_disclosure_payload(
    db: Session,
    *,
    pending_id: int,
    extracted_payload: dict[str, Any],
    review_note: str | None = None,
) -> PendingDisclosure | None:
    row = get_pending_disclosure(db, pending_id)
    if row is None:
        return None
    row.extracted_payload = json.dumps(extracted_payload)
    if review_note is not None:
        row.review_note = review_note
    row.fetched_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def review_pending_disclosure(
    db: Session,
    *,
    pending_id: int,
    status: str,
    review_note: str | None = None,
) -> PendingDisclosure | None:
    row = get_pending_disclosure(db, pending_id)
    if row is None:
        return None
    row.status = status
    row.review_note = review_note
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def record_extraction_run(
    db: Session,
    *,
    run_kind: str,
    file_hash: str | None = None,
    company_report_id: int | None = None,
    model: str | None = None,
    prompt_hash: str | None = None,
    raw_response: str | None = None,
    verdict: str | None = None,
    applied: bool = False,
    notes: str | None = None,
) -> ExtractionRun:
    """Persist one extraction/audit/validation event. Append-only — never UPDATE rows."""
    payload = raw_response
    if payload is not None and len(payload) > 65536:
        payload = payload[:65536] + "...[truncated]"
    row = ExtractionRun(
        run_kind=run_kind,
        file_hash=file_hash,
        company_report_id=company_report_id,
        model=model,
        prompt_hash=prompt_hash,
        raw_response=payload,
        verdict=verdict,
        applied=applied,
        notes=notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def ensure_storage_schema(engine: Engine) -> None:
    """
    Lightweight SQLite-safe migration for additive columns on company_reports.
    We keep this minimal so existing deployments can evolve without alembic.
    """
    # Always create newly declared tables (extraction_runs, pending_disclosures, etc.) on any backend.
    Base.metadata.create_all(
        bind=engine,
        tables=[ExtractionRun.__table__, PendingDisclosure.__table__],
    )

    if engine.dialect.name != "sqlite":
        return

    required_columns: dict[str, str] = {
        "reporting_period_label": "TEXT",
        "reporting_period_type": "TEXT",
        "source_document_type": "TEXT",
        "industry_code": "TEXT",
        "industry_sector": "TEXT",
        "evidence_summary": "TEXT",
        "source_doc_key": "TEXT",
    }
    required_pending_columns: dict[str, str] = {
        "review_note": "TEXT",
        "status": "TEXT",
        "source_type": "TEXT",
    }

    with engine.begin() as conn:
        existing_cols = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(company_reports)")).fetchall()
        }
        for name, col_type in required_columns.items():
            if name in existing_cols:
                continue
            conn.execute(text(f"ALTER TABLE company_reports ADD COLUMN {name} {col_type}"))

        pending_exists = conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='pending_disclosures'"
            )
        ).scalar()
        if pending_exists:
            pending_cols = {
                row[1]
                for row in conn.execute(text("PRAGMA table_info(pending_disclosures)")).fetchall()
            }
            for name, col_type in required_pending_columns.items():
                if name in pending_cols:
                    continue
                conn.execute(text(f"ALTER TABLE pending_disclosures ADD COLUMN {name} {col_type}"))
        conn.execute(
            text(
                """
                UPDATE company_reports
                SET source_doc_key = CASE
                    WHEN file_hash IS NOT NULL AND trim(file_hash) != ''
                        THEN 'file_hash:' || lower(trim(file_hash))
                    WHEN source_url IS NOT NULL AND trim(source_url) != ''
                        THEN 'source_url:' || lower(trim(source_url))
                            || '|type:' || lower(COALESCE(source_document_type, ''))
                    WHEN pdf_filename IS NOT NULL AND trim(pdf_filename) != ''
                        THEN 'pdf_filename:' || lower(trim(pdf_filename))
                            || '|type:' || lower(COALESCE(source_document_type, ''))
                    ELSE 'period:' || lower(COALESCE(source_document_type, ''))
                        || '|label:' || lower(COALESCE(reporting_period_label, CAST(report_year AS TEXT)))
                END
                WHERE source_doc_key IS NULL OR trim(source_doc_key) = ''
                """
            )
        )
        conn.execute(
            text(
                """
                DELETE FROM company_reports
                WHERE id IN (
                    SELECT id FROM (
                        SELECT id,
                               ROW_NUMBER() OVER (
                                   PARTITION BY company_name, report_year, source_doc_key
                                   ORDER BY updated_at DESC, created_at DESC, id DESC
                               ) AS rn
                        FROM company_reports
                        WHERE source_doc_key IS NOT NULL AND trim(source_doc_key) != ''
                    ) dedup
                    WHERE dedup.rn > 1
                )
                """
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_company_reports_industry_code "
                "ON company_reports (industry_code)"
            )
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_company_reports_source_key "
                "ON company_reports (company_name, report_year, source_doc_key)"
            )
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_pending_disclosures_source "
                "ON pending_disclosures (company_name, report_year, source_url)"
            )
        )


def _build_source_doc_key(
    *,
    file_hash: str | None,
    source_url: str | None,
    pdf_filename: str | None,
    source_document_type: str | None,
    reporting_period_label: str | None,
    report_year: int,
) -> str:
    doc_type = (source_document_type or "").strip().lower()
    if file_hash and file_hash.strip():
        return f"file_hash:{file_hash.strip().lower()}"
    if source_url and source_url.strip():
        return f"source_url:{source_url.strip().lower()}|type:{doc_type}"
    if pdf_filename and pdf_filename.strip():
        return f"pdf_filename:{pdf_filename.strip().lower()}|type:{doc_type}"
    label = (reporting_period_label or str(report_year)).strip().lower()
    return f"period:{doc_type}|label:{label}"

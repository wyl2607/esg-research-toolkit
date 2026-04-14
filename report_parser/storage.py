import json
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, func, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from core.database import Base
from core.schemas import CompanyESGData
from report_parser.company_identity import canonical_company_name, collapse_company_records, company_name_variants

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

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String, nullable=False, index=True)
    report_year = Column(Integer, nullable=False)
    reporting_period_label = Column(String, nullable=True)
    reporting_period_type = Column(String, nullable=True)  # annual | quarterly | event
    source_document_type = Column(String, nullable=True)  # annual_report | sustainability_report | filing

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
    """保存企业报告（含来源追溯字段）。company_name + report_year 已存在则更新。"""
    canonical_name = canonical_company_name(data.company_name)
    normalized_data = data.model_copy(update={"company_name": canonical_name})
    period_label, period_type, document_type = _normalized_period_fields(
        normalized_data,
        reporting_period_label=reporting_period_label,
        reporting_period_type=reporting_period_type,
        source_document_type=source_document_type,
    )
    name_variants = [variant.lower() for variant in company_name_variants(canonical_name)]

    record = (
        db.query(CompanyReport)
        .filter(
            func.lower(CompanyReport.company_name).in_(name_variants),
            CompanyReport.report_year == normalized_data.report_year,
        )
        .first()
    )
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
    if evidence_summary is None and not record.evidence_summary:
        record.evidence_summary = json.dumps(normalized_data.evidence_summary)

    record.scope1_co2e_tonnes = normalized_data.scope1_co2e_tonnes
    record.scope2_co2e_tonnes = normalized_data.scope2_co2e_tonnes
    record.scope3_co2e_tonnes = normalized_data.scope3_co2e_tonnes
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


def ensure_storage_schema(engine: Engine) -> None:
    """
    Lightweight SQLite-safe migration for additive columns on company_reports.
    We keep this minimal so existing deployments can evolve without alembic.
    """
    if engine.dialect.name != "sqlite":
        return

    required_columns: dict[str, str] = {
        "reporting_period_label": "TEXT",
        "reporting_period_type": "TEXT",
        "source_document_type": "TEXT",
        "evidence_summary": "TEXT",
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

import json
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from core.database import Base
from core.schemas import CompanyESGData


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
    record = (
        db.query(CompanyReport)
        .filter_by(company_name=data.company_name, report_year=data.report_year)
        .first()
    )
    now = datetime.now(timezone.utc)
    if record is None:
        record = CompanyReport(
            company_name=data.company_name,
            report_year=data.report_year,
            reporting_period_label=reporting_period_label or data.reporting_period_label or str(data.report_year),
            reporting_period_type=reporting_period_type or data.reporting_period_type or "annual",
            source_document_type=source_document_type or data.source_document_type or "sustainability_report",
            pdf_filename=pdf_filename,
            source_url=source_url,
            file_hash=file_hash,
            downloaded_at=downloaded_at or now,
            evidence_summary=json.dumps(evidence_summary if evidence_summary is not None else data.evidence_summary),
        )
        db.add(record)
    else:
        if pdf_filename:
            record.pdf_filename = pdf_filename
        if source_url:
            record.source_url = source_url
        if file_hash:
            record.file_hash = file_hash
        if downloaded_at:
            record.downloaded_at = downloaded_at
        if reporting_period_label:
            record.reporting_period_label = reporting_period_label
        if reporting_period_type:
            record.reporting_period_type = reporting_period_type
        if source_document_type:
            record.source_document_type = source_document_type
        if evidence_summary is not None:
            record.evidence_summary = json.dumps(evidence_summary)

    if not record.reporting_period_label:
        record.reporting_period_label = data.reporting_period_label or str(data.report_year)
    if not record.reporting_period_type:
        record.reporting_period_type = data.reporting_period_type or "annual"
    if not record.source_document_type:
        record.source_document_type = data.source_document_type or "sustainability_report"
    if evidence_summary is None and not record.evidence_summary:
        record.evidence_summary = json.dumps(data.evidence_summary)

    record.scope1_co2e_tonnes = data.scope1_co2e_tonnes
    record.scope2_co2e_tonnes = data.scope2_co2e_tonnes
    record.scope3_co2e_tonnes = data.scope3_co2e_tonnes
    record.energy_consumption_mwh = data.energy_consumption_mwh
    record.renewable_energy_pct = data.renewable_energy_pct
    record.water_usage_m3 = data.water_usage_m3
    record.waste_recycled_pct = data.waste_recycled_pct
    record.total_revenue_eur = data.total_revenue_eur
    record.taxonomy_aligned_revenue_pct = data.taxonomy_aligned_revenue_pct
    record.total_capex_eur = data.total_capex_eur
    record.taxonomy_aligned_capex_pct = data.taxonomy_aligned_capex_pct
    record.total_employees = data.total_employees
    record.female_pct = data.female_pct
    record.primary_activities = json.dumps(data.primary_activities)
    db.commit()
    db.refresh(record)
    return record


def get_report(db: Session, company_name: str, report_year: int) -> CompanyReport | None:
    return (
        db.query(CompanyReport)
        .filter_by(company_name=company_name, report_year=report_year)
        .first()
    )


def list_reports(db: Session, skip: int = 0, limit: int = 50) -> list[CompanyReport]:
    return db.query(CompanyReport).offset(skip).limit(limit).all()


def list_reports_for_company(
    db: Session,
    company_name: str,
    *,
    include_deleted: bool = False,
) -> list[CompanyReport]:
    query = db.query(CompanyReport).filter(CompanyReport.company_name == company_name)
    if not include_deleted:
        query = query.filter(CompanyReport.deletion_requested.is_(False))
    return query.order_by(CompanyReport.report_year.asc()).all()


def request_deletion(db: Session, company_name: str, report_year: int) -> CompanyReport | None:
    """标记来源删除请求，同时删除本地 PDF 副本（如存在）。"""
    from pathlib import Path

    record = get_report(db, company_name, report_year)
    if not record:
        return None

    # 删除本地 PDF 文件副本
    if record.pdf_filename:
        pdf_path = Path("data/reports") / record.pdf_filename
        if pdf_path.exists():
            pdf_path.unlink()

    record.deletion_requested = True
    record.deletion_requested_at = datetime.now(timezone.utc)
    record.pdf_filename = None  # 清除文件引用
    db.commit()
    db.refresh(record)
    return record


def hard_delete_report(db: Session, company_name: str, report_year: int) -> bool:
    """彻底删除记录（含所有提取数据），用于响应正式删除请求。"""
    from pathlib import Path

    record = get_report(db, company_name, report_year)
    if not record:
        return False

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

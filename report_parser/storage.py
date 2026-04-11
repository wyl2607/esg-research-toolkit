import json
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Session

from core.database import Base
from core.schemas import CompanyESGData


class CompanyReport(Base):
    __tablename__ = "company_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String, nullable=False, index=True)
    report_year = Column(Integer, nullable=False)
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
    pdf_filename = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def save_report(db: Session, data: CompanyESGData, pdf_filename: str | None = None) -> CompanyReport:
    """保存企业报告。如果 company_name + report_year 已存在则更新。"""
    record = (
        db.query(CompanyReport)
        .filter_by(company_name=data.company_name, report_year=data.report_year)
        .first()
    )
    if record is None:
        record = CompanyReport(
            company_name=data.company_name,
            report_year=data.report_year,
            pdf_filename=pdf_filename,
        )
        db.add(record)

    record.pdf_filename = pdf_filename or record.pdf_filename
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

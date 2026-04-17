from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from benchmark.compute import BENCHMARK_METRICS
from core.database import get_db
from core.schemas import CompanyByIndustryResponse
from report_parser.storage import CompanyReport

router = APIRouter(tags=["report_parser_industry"])


@router.get("/companies/by-industry/{industry_code}", response_model=CompanyByIndustryResponse)
def list_companies_by_industry(
    industry_code: str,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    rows = (
        db.query(CompanyReport)
        .filter(CompanyReport.industry_code == industry_code)
        .order_by(CompanyReport.company_name.asc(), CompanyReport.report_year.desc())
        .all()
    )

    latest_per_company: dict[str, CompanyReport] = {}
    for row in rows:
        existing = latest_per_company.get(row.company_name)
        if existing is None or (row.report_year or 0) > (existing.report_year or 0):
            latest_per_company[row.company_name] = row

    companies: list[dict[str, object]] = []
    for company_name, row in sorted(latest_per_company.items()):
        metrics: dict[str, float | None] = {}
        for metric in BENCHMARK_METRICS:
            value = getattr(row, metric, None)
            metrics[metric] = float(value) if value is not None else None
        companies.append(
            {
                "company_name": company_name,
                "report_year": row.report_year,
                "industry_code": row.industry_code,
                "industry_sector": row.industry_sector,
                "metrics": metrics,
            }
        )

    return {
        "industry_code": industry_code,
        "company_count": len(companies),
        "companies": companies,
    }

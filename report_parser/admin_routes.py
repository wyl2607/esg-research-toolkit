from __future__ import annotations

import csv
import io
import os
import secrets

import openpyxl
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from core.schemas import DeletionStatusResponse
from report_parser.storage import hard_delete_report, list_reports_grouped, request_deletion

router = APIRouter(tags=["report_parser_admin"])

# Environments where admin operations may run WITHOUT a configured token.
# Every other environment (production, staging, or any unknown value) is
# fail-closed: a token is mandatory.
_LOCAL_ENVS = {"development", "dev", "local", "test", "testing"}


def require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    configured_token = os.getenv("ADMIN_API_TOKEN", settings.admin_api_token).strip()
    if configured_token:
        # Constant-time comparison to avoid leaking the token via timing.
        if not secrets.compare_digest(x_admin_token or "", configured_token):
            raise HTTPException(403, "Admin token required")
        return

    # No token configured: only permitted on local/dev/test environments.
    app_env = os.getenv("APP_ENV", settings.app_env).strip().lower()
    if app_env not in _LOCAL_ENVS:
        raise HTTPException(503, "Admin operations require ADMIN_API_TOKEN to be configured")


def validate_admin_config() -> None:
    """Fail fast at startup if a non-local deployment has no admin token.

    Without this, a misconfigured production/staging boot would silently expose
    admin operations (deletion, export) with no authentication.
    """
    configured_token = os.getenv("ADMIN_API_TOKEN", settings.admin_api_token).strip()
    app_env = os.getenv("APP_ENV", settings.app_env).strip().lower()
    if not configured_token and app_env not in _LOCAL_ENVS:
        raise RuntimeError(
            f"ADMIN_API_TOKEN must be set when APP_ENV={app_env!r} (non-local). "
            "Refusing to start with unauthenticated admin endpoints."
        )


@router.post(
    "/companies/{company_name}/{report_year:int}/request-deletion",
    response_model=DeletionStatusResponse,
)
def request_source_deletion(
    company_name: str,
    report_year: int,
    _: None = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> dict[str, str | int | bool]:
    record = request_deletion(db, company_name, report_year)
    if not record:
        raise HTTPException(404, "Report not found")
    return {
        "status": "deletion_requested",
        "company_name": company_name,
        "report_year": report_year,
        "pdf_deleted": True,
        "message": (
            "PDF copy has been deleted. Extracted metrics will be purged within 30 days. "
            "Contact admin@esg-toolkit to expedite full removal."
        ),
    }


@router.delete("/companies/{company_name}/{report_year:int}", response_model=DeletionStatusResponse)
def delete_company_report(
    company_name: str,
    report_year: int,
    hard: bool = Query(default=False, description="彻底删除所有数据（管理员操作）"),
    _: None = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> dict[str, str | int]:
    if hard:
        ok = hard_delete_report(db, company_name, report_year)
    else:
        record = request_deletion(db, company_name, report_year)
        ok = record is not None
    if not ok:
        raise HTTPException(404, "Report not found")
    return {"status": "deleted", "company_name": company_name, "report_year": report_year}


@router.get("/companies/export/csv")
def export_companies_csv(db: Session = Depends(get_db)) -> StreamingResponse:
    records = list_reports_grouped(db)
    fieldnames = [
        "company_name",
        "report_year",
        "scope1_co2e_tonnes",
        "scope2_co2e_tonnes",
        "scope3_co2e_tonnes",
        "energy_consumption_mwh",
        "renewable_energy_pct",
        "water_usage_m3",
        "waste_recycled_pct",
        "total_employees",
        "female_pct",
    ]

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for record in records:
        writer.writerow({field: getattr(record, field, None) for field in fieldnames})

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="esg_companies.csv"'},
    )


@router.get("/companies/export/xlsx")
def export_companies_xlsx(db: Session = Depends(get_db)) -> StreamingResponse:
    records = list_reports_grouped(db)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "ESG Data"
    ws.append(
        [
            "Company",
            "Year",
            "Scope1 (tCO2e)",
            "Scope2 (tCO2e)",
            "Scope3 (tCO2e)",
            "Energy (MWh)",
            "Renewable %",
            "Water (m³)",
            "Waste Recycled %",
            "Employees",
            "Female %",
        ]
    )

    for record in records:
        ws.append(
            [
                record.company_name,
                record.report_year,
                record.scope1_co2e_tonnes,
                record.scope2_co2e_tonnes,
                record.scope3_co2e_tonnes,
                record.energy_consumption_mwh,
                record.renewable_energy_pct,
                record.water_usage_m3,
                record.waste_recycled_pct,
                record.total_employees,
                record.female_pct,
            ]
        )

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="esg_companies.xlsx"'},
    )

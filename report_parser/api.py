import csv
import hashlib
import importlib.util
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import openpyxl
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.database import get_db
from core.schemas import BatchStatusResponse, CompanyESGData
from report_parser.analyzer import AIExtractionError, analyze_esg_data
from report_parser.batch_jobs import batch_manager
from report_parser.extractor import extract_text_from_pdf
from report_parser.storage import (
    get_report,
    hard_delete_report,
    list_reports,
    list_reports_for_company,
    request_deletion,
    save_report,
)

router = APIRouter(prefix="/report", tags=["report_parser"])
_MULTIPART_AVAILABLE = any(
    importlib.util.find_spec(module_name) is not None
    for module_name in ("python_multipart", "multipart")
)


if _MULTIPART_AVAILABLE:

    @router.post("/upload", response_model=CompanyESGData)
    async def upload_report(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
    ):
        """
        上传企业 PDF 报告，提取 ESG 数据。
        1. 保存 PDF 到 data/reports/{filename}
        2. 提取文本
        3. OpenAI 分析
        4. 存储到 DB
        5. 返回 CompanyESGData
        """
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(400, "Only PDF files are supported")

        content = await file.read()

        # ── 合规：计算文件哈希用于溯源，PDF 不对外公开访问 ──────────────────
        file_hash = hashlib.sha256(content).hexdigest()
        upload_dir = Path("data/reports")
        upload_dir.mkdir(parents=True, exist_ok=True)
        # 用 hash 前缀命名，避免文件名泄露原始信息
        safe_name = f"{file_hash[:16]}_{Path(file.filename).name}"
        pdf_path = upload_dir / safe_name
        with pdf_path.open("wb") as handle:
            handle.write(content)

        text = extract_text_from_pdf(pdf_path)
        if not text:
            raise HTTPException(
                422,
                "无法从该 PDF 提取文本。请确认文件不是纯图片扫描件，或尝试上传文字版 PDF。",
            )

        try:
            esg_data = analyze_esg_data(text, filename=file.filename or "")
        except AIExtractionError as exc:
            raise HTTPException(422, str(exc.reason)) from exc

        save_report(
            db,
            esg_data,
            pdf_filename=safe_name,
            file_hash=file_hash,
            downloaded_at=datetime.now(timezone.utc),
            reporting_period_label=str(esg_data.report_year),
            reporting_period_type="annual",
            source_document_type="sustainability_report",
            evidence_summary=[
                {"metric": "scope1_co2e_tonnes", "source_type": "pdf", "file_hash": file_hash},
                {"metric": "scope2_co2e_tonnes", "source_type": "pdf", "file_hash": file_hash},
                {"metric": "renewable_energy_pct", "source_type": "pdf", "file_hash": file_hash},
            ],
        )
        return esg_data

    @router.post("/upload/batch", response_model=BatchStatusResponse)
    async def upload_reports_batch(files: list[UploadFile] = File(...)):
        """
        批量上传 PDF，并异步分析。
        返回 batch_id，前端通过 /report/jobs/{batch_id} 轮询进度。
        """
        if not files:
            raise HTTPException(400, "No files uploaded")
        if len(files) > 20:
            raise HTTPException(400, "At most 20 files per batch")

        upload_dir = Path("data/reports")
        upload_dir.mkdir(parents=True, exist_ok=True)

        saved_files: list[tuple[Path, str]] = []
        for file in files:
            if not file.filename or not file.filename.lower().endswith(".pdf"):
                raise HTTPException(400, f"Only PDF files are supported: {file.filename or '<unknown>'}")

            pdf_path = upload_dir / Path(file.filename).name
            with pdf_path.open("wb") as handle:
                content = await file.read()
                handle.write(content)
            saved_files.append((pdf_path, file.filename))

        return batch_manager.submit(saved_files)

    @router.get("/jobs/{batch_id}", response_model=BatchStatusResponse)
    def get_batch_status(batch_id: str):
        try:
            return batch_manager.get_batch_status(batch_id)
        except KeyError as exc:
            raise HTTPException(404, f"Batch not found: {batch_id}") from exc

else:

    @router.post("/upload", response_model=CompanyESGData)
    async def upload_report(db: Session = Depends(get_db)):
        raise HTTPException(500, 'File uploads require the "python-multipart" package')


def _record_to_company_data(record) -> CompanyESGData:
    evidence_summary = json.loads(record.evidence_summary) if record.evidence_summary else []
    return CompanyESGData(
        company_name=record.company_name,
        report_year=record.report_year,
        reporting_period_label=record.reporting_period_label,
        reporting_period_type=record.reporting_period_type,
        source_document_type=record.source_document_type,
        scope1_co2e_tonnes=record.scope1_co2e_tonnes,
        scope2_co2e_tonnes=record.scope2_co2e_tonnes,
        scope3_co2e_tonnes=record.scope3_co2e_tonnes,
        energy_consumption_mwh=record.energy_consumption_mwh,
        renewable_energy_pct=record.renewable_energy_pct,
        water_usage_m3=record.water_usage_m3,
        waste_recycled_pct=record.waste_recycled_pct,
        total_revenue_eur=record.total_revenue_eur,
        taxonomy_aligned_revenue_pct=record.taxonomy_aligned_revenue_pct,
        total_capex_eur=record.total_capex_eur,
        taxonomy_aligned_capex_pct=record.taxonomy_aligned_capex_pct,
        total_employees=record.total_employees,
        female_pct=record.female_pct,
        primary_activities=json.loads(record.primary_activities) if record.primary_activities else [],
        evidence_summary=evidence_summary if isinstance(evidence_summary, list) else [],
    )


@router.get("/companies/{company_name}/{report_year:int}", response_model=CompanyESGData)
def get_company_report(
    company_name: str,
    report_year: int,
    db: Session = Depends(get_db),
):
    record = get_report(db, company_name, report_year)
    if not record:
        raise HTTPException(404, "Report not found")
    return _record_to_company_data(record)


@router.get("/companies/{company_name}/history")
def get_company_history(
    company_name: str,
    db: Session = Depends(get_db),
):
    records = list_reports_for_company(db, company_name)
    if not records:
        raise HTTPException(404, f"No reports found for {company_name}")

    trend = []
    periods = []
    for record in records:
        periods.append(
            {
                "report_year": record.report_year,
                "reporting_period_label": record.reporting_period_label or str(record.report_year),
                "reporting_period_type": record.reporting_period_type or "annual",
                "source_document_type": record.source_document_type,
                "source_url": record.source_url,
                "downloaded_at": record.downloaded_at.isoformat() if record.downloaded_at else None,
            }
        )
        trend.append(
            {
                "year": record.report_year,
                "scope1": record.scope1_co2e_tonnes,
                "scope2": record.scope2_co2e_tonnes,
                "scope3": record.scope3_co2e_tonnes,
                "renewable_pct": record.renewable_energy_pct,
                "taxonomy_aligned_revenue_pct": record.taxonomy_aligned_revenue_pct,
                "taxonomy_aligned_capex_pct": record.taxonomy_aligned_capex_pct,
                "female_pct": record.female_pct,
            }
        )

    return {
        "company_name": company_name,
        "periods": periods,
        "trend": trend,
    }


@router.get("/companies/{company_name}/profile")
def get_company_profile(
    company_name: str,
    db: Session = Depends(get_db),
):
    from esg_frameworks.storage import list_framework_results

    records = list_reports_for_company(db, company_name)
    if not records:
        raise HTTPException(404, f"No reports found for {company_name}")

    latest = records[-1]
    history = get_company_history(company_name=company_name, db=db)
    latest_data = _record_to_company_data(latest)

    framework_rows = list_framework_results(
        db,
        company_name=company_name,
        report_year=latest.report_year,
    )
    framework_results = []
    for row in framework_rows:
        result = json.loads(row.result_payload)
        result["analysis_result_id"] = row.id
        result["stored_at"] = row.created_at.isoformat() if row.created_at else None
        framework_results.append(result)

    return {
        "company_name": company_name,
        "years_available": [record.report_year for record in records],
        "latest_year": latest.report_year,
        "latest_period": {
            "report_year": latest.report_year,
            "reporting_period_label": latest.reporting_period_label or str(latest.report_year),
            "reporting_period_type": latest.reporting_period_type or "annual",
            "source_document_type": latest.source_document_type,
        },
        "latest_metrics": latest_data.model_dump(),
        "trend": history["trend"],
        "periods": history["periods"],
        "framework_results": framework_results,
        "evidence_summary": latest_data.evidence_summary,
    }


@router.get("/companies")
def list_company_reports(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    records = list_reports(db, skip, limit)
    return [
        {
            "company_name": record.company_name,
            "report_year": record.report_year,
            "pdf_filename": record.pdf_filename,
            "source_url": record.source_url,
            "file_hash": record.file_hash,
            "downloaded_at": (
                record.downloaded_at.isoformat() if record.downloaded_at else None
            ),
            "reporting_period_label": record.reporting_period_label or str(record.report_year),
            "reporting_period_type": record.reporting_period_type or "annual",
            "source_document_type": record.source_document_type,
            "created_at": (
                record.created_at.isoformat() if record.created_at else None
            ),
            "scope1_co2e_tonnes": record.scope1_co2e_tonnes,
            "scope2_co2e_tonnes": record.scope2_co2e_tonnes,
            "scope3_co2e_tonnes": record.scope3_co2e_tonnes,
            "energy_consumption_mwh": record.energy_consumption_mwh,
            "renewable_energy_pct": record.renewable_energy_pct,
            "water_usage_m3": record.water_usage_m3,
            "waste_recycled_pct": record.waste_recycled_pct,
            "total_revenue_eur": record.total_revenue_eur,
            "taxonomy_aligned_revenue_pct": record.taxonomy_aligned_revenue_pct,
            "total_capex_eur": record.total_capex_eur,
            "taxonomy_aligned_capex_pct": record.taxonomy_aligned_capex_pct,
            "total_employees": record.total_employees,
            "female_pct": record.female_pct,
            "primary_activities": json.loads(record.primary_activities) if record.primary_activities else [],
            "evidence_summary": json.loads(record.evidence_summary) if record.evidence_summary else [],
        }
        for record in records
    ]


@router.post("/companies/{company_name}/{report_year:int}/request-deletion")
def request_source_deletion(
    company_name: str,
    report_year: int,
    db: Session = Depends(get_db),
):
    """
    来源删除机制（Requirement 4）：
    接收权利人请求，立即删除本地 PDF 副本，标记记录为 deletion_requested。
    提取的指标数据保留 30 天（可配置）后由管理员彻底删除。
    """
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


@router.delete("/companies/{company_name}/{report_year:int}")
def delete_company_report(
    company_name: str,
    report_year: int,
    hard: bool = Query(default=False, description="彻底删除所有数据（管理员操作）"),
    db: Session = Depends(get_db),
):
    """删除公司报告。hard=true 时彻底删除，否则仅软删除（标记 deletion_requested）。"""
    if hard:
        ok = hard_delete_report(db, company_name, report_year)
    else:
        record = request_deletion(db, company_name, report_year)
        ok = record is not None
    if not ok:
        raise HTTPException(404, "Report not found")
    return {"status": "deleted", "company_name": company_name, "report_year": report_year}


@router.get("/companies/export/csv")
def export_companies_csv(db: Session = Depends(get_db)):
    records = list_reports(db, skip=0, limit=10000)
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
def export_companies_xlsx(db: Session = Depends(get_db)):
    records = list_reports(db, skip=0, limit=10000)

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

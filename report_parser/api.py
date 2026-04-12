import importlib.util
import json
import csv
import io
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
import openpyxl
from sqlalchemy.orm import Session

from core.database import get_db
from core.schemas import BatchStatusResponse, CompanyESGData
from report_parser.analyzer import AIExtractionError, analyze_esg_data
from report_parser.batch_jobs import batch_manager
from report_parser.extractor import extract_text_from_pdf
from report_parser.storage import get_report, list_reports, save_report

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

        upload_dir = Path("data/reports")
        upload_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = upload_dir / Path(file.filename).name
        with pdf_path.open("wb") as handle:
            content = await file.read()
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

        save_report(db, esg_data, pdf_filename=file.filename)
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


@router.get("/companies/{company_name}/{report_year:int}", response_model=CompanyESGData)
def get_company_report(
    company_name: str,
    report_year: int,
    db: Session = Depends(get_db),
):
    record = get_report(db, company_name, report_year)
    if not record:
        raise HTTPException(404, "Report not found")

    return CompanyESGData(
        company_name=record.company_name,
        report_year=record.report_year,
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
    )


@router.get("/companies")
def list_company_reports(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    records = list_reports(db, skip, limit)
    return [
        {
            "company_name": record.company_name,
            "report_year": record.report_year,
            "pdf_filename": record.pdf_filename,
            "created_at": record.created_at.isoformat(),
        }
        for record in records
    ]


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

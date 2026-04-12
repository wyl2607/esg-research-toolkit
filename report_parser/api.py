import importlib.util
import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from core.database import get_db
from core.schemas import CompanyESGData
from report_parser.analyzer import analyze_esg_data
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
            raise HTTPException(500, "Failed to extract text from PDF")

        esg_data = analyze_esg_data(text)
        save_report(db, esg_data, pdf_filename=file.filename)
        return esg_data

else:

    @router.post("/upload", response_model=CompanyESGData)
    async def upload_report(db: Session = Depends(get_db)):
        raise HTTPException(500, 'File uploads require the "python-multipart" package')


@router.get("/companies/{company_name}/{report_year}", response_model=CompanyESGData)
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

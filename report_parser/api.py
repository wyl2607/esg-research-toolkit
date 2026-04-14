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
from core.schemas import (
    BatchStatusResponse,
    CompanyESGData,
    ManualReportInput,
    MergePreviewRequest,
    MergePreviewResponse,
)
from report_parser.merge_engine import build_merge_preview
from report_parser.analyzer import AIExtractionError, analyze_esg_data
from report_parser.batch_jobs import batch_manager
from report_parser.extractor import extract_text_from_pdf
from report_parser.storage import (
    get_report,
    hard_delete_report,
    list_reports,
    list_reports_grouped,
    list_reports_for_company,
    request_deletion,
    save_report,
)

router = APIRouter(prefix="/report", tags=["report_parser"])
_MULTIPART_AVAILABLE = any(
    importlib.util.find_spec(module_name) is not None
    for module_name in ("python_multipart", "multipart")
)


def _parse_evidence_summary(raw_value: str | None) -> list[dict[str, str | int | float | None]]:
    if not raw_value:
        return []
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _normalize_evidence_anchor(
    entry: dict,
    *,
    fallback_source_url: str | None = None,
) -> dict[str, str | int | float | None]:
    source = entry.get("source")
    if not isinstance(source, str) or not source:
        for key in ("source_url", "source_type", "file_hash"):
            value = entry.get(key)
            if isinstance(value, str) and value:
                source = value
                break
    if (not isinstance(source, str) or not source) and fallback_source_url:
        source = fallback_source_url

    page = entry.get("page")
    if page is None:
        page = entry.get("page_number")

    snippet = entry.get("snippet")
    if not isinstance(snippet, str) or not snippet:
        for key in ("extraction_note", "note"):
            value = entry.get(key)
            if isinstance(value, str) and value:
                snippet = value
                break

    normalized: dict[str, str | int | float | None] = {
        "metric": entry.get("metric") if isinstance(entry.get("metric"), str) else None,
        "source": source if isinstance(source, str) else None,
        "page": page if isinstance(page, (str, int, float)) else None,
        "snippet": snippet if isinstance(snippet, str) else None,
        "source_type": entry.get("source_type") if isinstance(entry.get("source_type"), str) else None,
        "source_url": entry.get("source_url") if isinstance(entry.get("source_url"), str) else None,
        "file_hash": entry.get("file_hash") if isinstance(entry.get("file_hash"), str) else None,
    }
    return normalized


def _evidence_anchors_for_record(record) -> list[dict[str, str | int | float | None]]:
    raw_items = _parse_evidence_summary(record.evidence_summary)
    anchors: list[dict[str, str | int | float | None]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        anchors.append(_normalize_evidence_anchor(item, fallback_source_url=record.source_url))
    return anchors


def _period_metadata(record) -> dict[str, str | int | None]:
    """
    Task 27B contract:
    - `report_year` remains the legacy compatibility anchor
    - normalized period fields are exposed in a stable nested object
    """
    report_year = record.report_year
    label = record.reporting_period_label or str(report_year)
    period_type = record.reporting_period_type or "annual"
    source_document_type = record.source_document_type or "sustainability_report"
    return {
        "period_id": f"{record.company_name}:{report_year}:{period_type}:{label}",
        "label": label,
        "type": period_type,
        "source_document_type": source_document_type,
        "legacy_report_year": report_year,
    }


def _manual_evidence_summary(
    data: CompanyESGData,
    *,
    source_url: str | None = None,
) -> list[dict[str, str | int | float | None]]:
    metric_keys = [
        "scope1_co2e_tonnes",
        "scope2_co2e_tonnes",
        "scope3_co2e_tonnes",
        "energy_consumption_mwh",
        "renewable_energy_pct",
        "water_usage_m3",
        "waste_recycled_pct",
        "taxonomy_aligned_revenue_pct",
        "taxonomy_aligned_capex_pct",
        "total_employees",
        "female_pct",
    ]
    source = source_url or f"manual://{data.company_name}/{data.report_year}"
    evidence: list[dict[str, str | int | float | None]] = []
    for metric in metric_keys:
        if getattr(data, metric, None) is None:
            continue
        evidence.append(
            {
                "metric": metric,
                "source": source,
                "snippet": "Saved via manual case builder",
                "source_type": "manual_entry",
                "source_url": source_url,
            }
        )

    if data.primary_activities:
        evidence.append(
            {
                "metric": "primary_activities",
                "source": source,
                "snippet": ", ".join(data.primary_activities),
                "source_type": "manual_entry",
                "source_url": source_url,
            }
        )

    return evidence


def _framework_metadata_item(row) -> dict[str, str | int | None]:
    return {
        "analysis_result_id": row.id,
        "framework_id": row.framework_id,
        "framework": row.framework_name,
        "framework_version": row.framework_version,
        "report_year": row.report_year,
        "stored_at": row.created_at.isoformat() if row.created_at else None,
    }


def _numeric_values(records, field: str) -> list[float]:
    values: list[float] = []
    for record in records:
        value = getattr(record, field, None)
        if value is None:
            continue
        values.append(float(value))
    return values


def _coverage_rates(records, fields: list[str]) -> dict[str, float]:
    if not records:
        return {field: 0.0 for field in fields}

    total = len(records)
    coverage: dict[str, float] = {}
    for field in fields:
        present = sum(1 for record in records if getattr(record, field, None) is not None)
        coverage[field] = round((present / total) * 100, 1)
    return coverage


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


@router.post("/manual", response_model=CompanyESGData)
def save_manual_report(
    payload: ManualReportInput,
    db: Session = Depends(get_db),
):
    report = CompanyESGData(**payload.model_dump(exclude={"source_url"}))
    evidence_summary = payload.evidence_summary or _manual_evidence_summary(
        report,
        source_url=payload.source_url,
    )
    record = save_report(
        db,
        report,
        source_url=payload.source_url,
        downloaded_at=datetime.now(timezone.utc),
        reporting_period_label=payload.reporting_period_label or str(payload.report_year),
        reporting_period_type=payload.reporting_period_type or "annual",
        source_document_type=payload.source_document_type or "manual_case",
        evidence_summary=evidence_summary,
    )
    return _record_to_company_data(record)


@router.post("/merge/preview", response_model=MergePreviewResponse)
def preview_merge(payload: MergePreviewRequest):
    try:
        return build_merge_preview(payload.documents)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


def _record_to_company_data(record) -> CompanyESGData:
    evidence_summary = _evidence_anchors_for_record(record)
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
        evidence_summary=evidence_summary,
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
    from esg_frameworks.storage import list_framework_results

    records = list_reports_for_company(db, company_name)
    if not records:
        raise HTTPException(404, f"No reports found for {company_name}")
    resolved_name = records[0].company_name

    trend = []
    periods = []
    framework_metadata = []
    for record in records:
        anchors = _evidence_anchors_for_record(record)
        period = _period_metadata(record)
        framework_rows = list_framework_results(
            db,
            company_name=resolved_name,
            report_year=record.report_year,
        )
        period_framework_metadata = [_framework_metadata_item(row) for row in framework_rows]
        framework_metadata.extend(period_framework_metadata)
        periods.append(
            {
                "report_year": record.report_year,
                "reporting_period_label": period["label"],
                "reporting_period_type": period["type"],
                "source_document_type": period["source_document_type"],
                "period": period,
                "source_url": record.source_url,
                "downloaded_at": record.downloaded_at.isoformat() if record.downloaded_at else None,
                "evidence_anchors": anchors,
                "framework_metadata": period_framework_metadata,
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
        "company_name": resolved_name,
        "periods": periods,
        "trend": trend,
        "framework_metadata": framework_metadata,
    }


@router.get("/companies/{company_name}/profile")
def get_company_profile(
    company_name: str,
    db: Session = Depends(get_db),
):
    from esg_frameworks.storage import list_framework_results
    from esg_frameworks.api import _SCORERS

    records = list_reports_for_company(db, company_name)
    if not records:
        raise HTTPException(404, f"No reports found for {company_name}")
    resolved_name = records[0].company_name

    latest = records[-1]
    history = get_company_history(company_name=resolved_name, db=db)
    latest_data = _record_to_company_data(latest)
    latest_evidence_anchors = _evidence_anchors_for_record(latest)
    latest_period = _period_metadata(latest)

    framework_rows = list_framework_results(
        db,
        company_name=resolved_name,
        report_year=latest.report_year,
    )
    framework_results = []
    for row in framework_rows:
        result = json.loads(row.result_payload)
        result["framework_version"] = result.get("framework_version") or row.framework_version
        result["framework_id"] = result.get("framework_id") or row.framework_id
        result["framework"] = result.get("framework") or row.framework_name
        result["analysis_result_id"] = row.id
        result["stored_at"] = row.created_at.isoformat() if row.created_at else None
        framework_results.append(result)
    latest_framework_metadata = [_framework_metadata_item(row) for row in framework_rows]
    framework_scores = [scorer(latest_data).model_dump() for scorer in _SCORERS.values()]

    return {
        "company_name": resolved_name,
        "years_available": [record.report_year for record in records],
        "latest_year": latest.report_year,
        "latest_period": {
            "report_year": latest.report_year,
            "reporting_period_label": latest_period["label"],
            "reporting_period_type": latest_period["type"],
            "source_document_type": latest_period["source_document_type"],
            "period": latest_period,
            "framework_metadata": latest_framework_metadata,
        },
        "latest_metrics": latest_data.model_dump(),
        "trend": history["trend"],
        "periods": history["periods"],
        "framework_metadata": history["framework_metadata"],
        "framework_scores": framework_scores,
        "framework_results": framework_results,
        "evidence_summary": latest_data.evidence_summary,
        "evidence_anchors": latest_evidence_anchors,
    }


@router.get("/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    records = list_reports_grouped(db)
    if not records:
        return {
            "total_companies": 0,
            "avg_taxonomy_aligned": 0,
            "avg_renewable_pct": 0,
            "yearly_trend": [],
            "top_emitters": [],
            "bottom_emitters": [],
            "coverage_rates": {},
        }

    from collections import defaultdict
    import statistics

    yearly: dict[int, int] = defaultdict(int)
    for record in records:
        yearly[record.report_year] += 1
    yearly_trend = [{"year": year, "count": count} for year, count in sorted(yearly.items())]

    taxonomy_values = _numeric_values(records, "taxonomy_aligned_revenue_pct")
    renewable_values = _numeric_values(records, "renewable_energy_pct")

    emitters = [
        (record.company_name, record.report_year, float(record.scope1_co2e_tonnes))
        for record in records
        if record.scope1_co2e_tonnes is not None
    ]
    emitters_desc = sorted(emitters, key=lambda item: item[2], reverse=True)
    emitters_asc = sorted(emitters, key=lambda item: item[2])

    coverage_fields = [
        "scope1_co2e_tonnes",
        "scope2_co2e_tonnes",
        "scope3_co2e_tonnes",
        "energy_consumption_mwh",
        "renewable_energy_pct",
        "water_usage_m3",
        "waste_recycled_pct",
        "taxonomy_aligned_revenue_pct",
        "female_pct",
    ]

    return {
        "total_companies": len(records),
        "avg_taxonomy_aligned": (
            round(statistics.mean(taxonomy_values), 1) if taxonomy_values else 0
        ),
        "avg_renewable_pct": (
            round(statistics.mean(renewable_values), 1) if renewable_values else 0
        ),
        "yearly_trend": yearly_trend,
        "top_emitters": [
            {"company": company, "year": year, "scope1": scope1}
            for company, year, scope1 in emitters_desc[:5]
        ],
        "bottom_emitters": [
            {"company": company, "year": year, "scope1": scope1}
            for company, year, scope1 in emitters_asc[:5]
        ],
        "coverage_rates": _coverage_rates(records, coverage_fields),
    }


@router.get("/companies")
def list_company_reports(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    records = list_reports_grouped(db)[skip : skip + limit]
    payload = []
    for record in records:
        period = _period_metadata(record)
        payload.append(
            {
                "company_name": record.company_name,
                "report_year": record.report_year,
                "pdf_filename": record.pdf_filename,
                "source_url": record.source_url,
                "file_hash": record.file_hash,
                "downloaded_at": (
                    record.downloaded_at.isoformat() if record.downloaded_at else None
                ),
                "reporting_period_label": period["label"],
                "reporting_period_type": period["type"],
                "source_document_type": period["source_document_type"],
                "period": period,
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
                "evidence_summary": _evidence_anchors_for_record(record),
            }
        )
    return payload


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
def export_companies_xlsx(db: Session = Depends(get_db)):
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

import csv
import hashlib
import importlib.util
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import openpyxl
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from core.database import get_db
from core.evidence import Evidence, infer_extraction_method, normalize_raw_evidence
from core.limiter import limiter
from core.normalization.period import normalize_reporting_period
from core.schemas import (
    AuditTrailRow,
    BatchStatusResponse,
    CompanyESGData,
    CompanyProfileMetric,
    CompanyProfileV1Response,
    ManualReportInput,
    MergePreviewRequest,
    MergePreviewResponse,
    MergeSourceInput,
)
from report_parser.merge_engine import build_merge_preview
from report_parser.merge_engine import build_merged_result
from report_parser.analyzer import AIExtractionError, analyze_esg_data
from report_parser.batch_jobs import batch_manager
from report_parser.company_identity import canonical_company_name
from report_parser.extractor import extract_text_from_pdf
from report_parser.storage import (
    CompanyReport,
    get_report,
    hard_delete_report,
    list_reports_grouped,
    list_reports_for_company,
    list_source_reports_for_company_year,
    request_deletion,
    save_report,
)
from taxonomy_scorer.scorer import get_metric_framework_mappings

router = APIRouter(prefix="/report", tags=["report_parser"])
v1_router = APIRouter(prefix="/api/v1", tags=["report_parser_v1"])
_MULTIPART_AVAILABLE = any(
    importlib.util.find_spec(module_name) is not None
    for module_name in ("python_multipart", "multipart")
)

# ── Upload hardening (P0) ────────────────────────────────────────────────
MAX_PDF_BYTES = 50 * 1024 * 1024          # 50 MB hard cap
MIN_PDF_BYTES = 1024                       # < 1 KB cannot be a real PDF
PDF_MAGIC_BYTES = b"%PDF-"

_PROFILE_METRICS = [
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
    "primary_activities",
]

_PROFILE_METRIC_UNITS = {
    "scope1_co2e_tonnes": "tCO2e",
    "scope2_co2e_tonnes": "tCO2e",
    "scope3_co2e_tonnes": "tCO2e",
    "energy_consumption_mwh": "MWh",
    "renewable_energy_pct": "percent",
    "water_usage_m3": "m3",
    "waste_recycled_pct": "percent",
    "taxonomy_aligned_revenue_pct": "percent",
    "taxonomy_aligned_capex_pct": "percent",
    "total_employees": "count",
    "female_pct": "percent",
    "primary_activities": "activity_ids",
}


def _validate_pdf_bytes(filename: str | None, content: bytes) -> None:
    """Strict PDF validation: extension + magic bytes + size bounds.

    Stops obvious attacks: oversized uploads, fake .pdf extensions,
    EICAR-style content masquerading as a PDF.
    """
    if not filename or not filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")
    if len(content) < MIN_PDF_BYTES:
        raise HTTPException(400, f"PDF too small ({len(content)} bytes); minimum {MIN_PDF_BYTES}")
    if len(content) > MAX_PDF_BYTES:
        raise HTTPException(
            413,
            f"PDF too large ({len(content) // (1024 * 1024)} MB); max {MAX_PDF_BYTES // (1024 * 1024)} MB",
        )
    if not content.startswith(PDF_MAGIC_BYTES):
        raise HTTPException(415, "File does not look like a PDF (missing %PDF- magic bytes)")


def _parse_evidence_summary(raw_value: str | None) -> list[dict[str, Any]]:
    if not raw_value:
        return []
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return []
    return [item for item in parsed if isinstance(item, dict)] if isinstance(parsed, list) else []


def _normalize_evidence_anchor(
    entry: dict,
    *,
    fallback_source_url: str | None = None,
) -> dict[str, Any]:
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

    source_type = entry.get("source_type") if isinstance(entry.get("source_type"), str) else None
    structured_evidence = normalize_raw_evidence(
        entry,
        fallback_source_doc_id=(
            entry.get("file_hash")
            if isinstance(entry.get("file_hash"), str) and entry.get("file_hash")
            else source if isinstance(source, str) and source else fallback_source_url
        ),
        fallback_source_type=source_type,
        fallback_snippet=snippet if isinstance(snippet, str) else None,
    )

    normalized: dict[str, Any] = {
        "metric": entry.get("metric") if isinstance(entry.get("metric"), str) else None,
        "source": source if isinstance(source, str) else None,
        "page": page if isinstance(page, (str, int, float)) else None,
        "snippet": snippet if isinstance(snippet, str) else None,
        "source_type": source_type,
        "source_url": entry.get("source_url") if isinstance(entry.get("source_url"), str) else None,
        "file_hash": entry.get("file_hash") if isinstance(entry.get("file_hash"), str) else None,
    }
    if structured_evidence is not None:
        normalized.update(structured_evidence.model_dump(mode="json"))
    return normalized


def _evidence_anchors_for_record(record) -> list[dict[str, Any]]:
    raw_items = _parse_evidence_summary(record.evidence_summary)
    anchors: list[dict[str, Any]] = []
    for item in raw_items:
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
    normalized_period = normalize_reporting_period(
        fiscal_year=report_year,
        reporting_period_label=label,
        reporting_period_type=period_type,
        source_document_type=source_document_type,
    )
    return {
        "period_id": f"{record.company_name}:{report_year}:{period_type}:{label}",
        "label": label,
        "type": period_type,
        "source_document_type": source_document_type,
        "legacy_report_year": report_year,
        "fiscal_year": normalized_period.fiscal_year,
        "reporting_standard": normalized_period.reporting_standard,
        "period_start": (
            normalized_period.period_start.isoformat()
            if normalized_period.period_start
            else None
        ),
        "period_end": (
            normalized_period.period_end.isoformat()
            if normalized_period.period_end
            else None
        ),
    }


def _manual_evidence_summary(
    data: CompanyESGData,
    *,
    source_url: str | None = None,
) -> list[dict[str, Any]]:
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
    evidence: list[dict[str, Any]] = []
    for metric in metric_keys:
        if getattr(data, metric, None) is None:
            continue
        evidence.append(
            {
                "metric": metric,
                "source": source,
                "source_doc_id": source,
                "page": None,
                "char_range": None,
                "snippet": "Saved via manual case builder",
                "extraction_method": "manual",
                "confidence": 1.0,
                "source_type": "manual_entry",
                "source_url": source_url,
            }
        )

    if data.primary_activities:
        evidence.append(
            {
                "metric": "primary_activities",
                "source": source,
                "source_doc_id": source,
                "page": None,
                "char_range": None,
                "snippet": ", ".join(data.primary_activities),
                "extraction_method": "manual",
                "confidence": 1.0,
                "source_type": "manual_entry",
                "source_url": source_url,
            }
        )

    return evidence


def _upload_evidence_summary(
    data: CompanyESGData,
    *,
    file_hash: str,
) -> list[dict[str, Any]]:
    if data.evidence_summary:
        return data.evidence_summary

    fallback_metrics = [
        "scope1_co2e_tonnes",
        "scope2_co2e_tonnes",
        "scope3_co2e_tonnes",
        "energy_consumption_mwh",
        "renewable_energy_pct",
        "water_usage_m3",
        "waste_recycled_pct",
        "total_revenue_eur",
        "taxonomy_aligned_revenue_pct",
        "total_capex_eur",
        "taxonomy_aligned_capex_pct",
        "total_employees",
        "female_pct",
    ]
    evidence: list[dict[str, Any]] = []
    for metric in fallback_metrics:
        if getattr(data, metric, None) is None:
            continue
        evidence.append(
            {
                "metric": metric,
                "source_doc_id": file_hash,
                "page": None,
                "char_range": None,
                "snippet": "Extracted from uploaded PDF.",
                "extraction_method": "pdf_text",
                "confidence": 0.65,
                "source_type": "pdf",
                "file_hash": file_hash,
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


def _source_doc_id(record) -> str:
    if getattr(record, "file_hash", None):
        return record.file_hash
    if getattr(record, "source_url", None):
        return record.source_url
    record_id = getattr(record, "id", None)
    if record_id is not None:
        return f"db:{record_id}"
    if getattr(record, "source_id", None):
        return record.source_id
    return f"{record.company_name}:{record.report_year}:{record.source_document_type or 'unknown'}"


def _metric_snippet(metric: str, value: str | int | float | list[str] | None) -> str:
    if isinstance(value, list):
        rendered_value = ", ".join(str(item) for item in value)
    else:
        rendered_value = "undisclosed" if value is None else str(value)
    return f"{metric} reported as {rendered_value}"


def _metric_anchor_from_record(
    record,
    metric: str,
    value: str | int | float | list[str] | None,
) -> dict[str, Any]:
    anchors = _evidence_anchors_for_record(record)
    metric_anchor = next(
        (
            anchor
            for anchor in anchors
            if anchor.get("metric") == metric
        ),
        None,
    )
    if metric_anchor is not None:
        return metric_anchor

    fallback_method = infer_extraction_method(
        None,
        fallback_source_type=getattr(record, "source_document_type", None),
        fallback_source_doc_id=_source_doc_id(record),
    )
    evidence = Evidence(
        source_doc_id=_source_doc_id(record),
        page=None,
        char_range=None,
        snippet=_metric_snippet(metric, value),
        extraction_method=fallback_method,
        confidence=1.0 if fallback_method == "manual" else 0.55,
    )
    return {
        "metric": metric,
        "source": getattr(record, "source_url", None) or evidence.source_doc_id,
        "source_type": "manual_entry" if fallback_method == "manual" else "pdf",
        "source_url": getattr(record, "source_url", None),
        "file_hash": getattr(record, "file_hash", None),
        **evidence.model_dump(mode="json"),
    }


def _structured_metric_evidence(
    anchor: dict[str, Any] | None,
    *,
    record,
    metric: str,
    value: str | int | float | list[str] | None,
) -> Evidence | None:
    if value in (None, []):
        return None
    candidate_anchor = anchor or _metric_anchor_from_record(record, metric, value)
    return normalize_raw_evidence(
        candidate_anchor,
        fallback_source_doc_id=_source_doc_id(record),
        fallback_source_type=getattr(record, "source_document_type", None),
        fallback_snippet=_metric_snippet(metric, value),
    )


def _record_to_merge_source_input(
    record,
    *,
    canonical_company_name_value: str | None = None,
) -> MergeSourceInput:
    primary_activities = json.loads(record.primary_activities) if record.primary_activities else []
    return MergeSourceInput(
        source_id=f"db:{record.id}",
        company_name=canonical_company_name_value or record.company_name,
        report_year=record.report_year,
        reporting_period_label=record.reporting_period_label,
        reporting_period_type=record.reporting_period_type,
        source_document_type=record.source_document_type,
        industry_code=record.industry_code,
        industry_sector=record.industry_sector,
        source_url=record.source_url,
        downloaded_at=record.downloaded_at.isoformat() if record.downloaded_at else None,
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
        primary_activities=primary_activities,
        evidence_summary=_evidence_anchors_for_record(record),
    )


def _source_document_payload(record) -> dict[str, str | int | float | list[str] | None]:
    return {
        "source_id": f"db:{record.id}",
        "source_document_type": record.source_document_type,
        "reporting_period_label": record.reporting_period_label,
        "reporting_period_type": record.reporting_period_type,
        "source_url": record.source_url,
        "file_hash": record.file_hash,
        "pdf_filename": record.pdf_filename,
        "downloaded_at": record.downloaded_at.isoformat() if record.downloaded_at else None,
        "evidence_anchors": _evidence_anchors_for_record(record),
    }


_KEY_DISCLOSURE_METRICS = [
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


def _data_quality_summary(data: CompanyESGData) -> dict[str, int | float | str | list[str]]:
    present_metrics = [
        metric
        for metric in _KEY_DISCLOSURE_METRICS
        if getattr(data, metric, None) is not None
    ]
    missing_metrics = [
        metric for metric in _KEY_DISCLOSURE_METRICS if metric not in present_metrics
    ]
    total_count = len(_KEY_DISCLOSURE_METRICS)
    present_count = len(present_metrics)
    completion_percentage = round((present_count / total_count) * 100, 1) if total_count else 0.0

    if completion_percentage >= 80:
        readiness_label = "showcase-ready"
    elif completion_percentage >= 50:
        readiness_label = "usable"
    else:
        readiness_label = "draft"

    return {
        "total_key_metrics_count": total_count,
        "present_metrics_count": present_count,
        "present_metrics": present_metrics,
        "missing_metrics": missing_metrics,
        "completion_percentage": completion_percentage,
        "readiness_label": readiness_label,
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


def _narrative_summary(
    *,
    latest_data: CompanyESGData,
    previous_trend_point: dict | None,
    periods_count: int,
    years_available: list[int],
    framework_count: int,
    data_quality_summary: dict[str, int | float | str | list[str]],
) -> dict[str, object]:
    trend_rules = {
        "scope1_co2e_tonnes": ("scope1", "down"),
        "scope2_co2e_tonnes": ("scope2", "down"),
        "scope3_co2e_tonnes": ("scope3", "down"),
        "renewable_energy_pct": ("renewable_pct", "up"),
        "taxonomy_aligned_revenue_pct": ("taxonomy_aligned_revenue_pct", "up"),
        "taxonomy_aligned_capex_pct": ("taxonomy_aligned_capex_pct", "up"),
        "female_pct": ("female_pct", "up"),
    }
    epsilon = 1e-9
    improved_metrics: list[str] = []
    weakened_metrics: list[str] = []
    stable_metrics: list[str] = []

    for metric_key, (trend_key, preferred_direction) in trend_rules.items():
        current_value = getattr(latest_data, metric_key, None)
        previous_value = previous_trend_point.get(trend_key) if previous_trend_point else None
        if current_value is None or previous_value is None:
            continue
        delta = float(current_value) - float(previous_value)
        if abs(delta) <= epsilon:
            stable_metrics.append(metric_key)
            continue
        if preferred_direction == "up":
            (improved_metrics if delta > 0 else weakened_metrics).append(metric_key)
        else:
            (improved_metrics if delta < 0 else weakened_metrics).append(metric_key)

    return {
        "snapshot": {
            "periods_count": periods_count,
            "years_count": len(years_available),
            "latest_year": latest_data.report_year,
            "framework_count": framework_count,
            "readiness_label": data_quality_summary["readiness_label"],
        },
        "has_previous_period": previous_trend_point is not None,
        "previous_year": previous_trend_point.get("year") if previous_trend_point else None,
        "improved_metrics": improved_metrics,
        "weakened_metrics": weakened_metrics,
        "stable_metrics": stable_metrics,
        "disclosure_strength_metrics": data_quality_summary["present_metrics"],
        "disclosure_gap_metrics": data_quality_summary["missing_metrics"],
    }


def _identity_provenance_summary(
    *,
    requested_company_name: str,
    canonical_company_name_value: str,
    latest_source_document_type: str | None,
    observed_company_names: list[str] | None = None,
    source_priority_preview: str | None = None,
    merge_priority_preview: str | None = None,
) -> dict[str, str | bool | list[str] | None]:
    normalized_canonical = canonical_company_name(canonical_company_name_value)
    normalized_canonical_key = normalized_canonical.lower()
    alias_candidates: set[str] = set()

    for candidate in observed_company_names or []:
        if not isinstance(candidate, str):
            continue
        trimmed = candidate.strip()
        if not trimmed:
            continue
        if trimmed.lower() == normalized_canonical_key:
            continue
        if canonical_company_name(trimmed) == normalized_canonical:
            alias_candidates.add(trimmed)

    trimmed_requested = requested_company_name.strip()
    if trimmed_requested and canonical_company_name(trimmed_requested) == normalized_canonical:
        if trimmed_requested.lower() != normalized_canonical_key:
            alias_candidates.add(trimmed_requested)

    aliases = sorted(alias_candidates, key=lambda item: item.lower())
    return {
        "canonical_company_name": normalized_canonical,
        "requested_company_name": requested_company_name,
        "has_alias_consolidation": len(aliases) > 0,
        "consolidated_aliases": aliases,
        "latest_source_document_type": latest_source_document_type,
        "source_priority_preview": source_priority_preview,
        "merge_priority_preview": merge_priority_preview,
    }


def _source_metadata_gap_preview(records) -> str | None:
    if not records:
        return None

    total = len(records)
    missing_source_document_type = sum(1 for record in records if not record.source_document_type)
    missing_period_label = sum(1 for record in records if not record.reporting_period_label)
    missing_period_type = sum(1 for record in records if not record.reporting_period_type)

    gaps: list[str] = []
    if missing_source_document_type:
        gaps.append(f"source_document_type {missing_source_document_type}/{total}")
    if missing_period_label:
        gaps.append(f"reporting_period_label {missing_period_label}/{total}")
    if missing_period_type:
        gaps.append(f"reporting_period_type {missing_period_type}/{total}")

    if not gaps:
        return None

    return (
        "Legacy metadata gaps detected ("
        + ", ".join(gaps)
        + "); defaults are shown until upstream metadata is backfilled."
    )


if _MULTIPART_AVAILABLE:

    @router.post("/upload", response_model=CompanyESGData)
    @limiter.limit("5/minute")
    async def upload_report(
        request: Request,
        file: UploadFile = File(...),
        industry_code: str | None = Form(default=None),
        industry_sector: str | None = Form(default=None),
        db: Session = Depends(get_db),
    ) -> CompanyESGData:
        """
        上传企业 PDF 报告，提取 ESG 数据。
        1. 保存 PDF 到 data/reports/{filename}
        2. 提取文本
        3. OpenAI 分析
        4. 存储到 DB
        5. 返回 CompanyESGData
        """
        content = await file.read()
        _validate_pdf_bytes(file.filename, content)

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
        if industry_code is not None or industry_sector is not None:
            esg_data = esg_data.model_copy(
                update={
                    "industry_code": industry_code,
                    "industry_sector": industry_sector,
                }
            )

        save_report(
            db,
            esg_data,
            pdf_filename=safe_name,
            file_hash=file_hash,
            downloaded_at=datetime.now(timezone.utc),
            reporting_period_label=str(esg_data.report_year),
            reporting_period_type="annual",
            source_document_type="sustainability_report",
            evidence_summary=_upload_evidence_summary(esg_data, file_hash=file_hash),
        )
        return esg_data

    @router.post("/upload/batch", response_model=BatchStatusResponse)
    @limiter.limit("5/minute")
    async def upload_reports_batch(request: Request, files: list[UploadFile] = File(...)) -> BatchStatusResponse:
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
            content = await file.read()
            _validate_pdf_bytes(file.filename, content)
            assert file.filename is not None  # guarded by _validate_pdf_bytes

            pdf_path = upload_dir / Path(file.filename).name
            with pdf_path.open("wb") as handle:
                handle.write(content)
            saved_files.append((pdf_path, file.filename))

        return batch_manager.submit(saved_files)

    @router.get("/jobs/{batch_id}", response_model=BatchStatusResponse)
    def get_batch_status(batch_id: str) -> BatchStatusResponse:
        try:
            return batch_manager.get_batch_status(batch_id)
        except KeyError as exc:
            raise HTTPException(404, f"Batch not found: {batch_id}") from exc

else:

    @router.post("/upload", response_model=CompanyESGData)
    async def upload_report(db: Session = Depends(get_db)) -> CompanyESGData:
        raise HTTPException(500, 'File uploads require the "python-multipart" package')


@router.post("/manual", response_model=CompanyESGData)
def save_manual_report(
    payload: ManualReportInput,
    db: Session = Depends(get_db),
) -> CompanyESGData:
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
def preview_merge(payload: MergePreviewRequest) -> MergePreviewResponse:
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
        industry_code=record.industry_code,
        industry_sector=record.industry_sector,
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


def _build_scored_metrics(
    *,
    latest,
    latest_merged_result,
    latest_source_records: list[CompanyReport],
    latest_period: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_records_by_id = {f"db:{record.id}": record for record in latest_source_records}
    scored_metrics: dict[str, Any] = {}
    evidence_anchors: list[dict[str, Any]] = []
    seen_evidence_keys: set[tuple[Any, ...]] = set()

    for metric in _PROFILE_METRICS:
        merged_metric = latest_merged_result.metrics.get(metric)
        value = (
            merged_metric.chosen_value
            if merged_metric
            else getattr(latest_merged_result.merged_metrics, metric, None)
        )
        chosen_record = source_records_by_id.get(merged_metric.chosen_source) if merged_metric else None
        source_record = chosen_record or latest
        anchor = _metric_anchor_from_record(source_record, metric, value)
        structured_evidence = _structured_metric_evidence(
            anchor,
            record=source_record,
            metric=metric,
            value=value,
        )

        scored_metric = CompanyProfileMetric(
            metric=metric,
            value=value,
            unit=_PROFILE_METRIC_UNITS.get(metric),
            period=normalize_reporting_period(
                fiscal_year=int(latest_period["fiscal_year"]),
                reporting_period_label=str(latest_period["label"]),
                reporting_period_type=str(latest_period["type"]),
                source_document_type=(
                    latest_period["reporting_standard"]
                    if isinstance(latest_period["reporting_standard"], str)
                    else None
                ),
            ),
            source_document_type=(
                merged_metric.chosen_source_document_type
                if merged_metric
                else getattr(source_record, "source_document_type", None)
            ),
            evidence=structured_evidence,
            framework_mappings=get_metric_framework_mappings(metric),
        )
        scored_metrics[metric] = scored_metric.model_dump(mode="json")

        if structured_evidence is not None:
            anchor.setdefault("source_doc_id", structured_evidence.source_doc_id)
            anchor.setdefault("page", structured_evidence.page)
            anchor.setdefault("char_range", structured_evidence.char_range)
            anchor.setdefault("snippet", structured_evidence.snippet)
            anchor.setdefault("extraction_method", structured_evidence.extraction_method)
            anchor.setdefault("confidence", structured_evidence.confidence)

            evidence_key = (
                metric,
                anchor.get("source_doc_id"),
                anchor.get("page"),
                tuple(anchor.get("char_range")) if isinstance(anchor.get("char_range"), list) else anchor.get("char_range"),
                anchor.get("snippet"),
            )
            if evidence_key not in seen_evidence_keys:
                seen_evidence_keys.add(evidence_key)
                evidence_anchors.append(anchor)

    return scored_metrics, evidence_anchors


@router.get("/companies/by-industry/{industry_code}")
def list_companies_by_industry(
    industry_code: str,
    db: Session = Depends(get_db),
) -> dict:
    """
    Return the latest report per company for a given NACE industry code,
    plus the numeric metric values that feed benchmark aggregation.
    """
    from benchmark.compute import BENCHMARK_METRICS

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


@router.get("/companies/{company_name}/{report_year:int}", response_model=CompanyESGData)
def get_company_report(
    company_name: str,
    report_year: int,
    db: Session = Depends(get_db),
) -> CompanyESGData:
    record = get_report(db, company_name, report_year)
    if not record:
        raise HTTPException(404, "Report not found")
    return _record_to_company_data(record)


@router.get("/{company_report_id:int}/audit-trail", response_model=list[AuditTrailRow])
def get_audit_trail(
    company_report_id: int,
    db: Session = Depends(get_db),
) -> list[AuditTrailRow]:
    report = db.query(CompanyReport).filter(CompanyReport.id == company_report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")

    bind = db.get_bind()
    if bind is None or not inspect(bind).has_table("extraction_runs"):
        return []

    query = """
        SELECT id, run_kind, model, verdict, applied, notes, created_at
        FROM extraction_runs
        WHERE company_report_id = :company_report_id
    """
    params: dict[str, Any] = {"company_report_id": company_report_id}

    if report.file_hash:
        query += " OR file_hash = :file_hash"
        params["file_hash"] = report.file_hash

    query += " ORDER BY created_at DESC LIMIT 50"

    rows = db.execute(text(query), params).mappings().all()
    return [
        AuditTrailRow(
            id=row["id"],
            run_kind=row["run_kind"],
            model=row["model"],
            verdict=row["verdict"],
            applied=row["applied"],
            notes=row["notes"],
            created_at=(
                row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else row["created_at"]
            ),
        )
        for row in rows
    ]


@router.get("/companies/{company_name}/history")
def get_company_history(
    company_name: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    from esg_frameworks.storage import list_framework_results

    records = list_reports_for_company(db, company_name)
    if not records:
        raise HTTPException(404, f"No reports found for {company_name}")
    resolved_name = records[0].company_name

    trend = []
    periods = []
    framework_metadata = []
    for record in records:
        source_records = list_source_reports_for_company_year(
            db,
            resolved_name,
            record.report_year,
        )
        merge_documents = [
            _record_to_merge_source_input(
                item,
                canonical_company_name_value=resolved_name,
            )
            for item in source_records
        ]
        merged_result = build_merged_result(merge_documents)
        merged_metrics = merged_result.merged_metrics
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
                "industry_code": record.industry_code,
                "industry_sector": record.industry_sector,
                "period": period,
                "source_url": record.source_url,
                "downloaded_at": record.downloaded_at.isoformat() if record.downloaded_at else None,
                "evidence_anchors": anchors,
                "framework_metadata": period_framework_metadata,
                "source_documents": [_source_document_payload(item) for item in source_records],
                "merged_result": merged_result.model_dump(),
            }
        )
        trend.append(
            {
                "year": record.report_year,
                "scope1": merged_metrics.scope1_co2e_tonnes,
                "scope2": merged_metrics.scope2_co2e_tonnes,
                "scope3": merged_metrics.scope3_co2e_tonnes,
                "renewable_pct": merged_metrics.renewable_energy_pct,
                "taxonomy_aligned_revenue_pct": merged_metrics.taxonomy_aligned_revenue_pct,
                "taxonomy_aligned_capex_pct": merged_metrics.taxonomy_aligned_capex_pct,
                "female_pct": merged_metrics.female_pct,
            }
        )

    return {
        "company_name": resolved_name,
        "periods": periods,
        "trend": trend,
        "framework_metadata": framework_metadata,
    }


def get_company_profile(
    company_name: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    from esg_frameworks.storage import list_framework_results
    from esg_frameworks.api import _SCORERS

    records = list_reports_for_company(db, company_name)
    if not records:
        raise HTTPException(404, f"No reports found for {company_name}")
    resolved_name = records[0].company_name

    latest = records[-1]
    observed_company_names: set[str] = set()
    for record in records:
        year_source_records = list_source_reports_for_company_year(
            db,
            resolved_name,
            record.report_year,
            collapse_duplicates=False,
        )
        observed_company_names.update(item.company_name for item in year_source_records if item.company_name)

    latest_source_records = list_source_reports_for_company_year(
        db,
        resolved_name,
        latest.report_year,
    )
    latest_merge_documents = [
        _record_to_merge_source_input(
            item,
            canonical_company_name_value=resolved_name,
        )
        for item in latest_source_records
    ]
    latest_merged_result = build_merged_result(latest_merge_documents)
    history = get_company_history(company_name=resolved_name, db=db)
    latest_data = _record_to_company_data(latest)
    latest_period = _period_metadata(latest)
    data_quality_summary = _data_quality_summary(latest_data)
    scored_metrics, scored_metric_evidence = _build_scored_metrics(
        latest=latest,
        latest_merged_result=latest_merged_result,
        latest_source_records=latest_source_records,
        latest_period=latest_period,
    )
    latest_evidence_anchors = scored_metric_evidence or _evidence_anchors_for_record(latest)
    profile_evidence_summary = latest_data.evidence_summary or latest_evidence_anchors

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
    years_available = [record.report_year for record in records]
    previous_trend_point = history["trend"][-2] if len(history["trend"]) >= 2 else None
    narrative_summary = _narrative_summary(
        latest_data=latest_data,
        previous_trend_point=previous_trend_point,
        periods_count=len(history["periods"]),
        years_available=years_available,
        framework_count=len(framework_rows),
        data_quality_summary=data_quality_summary,
    )
    identity_provenance_summary = _identity_provenance_summary(
        requested_company_name=company_name,
        canonical_company_name_value=resolved_name,
        latest_source_document_type=latest_period["source_document_type"],
        observed_company_names=sorted(observed_company_names),
        source_priority_preview=_source_metadata_gap_preview(latest_source_records),
        merge_priority_preview=(
            "Canonical identity merge active across multiple source records."
            if len(latest_source_records) > 1
            else None
        ),
    )

    response_model = CompanyProfileV1Response(
        company_name=resolved_name,
        industry_code=latest_data.industry_code,
        industry_sector=latest_data.industry_sector,
        years_available=years_available,
        latest_year=latest.report_year,
        latest_period={
            "report_year": latest.report_year,
            "reporting_period_label": latest_period["label"],
            "reporting_period_type": latest_period["type"],
            "source_document_type": latest_period["source_document_type"],
            "industry_code": latest_data.industry_code,
            "industry_sector": latest_data.industry_sector,
            "period": latest_period,
            "framework_metadata": latest_framework_metadata,
        },
        latest_metrics=latest_data,
        scored_metrics=scored_metrics,
        trend=history["trend"],
        periods=history["periods"],
        framework_metadata=history["framework_metadata"],
        framework_scores=framework_scores,
        framework_results=framework_results,
        evidence_summary=profile_evidence_summary,
        evidence_anchors=latest_evidence_anchors,
        data_quality_summary=data_quality_summary,
        narrative_summary=narrative_summary,
        identity_provenance_summary=identity_provenance_summary,
        latest_sources=[_source_document_payload(item) for item in latest_source_records],
        latest_merged_result=latest_merged_result.model_dump(mode="json"),
    )
    return response_model.model_dump(mode="json")


@v1_router.get("/companies/{company_name}/profile", response_model=CompanyProfileV1Response)
def get_company_profile_v1(
    company_name: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return get_company_profile(company_name=company_name, db=db)


@router.get(
    "/companies/{company_name}/profile",
    response_model=CompanyProfileV1Response,
    responses={200: {"headers": {"Deprecation": {"schema": {"type": "string"}}}}},
)
def get_company_profile_legacy(
    company_name: str,
    response: Response,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = f'</api/v1/companies/{company_name}/profile>; rel="successor-version"'
    return get_company_profile(company_name=company_name, db=db)


@router.get("/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)) -> dict[str, Any]:
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
def list_company_reports(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
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
                "industry_code": record.industry_code,
                "industry_sector": record.industry_sector,
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
) -> dict[str, str | int | bool]:
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
) -> dict[str, str | int]:
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

import json
from typing import Any

from core.evidence import Evidence, infer_extraction_method, normalize_raw_evidence
from core.schemas import CompanyESGData

CORE_METRICS: tuple[str, ...] = (
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
    "primary_activities",
)

DISCLOSURE_KEY_METRICS = CORE_METRICS[:7] + CORE_METRICS[8:9] + CORE_METRICS[10:13]
PROFILE_METRICS = DISCLOSURE_KEY_METRICS + CORE_METRICS[13:]
UPLOAD_FALLBACK_METRICS = CORE_METRICS[:13]


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


def _manual_evidence_summary(
    data: CompanyESGData,
    *,
    source_url: str | None = None,
) -> list[dict[str, Any]]:
    source = source_url or f"manual://{data.company_name}/{data.report_year}"
    evidence: list[dict[str, Any]] = []
    for metric in DISCLOSURE_KEY_METRICS:
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

    evidence: list[dict[str, Any]] = []
    for metric in UPLOAD_FALLBACK_METRICS:
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

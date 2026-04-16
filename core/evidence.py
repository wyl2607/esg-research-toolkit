from __future__ import annotations

from typing import Any, Literal, Mapping

from pydantic import BaseModel, Field


EvidenceExtractionMethod = Literal["manual", "pdf_text", "regex", "llm", "merge", "unknown"]


class Evidence(BaseModel):
    source_doc_id: str
    page: int | None = None
    char_range: tuple[int, int] | None = None
    snippet: str | None = None
    extraction_method: EvidenceExtractionMethod | str = "unknown"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


_EXTRACTION_METHOD_BY_SOURCE_TYPE: dict[str, EvidenceExtractionMethod] = {
    "manual": "manual",
    "manual_case": "manual",
    "manual_entry": "manual",
    "pdf": "pdf_text",
    "pdf_text": "pdf_text",
    "regex": "regex",
    "llm": "llm",
    "ai": "llm",
    "merge": "merge",
}

_DEFAULT_CONFIDENCE_BY_METHOD: dict[str, float] = {
    "manual": 1.0,
    "regex": 0.85,
    "llm": 0.75,
    "pdf_text": 0.65,
    "merge": 0.55,
    "unknown": 0.5,
}


def infer_extraction_method(
    entry: Mapping[str, Any] | None,
    *,
    fallback_source_type: str | None = None,
    fallback_source_doc_id: str | None = None,
) -> str:
    if entry:
        explicit = entry.get("extraction_method")
        if isinstance(explicit, str) and explicit:
            return explicit

        source_type = entry.get("source_type")
        if isinstance(source_type, str) and source_type:
            return _EXTRACTION_METHOD_BY_SOURCE_TYPE.get(source_type, source_type)

    if fallback_source_type:
        if fallback_source_type in _EXTRACTION_METHOD_BY_SOURCE_TYPE:
            return _EXTRACTION_METHOD_BY_SOURCE_TYPE[fallback_source_type]
        if fallback_source_type in {
            "annual_report",
            "sustainability_report",
            "annual_sustainability_report",
            "filing",
            "announcement",
            "event",
        }:
            return "pdf_text"
        return "manual" if fallback_source_type == "manual_case" else "unknown"

    if fallback_source_doc_id and fallback_source_doc_id.startswith("manual://"):
        return "manual"

    return "unknown"


def normalize_char_range(value: Any) -> tuple[int, int] | None:
    if isinstance(value, (list, tuple)) and len(value) == 2:
        start, end = value
        if isinstance(start, int) and isinstance(end, int):
            return start, end
    return None


def normalize_raw_evidence(
    entry: Mapping[str, Any] | None,
    *,
    fallback_source_doc_id: str | None = None,
    fallback_source_type: str | None = None,
    fallback_snippet: str | None = None,
) -> Evidence | None:
    raw_entry = entry or {}

    source_doc_id = next(
        (
            candidate
            for candidate in (
                raw_entry.get("source_doc_id"),
                raw_entry.get("file_hash"),
                raw_entry.get("source_url"),
                raw_entry.get("source"),
                fallback_source_doc_id,
            )
            if isinstance(candidate, str) and candidate
        ),
        None,
    )
    if not source_doc_id:
        return None

    page = raw_entry.get("page")
    if not isinstance(page, int):
        page_number = raw_entry.get("page_number")
        page = page_number if isinstance(page_number, int) else None

    snippet = next(
        (
            candidate
            for candidate in (
                raw_entry.get("snippet"),
                raw_entry.get("extraction_note"),
                raw_entry.get("note"),
                fallback_snippet,
            )
            if isinstance(candidate, str) and candidate
        ),
        None,
    )

    extraction_method = infer_extraction_method(
        raw_entry,
        fallback_source_type=fallback_source_type,
        fallback_source_doc_id=source_doc_id,
    )

    confidence = raw_entry.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        confidence = _DEFAULT_CONFIDENCE_BY_METHOD.get(extraction_method, 0.5)

    return Evidence(
        source_doc_id=source_doc_id,
        page=page,
        char_range=normalize_char_range(raw_entry.get("char_range")),
        snippet=snippet,
        extraction_method=extraction_method,
        confidence=float(confidence),
    )

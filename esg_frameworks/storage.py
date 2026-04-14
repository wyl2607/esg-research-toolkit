from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.database import Base
from esg_frameworks.schemas import FrameworkScoreResult
from report_parser.company_identity import canonical_company_name, company_name_variants


class FrameworkAnalysisResult(Base):
    __tablename__ = "framework_analysis_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String, nullable=False, index=True)
    report_year = Column(Integer, nullable=False, index=True)
    framework_id = Column(String, nullable=False, index=True)
    framework_name = Column(String, nullable=False)
    framework_version = Column(String, nullable=False)
    total_score = Column(Float, nullable=False)
    grade = Column(String, nullable=False)
    coverage_pct = Column(Float, nullable=False)
    result_payload = Column(Text, nullable=False)  # Full FrameworkScoreResult as JSON
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


def _normalize_framework_payload(
    payload: dict,
    *,
    framework_version: str,
) -> dict:
    normalized = dict(payload)
    normalized["framework_version"] = normalized.get("framework_version") or framework_version
    normalized["analyzed_at"] = None
    return normalized


def _serialize_framework_payload(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _payload_matches_row(
    row: FrameworkAnalysisResult,
    *,
    expected_payload: dict,
) -> bool:
    try:
        existing_payload = json.loads(row.result_payload)
    except json.JSONDecodeError:
        return False
    normalized_existing = _normalize_framework_payload(
        existing_payload,
        framework_version=row.framework_version,
    )
    return normalized_existing == expected_payload


def save_framework_result(
    db: Session,
    result: FrameworkScoreResult,
    *,
    framework_version: str = "v1",
) -> FrameworkAnalysisResult:
    payload = result.model_dump()
    resolved_framework_version = payload.get("framework_version") or framework_version
    normalized_payload = _normalize_framework_payload(
        payload,
        framework_version=resolved_framework_version,
    )
    canonical_name = canonical_company_name(result.company_name)
    existing_records = (
        db.query(FrameworkAnalysisResult)
        .filter(
            FrameworkAnalysisResult.company_name == canonical_name,
            FrameworkAnalysisResult.report_year == result.report_year,
            FrameworkAnalysisResult.framework_id == result.framework_id,
            FrameworkAnalysisResult.framework_version == resolved_framework_version,
        )
        .order_by(FrameworkAnalysisResult.created_at.desc(), FrameworkAnalysisResult.id.desc())
        .all()
    )
    for existing_record in existing_records:
        if _payload_matches_row(existing_record, expected_payload=normalized_payload):
            return existing_record
    record = FrameworkAnalysisResult(
        company_name=canonical_name,
        report_year=result.report_year,
        framework_id=result.framework_id,
        framework_name=result.framework,
        framework_version=resolved_framework_version,
        total_score=result.total_score,
        grade=result.grade,
        coverage_pct=result.coverage_pct,
        result_payload=_serialize_framework_payload(normalized_payload),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_framework_results(
    db: Session,
    *,
    company_name: str,
    report_year: int,
) -> list[FrameworkAnalysisResult]:
    variants = [variant.lower() for variant in company_name_variants(company_name)]
    return (
        db.query(FrameworkAnalysisResult)
        .filter(
            func.lower(FrameworkAnalysisResult.company_name).in_(variants),
            FrameworkAnalysisResult.report_year == report_year,
        )
        .order_by(FrameworkAnalysisResult.created_at.desc())
        .all()
    )


def get_framework_result(db: Session, result_id: int) -> FrameworkAnalysisResult | None:
    return db.query(FrameworkAnalysisResult).filter(FrameworkAnalysisResult.id == result_id).first()

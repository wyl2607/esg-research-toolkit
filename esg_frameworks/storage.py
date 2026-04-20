from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, UniqueConstraint, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.database import Base
from esg_frameworks.schemas import FrameworkScoreResult, normalize_framework_version
from report_parser.company_identity import canonical_company_name, company_name_variants


class FrameworkAnalysisResult(Base):
    __tablename__ = "framework_analysis_results"
    __table_args__ = (
        UniqueConstraint(
            "company_name",
            "report_year",
            "framework_id",
            "framework_version",
            "payload_hash",
            name="uq_framework_analysis_payload",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String, nullable=False, index=True)
    report_year = Column(Integer, nullable=False, index=True)
    framework_id = Column(String, nullable=False, index=True)
    framework_name = Column(String, nullable=False)
    framework_version = Column(String, nullable=False)
    total_score = Column(Float, nullable=False)
    grade = Column(String, nullable=False)
    coverage_pct = Column(Float, nullable=False)
    payload_hash = Column(String, nullable=False, default="", index=True)
    result_payload = Column(Text, nullable=False)  # Full FrameworkScoreResult as JSON
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


def _normalize_framework_payload(
    payload: dict,
    *,
    framework_version: str,
) -> dict:
    normalized = dict(payload)
    normalized["framework_version"] = _resolve_framework_version(
        framework_id=normalized.get("framework_id", ""),
        framework_version=normalized.get("framework_version") or framework_version,
    )
    normalized["analyzed_at"] = None
    return normalized


def _serialize_framework_payload(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _payload_hash(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _resolve_framework_version(
    *,
    framework_id: str,
    framework_version: str | None,
) -> str:
    return normalize_framework_version(
        framework_id=framework_id,
        framework_version=framework_version,
    )


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
    framework_version: str | None = None,
) -> FrameworkAnalysisResult:
    payload = result.model_dump()
    resolved_framework_version = _resolve_framework_version(
        framework_id=result.framework_id,
        framework_version=payload.get("framework_version") or framework_version,
    )
    normalized_payload = _normalize_framework_payload(
        payload,
        framework_version=resolved_framework_version,
    )
    serialized_payload = _serialize_framework_payload(normalized_payload)
    payload_hash = _payload_hash(serialized_payload)
    canonical_name = canonical_company_name(result.company_name)
    existing_records = (
        db.query(FrameworkAnalysisResult)
        .filter(
            FrameworkAnalysisResult.company_name == canonical_name,
            FrameworkAnalysisResult.report_year == result.report_year,
            FrameworkAnalysisResult.framework_id == result.framework_id,
            FrameworkAnalysisResult.framework_version == resolved_framework_version,
            FrameworkAnalysisResult.payload_hash == payload_hash,
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
        payload_hash=payload_hash,
        result_payload=serialized_payload,
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


def ensure_framework_storage_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    if "alembic_version" in inspector.get_table_names():
        return

    if engine.dialect.name != "sqlite":
        return

    with engine.begin() as conn:
        existing_cols = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(framework_analysis_results)")).fetchall()
        }
        if "payload_hash" not in existing_cols:
            conn.execute(text("ALTER TABLE framework_analysis_results ADD COLUMN payload_hash TEXT"))

        rows = conn.execute(
            text("SELECT id, result_payload, payload_hash FROM framework_analysis_results")
        ).mappings().all()
        for row in rows:
            payload = row["result_payload"] or ""
            current_hash = row["payload_hash"]
            if isinstance(current_hash, str) and current_hash.strip():
                continue
            conn.execute(
                text(
                    "UPDATE framework_analysis_results SET payload_hash = :payload_hash WHERE id = :id"
                ),
                {"id": row["id"], "payload_hash": _payload_hash(payload)},
            )

        conn.execute(
            text(
                """
                DELETE FROM framework_analysis_results
                WHERE id IN (
                    SELECT id FROM (
                        SELECT id,
                               ROW_NUMBER() OVER (
                                   PARTITION BY company_name, report_year, framework_id, framework_version, payload_hash
                                   ORDER BY created_at DESC, id DESC
                               ) AS rn
                        FROM framework_analysis_results
                        WHERE payload_hash IS NOT NULL AND trim(payload_hash) != ''
                    ) dedup
                    WHERE dedup.rn > 1
                )
                """
            )
        )

        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_framework_analysis_payload "
                "ON framework_analysis_results (company_name, report_year, framework_id, framework_version, payload_hash)"
            )
        )

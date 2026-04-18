"""Database models for multi-level QA audit results.

All audit records are APPEND-ONLY. No automatic data corrections applied.
Human review is required before any writeback to source-of-truth tables.
"""

from datetime import datetime, timedelta
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Index
from sqlalchemy.orm import Session

from core.database import Base


class AuditQAResult(Base):
    """Append-only record of LLM audit verdicts."""

    __tablename__ = "audit_qa_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # identifiers
    company_name = Column(String(255), nullable=False, index=True)
    report_year = Column(Integer, nullable=False, index=True)
    field = Column(String(100), nullable=False, index=True)
    
    # extracted data
    extracted_value = Column(Text, nullable=True)
    
    # audit result
    verdict = Column(
        String(50),
        nullable=False,
        index=True,
        # ok | missing | incorrect | context_mismatch | needs_review
    )
    confidence = Column(Float, nullable=False)  # 0.0–1.0
    
    # evidence
    evidence_quote = Column(Text, nullable=True)
    evidence_page = Column(Integer, nullable=True)
    
    # suggestion for improvement
    suggestion = Column(Text, nullable=True)
    
    # audit metadata
    audit_level = Column(Integer, nullable=False)  # 1 or 2
    audit_model = Column(String(100), nullable=False)
    audit_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # document provenance
    doc_hash = Column(String(64), nullable=True, index=True)
    
    # human review (null = pending, true/false = approved/rejected)
    human_review = Column(String(20), nullable=True, default=None)  # pending | approved | rejected
    reviewer = Column(String(255), nullable=True)
    review_timestamp = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    
    # if approved & deemed correct, track the correction
    corrected_value = Column(Text, nullable=True)  # what should the correct value be?
    correction_rationale = Column(Text, nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_audit_key", "company_name", "report_year", "field", "audit_timestamp"),
        Index("idx_audit_status", "verdict", "human_review", "audit_timestamp"),
    )


class AuditSummary(Base):
    """Aggregate audit metrics per field/version (for trend tracking)."""

    __tablename__ = "audit_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # scope
    field = Column(String(100), nullable=False, index=True)
    parser_version = Column(String(50), nullable=True)
    audit_period_start = Column(DateTime, nullable=False)
    audit_period_end = Column(DateTime, nullable=False)
    
    # stats
    total_audits = Column(Integer, nullable=False, default=0)
    ok_count = Column(Integer, nullable=False, default=0)
    missing_count = Column(Integer, nullable=False, default=0)
    incorrect_count = Column(Integer, nullable=False, default=0)
    context_mismatch_count = Column(Integer, nullable=False, default=0)
    needs_review_count = Column(Integer, nullable=False, default=0)
    
    # aggregates
    avg_confidence = Column(Float, nullable=True)
    accuracy_pct = Column(Float, nullable=True)  # (ok + context_mismatch) / total * 100
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_summary_key", "field", "parser_version", "audit_period_start"),
    )


def record_audit_result(db: Session, result: "AuditQAResult") -> None:
    """Append new audit result (idempotent-safe)."""
    db.add(result)
    db.commit()


def get_pending_reviews(db: Session, limit: int = 50) -> list["AuditQAResult"]:
    """Get audits awaiting human review."""
    return (
        db.query(AuditQAResult)
        .filter(AuditQAResult.human_review.is_(None))
        .order_by(AuditQAResult.audit_timestamp.desc())
        .limit(limit)
        .all()
    )


def get_audit_trend(db: Session, field: str, days: int = 30) -> list["AuditSummary"]:
    """Get audit trend for a field over recent period."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(AuditSummary)
        .filter(AuditSummary.field == field, AuditSummary.audit_period_end >= cutoff)
        .order_by(AuditSummary.audit_period_start.asc())
        .all()
    )


def approve_correction(
    db: Session,
    audit_id: int,
    corrected_value: str,
    rationale: str,
    reviewer: str,
) -> None:
    """Human approves a suggested correction."""
    record = db.query(AuditQAResult).filter(AuditQAResult.id == audit_id).first()
    if not record:
        raise ValueError(f"Audit ID {audit_id} not found")
    
    record.human_review = "approved"
    record.corrected_value = corrected_value
    record.correction_rationale = rationale
    record.reviewer = reviewer
    record.review_timestamp = datetime.utcnow()
    
    db.commit()


def reject_audit(
    db: Session,
    audit_id: int,
    reason: str,
    reviewer: str,
) -> None:
    """Human rejects an audit (auditor was wrong)."""
    record = db.query(AuditQAResult).filter(AuditQAResult.id == audit_id).first()
    if not record:
        raise ValueError(f"Audit ID {audit_id} not found")
    
    record.human_review = "rejected"
    record.review_notes = reason
    record.reviewer = reviewer
    record.review_timestamp = datetime.utcnow()
    
    db.commit()

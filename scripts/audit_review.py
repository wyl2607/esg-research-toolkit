"""
Interactive human review CLI for audit results.

Shows pending audits, applies corrections, and tracks review workflow.

Usage:
  python scripts/audit_review.py               # list pending reviews
  python scripts/audit_review.py --approve ID corrected_value
  python scripts/audit_review.py --reject ID reason
  python scripts/audit_review.py --summary field
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import SessionLocal  # noqa: E402
from report_parser.audit_models import (  # noqa: E402
    AuditQAResult,
    AuditSummary,
    get_pending_reviews,
    get_audit_trend,
    approve_correction,
    reject_audit,
)


def format_verdict(verdict: str, confidence: float) -> str:
    """Pretty-print verdict with confidence."""
    color_map = {
        "ok": "✓",
        "missing": "○",
        "incorrect": "✗",
        "context_mismatch": "?",
        "needs_review": "!",
    }
    symbol = color_map.get(verdict, "?")
    return f"{symbol} {verdict} ({confidence:.0%})"


def show_pending_reviews(db: SessionLocal, limit: int = 50) -> None:
    """List all pending audit reviews."""
    pending = get_pending_reviews(db, limit=limit)
    
    if not pending:
        print("✓ All audits have been reviewed!")
        return
    
    print(f"\n{len(pending)} pending audits (showing first {limit}):\n")
    print("ID  | Company            | Year | Field                    | Verdict            | Quote")
    print("-" * 120)
    
    for audit in pending:
        quote = (audit.evidence_quote or "")[:40]
        if len(audit.evidence_quote or "") > 40:
            quote += "..."
        
        print(
            f"{audit.id:3d} | {audit.company_name:18s} | {audit.report_year:4d} | "
            f"{audit.field:24s} | {format_verdict(audit.verdict, audit.confidence):20s} | {quote}"
        )
    
    print(f"\nTotal pending: {len(pending)}")
    print("\nNext step: Use --approve ID corrected_value or --reject ID reason to review.\n")


def show_audit_trend(db: SessionLocal, field: str, days: int = 30) -> None:
    """Show audit trend for a field."""
    summaries = get_audit_trend(db, field, days=days)
    
    if not summaries:
        print(f"No audit summaries found for {field} in past {days} days.")
        return
    
    print(f"\nAudit trend for {field} (past {days} days):\n")
    print("Period          | Total | OK  | Missing | Incorrect | Context Mismatch | Needs Review | Accuracy")
    print("-" * 110)
    
    for summary in summaries:
        accuracy = f"{summary.accuracy_pct:.1f}%" if summary.accuracy_pct else "N/A"
        print(
            f"{summary.audit_period_start.strftime('%Y-%m-%d')} - "
            f"{summary.audit_period_end.strftime('%Y-%m-%d')} | "
            f"{summary.total_audits:5d} | {summary.ok_count:3d} | {summary.missing_count:7d} | "
            f"{summary.incorrect_count:9d} | {summary.context_mismatch_count:16d} | "
            f"{summary.needs_review_count:12d} | {accuracy}"
        )
    
    print()


def approve_audit_interactive(
    db: SessionLocal,
    audit_id: int,
    corrected_value: Optional[str] = None,
) -> None:
    """Approve an audit and store correction."""
    audit = db.query(AuditQAResult).filter(AuditQAResult.id == audit_id).first()
    
    if not audit:
        print(f"✗ Audit ID {audit_id} not found.")
        return
    
    if audit.human_review:
        print(f"✗ Audit {audit_id} already reviewed ({audit.human_review}).")
        return
    
    print(f"\n{'-'*60}")
    print(f"Audit #{audit_id}: {audit.company_name} {audit.report_year}")
    print(f"Field: {audit.field}")
    print(f"Extracted value: {audit.extracted_value}")
    print(f"Verdict: {format_verdict(audit.verdict, audit.confidence)}")
    print(f"Evidence page: {audit.evidence_page}")
    print(f"Quote: {audit.evidence_quote[:100]}...")
    print(f"Suggestion: {audit.suggestion}")
    print(f"{'-'*60}\n")
    
    if corrected_value is None:
        corrected_value = input("Enter corrected value (or press Enter to skip): ").strip()
    
    if not corrected_value:
        print("Skipped.")
        return
    
    rationale = input("Rationale for correction: ").strip()
    if not rationale:
        rationale = "Auditor suggestion adopted."
    
    try:
        approve_correction(
            db,
            audit_id,
            corrected_value,
            rationale,
            reviewer="manual-review",
        )
        print(f"✓ Audit {audit_id} approved with correction.\n")
    except Exception as e:
        print(f"✗ Failed to approve: {e}\n")


def reject_audit_interactive(
    db: SessionLocal,
    audit_id: int,
    reason: Optional[str] = None,
) -> None:
    """Reject an audit (auditor was wrong)."""
    audit = db.query(AuditQAResult).filter(AuditQAResult.id == audit_id).first()
    
    if not audit:
        print(f"✗ Audit ID {audit_id} not found.")
        return
    
    if audit.human_review:
        print(f"✗ Audit {audit_id} already reviewed ({audit.human_review}).")
        return
    
    print(f"\n{'-'*60}")
    print(f"Audit #{audit_id}: {audit.company_name} {audit.report_year}")
    print(f"Field: {audit.field}")
    print(f"Extracted value: {audit.extracted_value}")
    print(f"Verdict: {format_verdict(audit.verdict, audit.confidence)}")
    print(f"Suggestion: {audit.suggestion}")
    print(f"{'-'*60}\n")
    
    if reason is None:
        reason = input("Reason for rejection (auditor was wrong): ").strip()
    
    if not reason:
        reason = "Auditor verdict was incorrect."
    
    try:
        reject_audit(
            db,
            audit_id,
            reason,
            reviewer="manual-review",
        )
        print(f"✓ Audit {audit_id} rejected.\n")
    except Exception as e:
        print(f"✗ Failed to reject: {e}\n")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--approve", type=int, help="Approve audit by ID")
    parser.add_argument("--value", help="Corrected value (for --approve)")
    parser.add_argument("--reject", type=int, help="Reject audit by ID")
    parser.add_argument("--reason", help="Rejection reason (for --reject)")
    parser.add_argument("--summary", help="Show audit trend for field")
    parser.add_argument("--limit", type=int, default=50, help="Limit pending results")
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        if args.approve:
            approve_audit_interactive(db, args.approve, corrected_value=args.value)
        elif args.reject:
            reject_audit_interactive(db, args.reject, reason=args.reason)
        elif args.summary:
            show_audit_trend(db, args.summary)
        else:
            show_pending_reviews(db, limit=args.limit)
    finally:
        db.close()


if __name__ == "__main__":
    main()

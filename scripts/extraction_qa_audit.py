"""Multi-level QA audit for ESG data extraction.

Combines fast L1 screening (GPT-5.4 mini, ~500–1500 chars per field)
with deeper L2 verification (GPT-4o, page-local context) for flagged cases.

All corrections are append-only + human-reviewable, never auto-applied.

Usage:
  python scripts/extraction_qa_audit.py                # recent + all fields
  python scripts/extraction_qa_audit.py --company RWE  # single company
  python scripts/extraction_qa_audit.py --level 1      # fast screening only
  python scripts/extraction_qa_audit.py --level 2 --fields scope1_co2e_tonnes
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

import httpx

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import SessionLocal  # noqa: E402
from scripts.seed_german_demo import PDF_CACHE_DIR  # noqa: E402

# ─── Types ──────────────────────────────────────────────────────────────

AuditLevel = Literal[1, 2]
AuditVerdict = Literal["ok", "missing", "incorrect", "context_mismatch", "needs_review"]

@dataclass
class ExtractedMetric:
    """One metric from extraction output."""
    field: str
    value: str | int | float | None
    confidence: float  # 0.0–1.0

@dataclass
class PDFContext:
    """PDF text with page boundaries."""
    pages: list[str]  # page_num -> text
    total_pages: int
    total_chars: int

@dataclass
class AuditResult:
    """One verdict for one (company, year, field)."""
    company_name: str
    report_year: int
    field: str
    extracted_value: str | int | float | None
    verdict: AuditVerdict
    confidence: float  # 0.0–1.0
    evidence_quote: str | None
    evidence_page: int | None
    suggestion: str | None
    model: str
    level: AuditLevel
    timestamp: str
    doc_hash: str

# ─── Constants ──────────────────────────────────────────────────────────

METRIC_KEYWORDS: dict[str, list[str]] = {
    "scope1_co2e_tonnes": ["scope 1", "scope1", "s1", "direct emissions"],
    "scope2_co2e_tonnes": ["scope 2", "scope2", "s2", "electricity", "indirect"],
    "scope3_co2e_tonnes": ["scope 3", "scope3", "s3", "value chain"],
    "renewable_energy_pct": ["renewable", "renewables", "%", "%", "green energy"],
    "taxonomy_aligned_revenue_pct": ["taxonomy", "aligned", "revenue", "sustainable"],
    "water_usage_m3": ["water", "m3", "m³", "consumption", "withdrawal"],
    "waste_recycled_pct": ["waste", "recycled", "recycling", "%"],
    "female_pct": ["female", "women", "gender", "diversity", "%"],
    "energy_consumption_mwh": ["energy", "mwh", "kwh", "consumption"],
}

DEFAULT_API_BASE = os.environ.get("API_BASE", "http://localhost:8000")
DEFAULT_L1_MODEL = "gpt-5.4-mini"  # fast + cheap for screening
DEFAULT_L2_MODEL = "gpt-4o"       # accurate for detailed audit


# ─── PDF Context Extraction ─────────────────────────────────────────────

def extract_pdf_pages(pdf_path: Path) -> PDFContext | None:
    """Extract PDF text split by pages."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return None

    try:
        pages = []
        with fitz.open(str(pdf_path)) as doc:
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text("text") or ""
                # clean
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                cleaned = "\n".join(lines)
                pages.append(cleaned)
        
        total_chars = sum(len(p) for p in pages)
        return PDFContext(
            pages=pages,
            total_pages=len(pages),
            total_chars=total_chars,
        )
    except Exception:
        return None


def find_metric_pages(pdf_context: PDFContext, field: str, top_n: int = 3) -> list[tuple[int, str]]:
    """
    Find pages most likely to contain a metric.
    Returns list of (page_num, snippet) ranked by keyword match.
    """
    keywords = METRIC_KEYWORDS.get(field, [field])
    keyword_lower = [kw.lower() for kw in keywords]

    scored_pages: list[tuple[int, int, str]] = []
    for page_num, text in enumerate(pdf_context.pages, start=1):
        text_lower = text.lower()
        score = sum(text_lower.count(kw) for kw in keyword_lower)
        if score > 0:
            scored_pages.append((page_num, score, text))

    scored_pages.sort(key=lambda x: x[1], reverse=True)
    return [(page_num, text) for page_num, _, text in scored_pages[:top_n]]


def _truncate_snippet(text: str, max_chars: int = 1500) -> str:
    """Truncate to max_chars, trying to keep word boundaries."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_newline = truncated.rfind("\n")
    if last_newline > max_chars * 0.8:
        return truncated[:last_newline]
    return truncated + "\n[... truncated ...]"


# ─── Level 1: Fast Screening ────────────────────────────────────────────

def audit_level_1(
    company_name: str,
    report_year: int,
    field: str,
    extracted_value: str | int | float | None,
    pdf_context: PDFContext,
    model: str = DEFAULT_L1_MODEL,
) -> AuditResult | None:
    """
    L1: Fast screening on targeted snippet. ~500–1500 chars.
    Returns verdict or None if context lookup fails.
    """
    if pdf_context.total_chars < 100:
        return AuditResult(
            company_name=company_name,
            report_year=report_year,
            field=field,
            extracted_value=extracted_value,
            verdict="needs_review",
            confidence=0.0,
            evidence_quote=None,
            evidence_page=None,
            suggestion="PDF extraction failed or too short",
            model=model,
            level=1,
            timestamp=datetime.utcnow().isoformat(),
            doc_hash="",
        )

    pages_with_metric = find_metric_pages(pdf_context, field, top_n=2)
    if not pages_with_metric:
        return AuditResult(
            company_name=company_name,
            report_year=report_year,
            field=field,
            extracted_value=extracted_value,
            verdict="missing",
            confidence=0.8,
            evidence_quote=None,
            evidence_page=None,
            suggestion=f"No pages matched keywords for {field}",
            model=model,
            level=1,
            timestamp=datetime.utcnow().isoformat(),
            doc_hash="",
        )

    # build snippet
    snippet_parts = []
    for page_num, text in pages_with_metric[:2]:
        truncated = _truncate_snippet(text, max_chars=750)
        snippet_parts.append(f"[Page {page_num}]\n{truncated}")
    snippet = "\n\n".join(snippet_parts)

    # prompt
    field_readable = field.replace("_", " ").title()
    prompt = f"""You are reviewing ESG data extraction accuracy.

Field: {field_readable}
Extracted Value: {extracted_value!r}
Report Year: {report_year}
Company: {company_name}

Below is the relevant PDF text:
{snippet}

Question: Is the extracted value "{extracted_value}" actually stated in this PDF text?
- "ok" if value is clearly stated and correct
- "missing" if the field should be there but is not disclosed
- "incorrect" if the value is wrong (cite correct value)
- "context_mismatch" if value is mentioned but context is unclear
- "needs_review" if you are unsure

Respond ONLY with JSON:
{{"verdict": "<ok|missing|incorrect|context_mismatch|needs_review>", "confidence": 0.5, "quote": "...", "reason": "..."}}
"""

    try:
        client = httpx.Client(timeout=30)
        response = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY')}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            },
        )
        if response.status_code != 200:
            return None
        
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        verdict_obj = json.loads(content)
        
        return AuditResult(
            company_name=company_name,
            report_year=report_year,
            field=field,
            extracted_value=extracted_value,
            verdict=verdict_obj.get("verdict", "needs_review"),
            confidence=verdict_obj.get("confidence", 0.5),
            evidence_quote=verdict_obj.get("quote"),
            evidence_page=pages_with_metric[0][0] if pages_with_metric else None,
            suggestion=verdict_obj.get("reason"),
            model=model,
            level=1,
            timestamp=datetime.utcnow().isoformat(),
            doc_hash="",
        )
    except Exception as e:
        print(f"L1 audit failed: {e}", file=sys.stderr)
        return None


# ─── Level 2: Detailed Verification ─────────────────────────────────────

def audit_level_2(
    company_name: str,
    report_year: int,
    field: str,
    extracted_value: str | int | float | None,
    pdf_context: PDFContext,
    level_1_result: AuditResult | None = None,
    model: str = DEFAULT_L2_MODEL,
) -> AuditResult | None:
    """
    L2: Deeper audit with page-local context (~5–15k chars).
    Only run this if L1 flagged or if we're doing thorough audit.
    """
    if pdf_context.total_chars < 100:
        return None

    pages_with_metric = find_metric_pages(pdf_context, field, top_n=3)
    if not pages_with_metric:
        return None

    # build richer context
    context_parts = []
    for page_num, text in pages_with_metric:
        # include neighboring page if available
        context = text
        if page_num > 1 and page_num - 1 < len(pdf_context.pages):
            prev_text = pdf_context.pages[page_num - 2]  # 0-indexed
            context = prev_text[-500:] + "\n[...]\n" + context
        context_parts.append(f"[Page {page_num}]\n{context}")
    
    full_context = "\n\n".join(context_parts)
    if len(full_context) > 15000:
        full_context = full_context[:15000] + "\n[... truncated ...]"

    prompt = f"""You are performing a detailed audit of ESG data extraction.

Company: {company_name}
Report Year: {report_year}
Field: {field.replace("_", " ").title()}
Extracted Value: {extracted_value!r}

Below is the relevant PDF context (possibly spanning multiple pages):

{full_context}

Task:
1. Find the exact value for this field in the context.
2. If the extracted value is WRONG, cite the correct value.
3. If the value is MISSING or NOT DISCLOSED, state that clearly.
4. If you find the value but extraction seems plausible, say "ok".

Respond with JSON:
{{"verdict": "<ok|missing|incorrect|not_disclosed>", "confidence": 0.0–1.0, "correct_value": "...", "exact_quote": "...", "issue": "...", "suggested_fix": "..."}}
"""

    try:
        client = httpx.Client(timeout=60)
        response = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY')}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
            },
        )
        if response.status_code != 200:
            return None
        
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        verdict_obj = json.loads(content)
        
        return AuditResult(
            company_name=company_name,
            report_year=report_year,
            field=field,
            extracted_value=extracted_value,
            verdict=verdict_obj.get("verdict", "needs_review"),
            confidence=verdict_obj.get("confidence", 0.5),
            evidence_quote=verdict_obj.get("exact_quote"),
            evidence_page=pages_with_metric[0][0] if pages_with_metric else None,
            suggestion=verdict_obj.get("suggested_fix"),
            model=model,
            level=2,
            timestamp=datetime.utcnow().isoformat(),
            doc_hash="",
        )
    except Exception as e:
        print(f"L2 audit failed: {e}", file=sys.stderr)
        return None


# ─── Main ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--company", help="Audit single company")
    parser.add_argument("--level", type=int, default=1, choices=[1, 2], help="Audit level (1=fast, 2=detailed)")
    parser.add_argument("--fields", default="", help="Comma-separated fields to audit (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="Don't call LLM, just prepare")
    args = parser.parse_args()

    print("Multi-level QA audit initialized.")
    print(f"Level: {args.level}, Dry-run: {args.dry_run}")
    print("\nNote: All audit verdicts are append-only. No automatic corrections applied.")
    print("Human review required before any data writeback.\n")

    # parse field list
    fields_to_audit = set(METRIC_KEYWORDS.keys())
    if args.fields:
        requested = set(f.strip() for f in args.fields.split(","))
        fields_to_audit &= requested

    # fetch companies
    db = SessionLocal()
    
    from core.schemas import CompanyESGData
    query = (
        db.query(CompanyESGData)
        .order_by(CompanyESGData.company_name.asc(), CompanyESGData.report_year.desc())
    )
    
    if args.company:
        query = query.filter(CompanyESGData.company_name == args.company)
    
    companies = query.all()
    print(f"Found {len(companies)} company records to audit.\n")

    if not companies:
        print("No companies found. Exiting.")
        return

    audit_results: list[AuditResult] = []
    errors: list[str] = []

    for company in companies:
        print(f"[{company.company_name} {company.report_year}]", flush=True)
        
        # find PDF
        pdf_path = PDF_CACHE_DIR / f"{company.company_name}_{company.report_year}.pdf"
        if not pdf_path.exists():
            errors.append(f"PDF not found: {pdf_path}")
            print(f"  ⚠️  PDF not found\n")
            continue

        # extract PDF pages
        pdf_context = extract_pdf_pages(pdf_path)
        if not pdf_context:
            errors.append(f"Failed to parse PDF: {pdf_path}")
            print(f"  ⚠️  Failed to parse PDF\n")
            continue

        print(f"  PDF: {pdf_context.total_pages} pages, {pdf_context.total_chars} chars")

        # audit each field
        for field in fields_to_audit:
            extracted_value = getattr(company, field, None)
            
            if args.dry_run:
                print(f"  [{field}] value={extracted_value} (dry-run, skipping LLM)")
                continue

            print(f"  Auditing {field}...", flush=True)

            result = None
            if args.level >= 1:
                result = audit_level_1(
                    company.company_name,
                    company.report_year,
                    field,
                    extracted_value,
                    pdf_context,
                    model=DEFAULT_L1_MODEL,
                )
            
            if result and args.level == 2 and result.verdict != "ok":
                print(f"    L1 flagged as {result.verdict}, running L2...")
                result = audit_level_2(
                    company.company_name,
                    company.report_year,
                    field,
                    extracted_value,
                    pdf_context,
                    level_1_result=result,
                    model=DEFAULT_L2_MODEL,
                )

            if result:
                audit_results.append(result)
                print(f"    ✓ {result.verdict} (confidence={result.confidence:.1%})")
            else:
                print(f"    ⚠️  Audit failed or timed out")

        print()

    # store results
    if not args.dry_run and audit_results:
        print(f"\n{'='*60}")
        print(f"Storing {len(audit_results)} audit results...")
        print(f"{'='*60}\n")

        try:
            from report_parser.audit_models import AuditQAResult, record_audit_result
            
            for res in audit_results:
                audit_record = AuditQAResult(
                    company_name=res.company_name,
                    report_year=res.report_year,
                    field=res.field,
                    extracted_value=str(res.extracted_value) if res.extracted_value is not None else None,
                    verdict=res.verdict,
                    confidence=res.confidence,
                    evidence_quote=res.evidence_quote,
                    evidence_page=res.evidence_page,
                    suggestion=res.suggestion,
                    audit_level=res.level,
                    audit_model=res.model,
                    doc_hash=res.doc_hash,
                )
                record_audit_result(db, audit_record)

            print(f"✓ {len(audit_results)} audit records stored (append-only).")
            
            # summary
            verdict_counts = {}
            for res in audit_results:
                verdict_counts[res.verdict] = verdict_counts.get(res.verdict, 0) + 1
            
            print("\nAudit summary:")
            for verdict, count in sorted(verdict_counts.items()):
                print(f"  {verdict}: {count}")

        except Exception as e:
            errors.append(f"Failed to store audit results: {e}")
            print(f"✗ Store failed: {e}")

    db.close()

    # print errors
    if errors:
        print(f"\n{'='*60}")
        print(f"Warnings/Errors ({len(errors)}):")
        print(f"{'='*60}")
        for err in errors:
            print(f"  ⚠️  {err}")

    print(f"\n{'='*60}")
    print(f"Audit complete. {len(audit_results)} verdicts recorded.")
    print("Next: Review pending audits in database, approve/reject, then writeback.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()

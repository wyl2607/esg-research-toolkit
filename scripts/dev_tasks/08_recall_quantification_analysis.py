"""Recall quantification analysis over mimo-channel audit rows.

Dedupes to the latest verdict per (company, report_year, field), then:
- NULL extracted values  -> recall lane: 'missing' = correctly null;
  any other verdict = candidate recall gap (model found a value in the PDF).
- Non-NULL extracted values -> precision cross-check vs. manual Stage 6 results.
Writes a markdown report to /tmp/esg-recall-report.md and prints it.
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core.database import SessionLocal  # noqa: E402
from report_parser.audit_models import AuditQAResult  # noqa: E402

db = SessionLocal()
rows = (
    db.query(AuditQAResult)
    .filter(AuditQAResult.audit_model.like("mimo%"))
    .order_by(AuditQAResult.id.asc())
    .all()
)

latest = {}
for r in rows:
    latest[(r.company_name, r.report_year, r.field)] = r
rows = list(latest.values())

null_rows = [r for r in rows if r.extracted_value in (None, "", "None")]
val_rows = [r for r in rows if r not in null_rows]

null_verdicts = Counter(r.verdict for r in null_rows)
val_verdicts = Counter(r.verdict for r in val_rows)

# recall gaps: null field but model found a value. In the null lane,
# 'ok' means the NULL is confirmed correct, so only 'incorrect' is a true
# gap; needs_review / context_mismatch go to a manual-triage list.
gaps = [r for r in null_rows if r.verdict == "incorrect"]
triage = [r for r in null_rows if r.verdict in ("needs_review", "context_mismatch")]
gaps_by_field = defaultdict(list)
for r in gaps:
    gaps_by_field[r.field].append(r)

n_null = len(null_rows)
n_correct_null = null_verdicts.get("missing", 0) + null_verdicts.get("ok", 0)

lines = []
lines.append("# Recall Quantification — mimo channel audit (2026-06-11)")
lines.append("")
lines.append(f"Deduped verdicts: {len(rows)} (companies: {len(set(r.company_name for r in rows))})")
lines.append("")
lines.append("## NULL-field lane (recall)")
lines.append("")
lines.append(f"- NULL extracted fields audited: {n_null}")
lines.append(f"- Confirmed correctly null ('missing' + 'ok'): {n_correct_null}")
lines.append(f"- True recall gaps ('incorrect': value exists in PDF): {len(gaps)}")
lines.append(f"- Manual triage (needs_review / context_mismatch): {len(triage)}")
if n_null:
    lines.append(f"- **Recall proxy (null fields correctly null): {n_correct_null/n_null:.1%}**")
lines.append("")
lines.append(f"Verdict breakdown (null fields): {dict(null_verdicts)}")
lines.append("")
lines.append("### Candidate recall gaps by field")
lines.append("")
for field, rs in sorted(gaps_by_field.items(), key=lambda kv: -len(kv[1])):
    lines.append(f"**{field}** ({len(rs)}):")
    for r in rs:
        sugg = (r.suggestion or "").replace("\n", " ")[:160]
        quote = (r.evidence_quote or "").replace("\n", " ")[:100]
        lines.append(
            f"- {r.company_name} {r.report_year} — verdict={r.verdict}, conf={r.confidence:.0%}, "
            f"page={r.evidence_page}; quote: {quote!r}; suggestion: {sugg}"
        )
    lines.append("")
lines.append("### Manual triage (needs_review / context_mismatch)")
lines.append("")
for r in triage:
    sugg = (r.suggestion or "").replace("\n", " ")[:160]
    lines.append(
        f"- {r.company_name} {r.report_year} {r.field} — verdict={r.verdict}, "
        f"conf={r.confidence:.0%}, page={r.evidence_page}; {sugg}"
    )
lines.append("")
lines.append("## Non-NULL lane (precision cross-check)")
lines.append("")
lines.append(f"- Non-null fields audited: {len(val_rows)}")
lines.append(f"- Verdict breakdown: {dict(val_verdicts)}")
incorrect = [r for r in val_rows if r.verdict == "incorrect"]
lines.append("")
lines.append(f"### 'incorrect' rows to triage ({len(incorrect)})")
for r in incorrect:
    sugg = (r.suggestion or "").replace("\n", " ")[:160]
    lines.append(
        f"- {r.company_name} {r.report_year} {r.field}: stored={r.extracted_value}, "
        f"conf={r.confidence:.0%}, page={r.evidence_page}; {sugg}"
    )

report = "\n".join(lines)
with open("runtime/qa/recall-quantification-20260611.md", "w") as f:
    f.write(report + "\n")
print(report)

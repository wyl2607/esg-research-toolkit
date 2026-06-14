"""Recall-gap writeback: apply human-reviewed corrections from the 2026-06-11
mimo audit (48 NULL-lane 'incorrect' verdicts) to company_reports.

Default is --dry-run (no writes). --apply commits, in one session:
  - audit_qa_results: human_review='approved' + corrected_value/rationale,
    or human_review='rejected' + review_notes
  - company_reports: the corrected field value (+ scope2_basis where relevant)

Decisions below reflect the human review of
docs/audits/recall-quantification-2026-06-11.md under the analyzer schema rules
(female_pct = total-workforce only; taxonomy = aligned only, no derived value;
scope2 canonically market-based with scope2_basis). 40 applied, 8 rejected.

Reproduce:
    OPENAI_API_KEY=dummy .venv/bin/python scripts/dev_tasks/09_recall_writeback.py
    OPENAI_API_KEY=dummy .venv/bin/python scripts/dev_tasks/09_recall_writeback.py --apply
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core.database import SessionLocal  # noqa: E402
from report_parser.audit_models import (  # noqa: E402
    AuditQAResult,
    approve_correction,
    reject_audit,
)
from report_parser.storage import CompanyReport  # noqa: E402

REVIEWER = "helena (Claude-assisted recall writeback, 2026-06-14)"

# (field, company_name, year) -> value  [+ optional scope2 basis]
APPLY: dict[tuple[str, str, int], float] = {
    # taxonomy_aligned_revenue_pct (directly disclosed taxonomy-ALIGNED share, %)
    ("taxonomy_aligned_revenue_pct", "BASF SE", 2024): 1.2,
    ("taxonomy_aligned_revenue_pct", "BASF SE", 2023): 1.6,
    ("taxonomy_aligned_revenue_pct", "BASF SE", 2022): 0.4,
    ("taxonomy_aligned_revenue_pct", "BMW AG", 2024): 14.6,
    ("taxonomy_aligned_revenue_pct", "BMW AG", 2023): 15.2,
    ("taxonomy_aligned_revenue_pct", "BMW AG", 2022): 11.0,
    ("taxonomy_aligned_revenue_pct", "EnBW Energie Baden-Württemberg AG", 2024): 21.8,
    ("taxonomy_aligned_revenue_pct", "Heidelberg Materials AG", 2024): 1.1,
    ("taxonomy_aligned_revenue_pct", "DHL Group", 2024): 13.8,
    ("taxonomy_aligned_revenue_pct", "Porsche AG", 2024): 12.1,
    ("taxonomy_aligned_revenue_pct", "Deutsche Telekom AG", 2024): 0.5,
    ("taxonomy_aligned_revenue_pct", "Volkswagen AG", 2022): 9.4,
    ("taxonomy_aligned_revenue_pct", "Volkswagen AG", 2024): 7.4,
    # energy_consumption_mwh (normalized to MWh)
    ("energy_consumption_mwh", "SAP SE", 2022): 906_000.0,          # 906 GWh
    ("energy_consumption_mwh", "BASF SE", 2024): 75_600_000.0,      # 75.6 million MWh
    ("energy_consumption_mwh", "BASF SE", 2023): 32_100_000.0,      # 32.1 million MWh
    ("energy_consumption_mwh", "BMW AG", 2024): 6_205_004.0,
    ("energy_consumption_mwh", "Merck KGaA, Darmstadt, Germany", 2024): 2_394_720.0,
    ("energy_consumption_mwh", "Deutsche Telekom AG", 2024): 11_925_733.0,  # 2024 col
    ("energy_consumption_mwh", "PUMA SE", 2024): 123_923.0,
    ("energy_consumption_mwh", "thyssenkrupp AG", 2024): 69_000_000.0,      # ~69 TWh
    ("energy_consumption_mwh", "RWE AG", 2024): 183_521_636.0,
    # water_usage_m3 (normalized to m3)
    ("water_usage_m3", "SAP SE", 2024): 682_000.0,                 # 682 thousand m3
    ("water_usage_m3", "BASF SE", 2024): 7_102_000_000.0,          # 7,102 million m3
    ("water_usage_m3", "Porsche AG", 2024): 162_722.0,
    ("water_usage_m3", "PUMA SE", 2024): 123_523.0,                # total consumption
    ("water_usage_m3", "Salzgitter AG", 2024): 7_243_000.0,        # 7,243 Tm3
    ("water_usage_m3", "Uniper SE", 2024): 19_946_640.0,
    # female_pct (total-workforce share, %)
    ("female_pct", "SAP SE", 2024): 35.4,
    ("female_pct", "SAP SE", 2023): 35.2,
    ("female_pct", "PUMA SE", 2024): 50.0,
    # scope3_co2e_tonnes (total Scope 3, tonnes)
    ("scope3_co2e_tonnes", "SAP SE", 2023): 7_000_000.0,
    ("scope3_co2e_tonnes", "BASF SE", 2024): 92_000_000.0,
    ("scope3_co2e_tonnes", "Deutsche Telekom AG", 2024): 10_100_000.0,
    ("scope3_co2e_tonnes", "Uniper SE", 2024): 65_494_989.0,
    # scope1_co2e_tonnes (group-consolidated, tonnes)
    ("scope1_co2e_tonnes", "PUMA SE", 2024): 5_950.0,
    ("scope1_co2e_tonnes", "RWE AG", 2024): 53_242_042.0,
    # waste_recycled_pct (100 - non-recycled 96.7)
    ("waste_recycled_pct", "RWE AG", 2024): 3.3,
}

# scope2 market-based writebacks also set scope2_basis
SCOPE2_BASIS: dict[tuple[str, str, int], str] = {
    ("scope2_co2e_tonnes", "Munich Re", 2024): "market",
    ("scope2_co2e_tonnes", "Deutsche Telekom AG", 2024): "market",
}
APPLY[("scope2_co2e_tonnes", "Munich Re", 2024)] = 112_657.0
APPLY[("scope2_co2e_tonnes", "Deutsche Telekom AG", 2024)] = 16_212.0

# (field, company_name, year) -> reject reason (schema-rule or quality exclusion)
REJECT: dict[tuple[str, str, int], str] = {
    ("taxonomy_aligned_revenue_pct", "RWE AG", 2022):
        "derived ~28.4% reverse-computed from numerator/denominator, not a directly disclosed aligned figure",
    ("female_pct", "Heidelberg Materials AG", 2024):
        "18% is leadership-position share, not total workforce (schema: female_pct = total workforce only)",
    ("female_pct", "Deutsche Telekom AG", 2023):
        "27.9% is middle/upper management share, not total workforce",
    ("female_pct", "RWE AG", 2023):
        "23.1% is leadership-position share, not total workforce",
    ("water_usage_m3", "DHL Group", 2024):
        "disclosed as 'Not material' — non-numeric, cannot store a float",
    ("water_usage_m3", "RWE AG", 2024):
        "476.6M m3 is opencast-lignite-mine freshwater input, not group total water usage",
    ("scope3_co2e_tonnes", "PUMA SE", 2024):
        "1,445,497 is Cat1+Cat4 only, not total Scope 3",
    ("scope2_co2e_tonnes", "Heidelberg Materials AG", 2024):
        "4.44M derived by summing business-line shares; quote is a '54% share', not a clean disclosed figure",
}


def load_gaps(db):
    rows = (
        db.query(AuditQAResult)
        .filter(AuditQAResult.audit_model.like("mimo%"))
        .order_by(AuditQAResult.id.asc())
        .all()
    )
    latest = {}
    for r in rows:
        latest[(r.company_name, r.report_year, r.field)] = r
    return [
        r
        for r in latest.values()
        if r.extracted_value in (None, "", "None") and r.verdict == "incorrect"
    ]


def find_report(db, company_name, year):
    matches = (
        db.query(CompanyReport)
        .filter(CompanyReport.company_name == company_name, CompanyReport.report_year == year)
        .all()
    )
    return matches


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="commit changes (default: dry-run)")
    args = ap.parse_args()

    db = SessionLocal()
    gaps = load_gaps(db)

    # validate decision coverage before touching anything
    gap_keys = {(g.field, g.company_name, g.report_year) for g in gaps}
    decided = set(APPLY) | set(REJECT)
    missing = gap_keys - decided
    extra = decided - gap_keys
    overlap = set(APPLY) & set(REJECT)
    if missing or extra or overlap:
        print("DECISION MAP MISMATCH — aborting, no writes.")
        for k in sorted(missing):
            print(f"  no decision for gap: {k}")
        for k in sorted(extra):
            print(f"  decision for non-gap: {k}")
        for k in sorted(overlap):
            print(f"  in both APPLY and REJECT: {k}")
        sys.exit(1)

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"=== Recall-gap writeback [{mode}] — {len(gaps)} gaps "
          f"({len(APPLY)} apply, {len(REJECT)} reject) ===\n")

    applied = rejected = errors = 0
    for g in sorted(gaps, key=lambda x: (x.field, x.company_name, x.report_year)):
        key = (g.field, g.company_name, g.report_year)
        reports = find_report(db, g.company_name, g.report_year)
        if len(reports) != 1:
            print(f"  !! {key}: expected 1 company_reports row, found {len(reports)} — SKIP")
            errors += 1
            continue
        report = reports[0]

        if key in APPLY:
            value = APPLY[key]
            current = getattr(report, g.field)
            basis = SCOPE2_BASIS.get(key)

            # This lane only FILLS genuine NULLs. A non-null current means the
            # gap was independently closed by re-extraction; never overwrite or
            # degrade it — retain the stored value and just mark the audit row.
            if current is None:
                tag, stored = "fill   ", value
                note = f"recall audit 2026-06-11 (mimo) p.{g.evidence_page} conf {g.confidence}"
            else:
                stored = current
                # flag material disagreements (>1%) for the precision-triage lane
                try:
                    rel = abs(float(current) - float(value)) / abs(float(value)) if value else 0.0
                except (TypeError, ValueError):
                    rel = 0.0
                if rel > 0.01:
                    tag = "confirm*"  # closed by re-extraction, value differs from audit
                    note = (f"recall gap closed by re-extraction; stored {current} retained "
                            f"(audit suggested {value}, differs {rel*100:.1f}% — defer to precision triage)")
                else:
                    tag = "confirm "
                    note = f"recall gap closed by re-extraction; stored {current} retained"

            basis_str = ""
            set_basis = basis and report.scope2_basis is None
            if set_basis:
                basis_str = f"  +scope2_basis={basis}"
            print(f"  [{tag}] {g.field:<28} {g.company_name} {g.report_year}: "
                  f"{current} -> {stored}{basis_str}")
            if args.apply:
                if current is None:
                    setattr(report, g.field, value)
                if set_basis:
                    report.scope2_basis = basis
                approve_correction(db, g.id, str(stored), rationale=note, reviewer=REVIEWER)
            applied += 1
        else:
            reason = REJECT[key]
            print(f"  [reject] {g.field:<28} {g.company_name} {g.report_year}: {reason}")
            if args.apply:
                reject_audit(db, g.id, reason, reviewer=REVIEWER)
            rejected += 1

    print(f"\nSummary: {applied} applied, {rejected} rejected, {errors} errors.")
    if not args.apply:
        print("Dry-run only — no database changes. Re-run with --apply to commit.")
    else:
        print("Committed. Next: re-run offline verifier, then sync to VPS (with approval).")


if __name__ == "__main__":
    main()

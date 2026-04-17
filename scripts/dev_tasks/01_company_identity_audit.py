#!/usr/bin/env python3
"""Audit company_name duplicates / near-duplicates in the analysis_results table.

Finds cases like:
  - "SAP" vs "SAP SE"
  - "Volkswagen Group" vs "Volkswagen AG"
  - "Deutsche Telekom" vs "Deutsche Telekom AG"

These split multi-year trend data across two identity rows, limiting the
number of companies that can show a meaningful 2022-2024 line.

Output: docs/dev-tasks/01_identity_merge_proposals.md
This script is READ-ONLY. It does not modify the database.

Usage:
  OPENAI_API_KEY=dummy .venv/bin/python scripts/dev_tasks/01_company_identity_audit.py
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

# Ensure project root on path so we can import `core`
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from core.config import settings
from report_parser.storage import CompanyReport
from report_parser.company_identity import canonical_company_name


REPORT_PATH = PROJECT_ROOT / "docs" / "dev-tasks" / "01_identity_merge_proposals.md"
SIMILARITY_THRESHOLD = 0.78  # tune: 0.78 catches "SAP" vs "SAP SE" but not "BASF" vs "BMW"


def normalize(name: str) -> str:
    """Strip common legal suffixes for comparison."""
    lowered = name.lower().strip()
    for suffix in [" se", " ag", " gmbh", " group", " plc", " n.v.", " sa"]:
        if lowered.endswith(suffix):
            lowered = lowered[: -len(suffix)].strip()
    return lowered


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def main() -> int:
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    rows = (
        session.query(
            CompanyReport.company_name,
            func.count(CompanyReport.id).label("n_reports"),
            func.group_concat(CompanyReport.report_year).label("years"),
        )
        .group_by(CompanyReport.company_name)
        .all()
    )

    names = [(r.company_name, r.n_reports, r.years) for r in rows]
    print(f"Loaded {len(names)} unique company_name values from DB.\n")

    # Group near-duplicates. We report two kinds of clusters:
    #   A) names that ALREADY collapse to the same canonical via
    #      canonical_company_name() — means _KNOWN_CANONICAL_NAMES is doing its
    #      job at the logic layer, but the DB still has split rows that
    #      need backfill.
    #   B) names that are similar but do NOT collapse — need new entries
    #      added to _KNOWN_CANONICAL_NAMES (or a proper alias table).
    clusters_known: dict[str, list[tuple[str, int, str]]] = {}
    for name, n, years in names:
        canonical = canonical_company_name(name)
        if canonical != name or sum(1 for other, *_ in names if canonical_company_name(other) == canonical) > 1:
            clusters_known.setdefault(canonical, []).append((name, n, years))
    # Drop singletons from the "known" bucket — no merge needed
    clusters_known = {k: v for k, v in clusters_known.items() if len(v) > 1}

    clusters_fuzzy: list[list[tuple[str, int, str]]] = []
    already_in_known = {name for group in clusters_known.values() for name, *_ in group}
    seen: set[str] = set(already_in_known)

    for i, (name_a, n_a, years_a) in enumerate(names):
        if name_a in seen:
            continue
        cluster = [(name_a, n_a, years_a)]
        seen.add(name_a)
        for name_b, n_b, years_b in names[i + 1 :]:
            if name_b in seen:
                continue
            if similarity(name_a, name_b) >= SIMILARITY_THRESHOLD:
                cluster.append((name_b, n_b, years_b))
                seen.add(name_b)
        if len(cluster) > 1:
            clusters_fuzzy.append(cluster)

    clusters = list(clusters_known.values()) + clusters_fuzzy

    # Write report
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as f:
        f.write("# Company Identity Merge Proposals\n\n")
        f.write(f"**Generated**: by `scripts/dev_tasks/01_company_identity_audit.py`\n")
        f.write(f"**DB**: `{settings.database_url}`\n")
        f.write(f"**Similarity threshold**: {SIMILARITY_THRESHOLD}\n")
        f.write(f"**Unique company names in DB**: {len(names)}\n")
        f.write(f"**Near-duplicate clusters**: {len(clusters)}\n\n")

        if not clusters:
            f.write("_No near-duplicate company names found._ 🎉\n")
            print("✅ No near-duplicate company names found.")
            return 0

        if clusters_known:
            f.write("## A. Already handled by `_KNOWN_CANONICAL_NAMES` (DB needs backfill)\n\n")
            f.write("These clusters map to the same canonical name via `canonical_company_name()`, ")
            f.write("so the logic layer is correct — but legacy DB rows still have divergent `company_name` ")
            f.write("values. A one-off UPDATE migration should rename them to the canonical.\n\n")
            for idx, (canonical_name, cluster) in enumerate(clusters_known.items(), start=1):
                f.write(f"### A{idx}: canonical = `{canonical_name}`\n\n")
                f.write("| DB name | Reports | Years |\n|---|---|---|\n")
                for name, n, years in sorted(cluster, key=lambda r: -r[1]):
                    f.write(f"| `{name}` | {n} | `{years}` |\n")
                f.write("\n")

        if clusters_fuzzy:
            f.write("## B. Fuzzy-match candidates (need new alias entries)\n\n")
            f.write("These are **not** yet canonicalized. Review each cluster and either:\n")
            f.write("- add aliases to `_KNOWN_CANONICAL_NAMES` in `report_parser/company_identity.py`, **or**\n")
            f.write("- confirm they are genuinely different entities and ignore.\n\n")
            for idx, cluster in enumerate(clusters_fuzzy, start=1):
                f.write(f"### B{idx}\n\n")
                f.write("| Current name | Reports | Years |\n|---|---|---|\n")
                for name, n, years in sorted(cluster, key=lambda r: -r[1]):
                    f.write(f"| `{name}` | {n} | `{years}` |\n")
                suggested = max(cluster, key=lambda r: (r[1], len(r[0]), r[0]))
                f.write(f"\n**Suggested canonical**: `{suggested[0]}`\n\n")

        f.write("## Next Steps\n\n")
        f.write("1. Review each cluster above and confirm the canonical name is correct.\n")
        f.write("2. Add aliases to `company_identity.py` (or the equivalent lookup).\n")
        f.write("3. Backfill existing DB rows via a one-off migration script OR re-run the seed pipeline.\n")
        f.write("4. Re-run this audit script to verify clusters are resolved.\n")

    print(f"Report written: {REPORT_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Clusters found: {len(clusters)}")
    for idx, cluster in enumerate(clusters, start=1):
        names_list = ", ".join(f'"{r[0]}"' for r in cluster)
        print(f"  #{idx}: {names_list}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

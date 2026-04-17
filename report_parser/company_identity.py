from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from typing import Any


_KNOWN_CANONICAL_NAMES: dict[str, str] = {
    "bmw group": "BMW AG",
    "bmw ag": "BMW AG",
    "catl": "Contemporary Amperex Technology Co., Limited",
    "contemporary amperex technology co limited": "Contemporary Amperex Technology Co., Limited",
    "contemporary amperex technology co ltd": "Contemporary Amperex Technology Co., Limited",
    "contemporary amperex technology co., limited": "Contemporary Amperex Technology Co., Limited",
    "contemporary amperex technology co., ltd.": "Contemporary Amperex Technology Co., Limited",
    "byd": "BYD Company Limited",
    "byd company limited": "BYD Company Limited",
    "byd company ltd": "BYD Company Limited",
    "deutsche telekom": "Deutsche Telekom AG",
    "deutsche telekom ag": "Deutsche Telekom AG",
    "fresenius": "Fresenius SE & Co. KGaA",
    "fresenius se co kgaa": "Fresenius SE & Co. KGaA",
    "linde": "Linde plc",
    "linde plc": "Linde plc",
    "puma": "PUMA SE",
    "puma se": "PUMA SE",
    "rwe": "RWE AG",
    "rwe ag": "RWE AG",
    "sap": "SAP SE",
    "sap se": "SAP SE",
    "thyssenkrupp": "thyssenkrupp AG",
    "thyssenkrupp ag": "thyssenkrupp AG",
    "volkswagen": "Volkswagen AG",
    "volkswagen ag": "Volkswagen AG",
    "volkswagen group": "Volkswagen AG",
    "basf": "BASF SE",
    "basf se": "BASF SE",
    "siemens": "Siemens AG",
    "siemens ag": "Siemens AG",
}

_DOCUMENT_PRIORITY: dict[str, int] = {
    "annual_report": 600,
    "annual_sustainability_report": 540,
    "sustainability_report": 500,
    "manual_case": 400,
    "filing": 320,
    "announcement": 260,
    "event": 200,
}


def _normalize_key(name: str) -> str:
    compact = re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()
    return re.sub(r"\s+", " ", compact)


def canonical_company_name(name: str) -> str:
    trimmed = name.strip()
    if not trimmed:
        return trimmed
    return _KNOWN_CANONICAL_NAMES.get(_normalize_key(trimmed), trimmed)


def company_name_variants(name: str) -> set[str]:
    canonical = canonical_company_name(name)
    canonical_key = _normalize_key(canonical)
    variants = {canonical}
    for raw, mapped in _KNOWN_CANONICAL_NAMES.items():
        if _normalize_key(mapped) == canonical_key:
            variants.add(raw)
    return variants


def company_names_match(left: str, right: str) -> bool:
    return canonical_company_name(left) == canonical_company_name(right)


def report_quality_score(record: Any) -> tuple[int, int, int, str]:
    metric_fields = (
        "scope1_co2e_tonnes",
        "scope2_co2e_tonnes",
        "scope3_co2e_tonnes",
        "energy_consumption_mwh",
        "renewable_energy_pct",
        "water_usage_m3",
        "waste_recycled_pct",
        "taxonomy_aligned_revenue_pct",
        "taxonomy_aligned_capex_pct",
        "total_employees",
        "female_pct",
    )
    filled_metrics = sum(1 for field in metric_fields if getattr(record, field, None) is not None)
    evidence_len = 0
    evidence_summary = getattr(record, "evidence_summary", None)
    if isinstance(evidence_summary, str) and evidence_summary.strip():
        evidence_len = evidence_summary.count('"metric"')
    priority = _DOCUMENT_PRIORITY.get(getattr(record, "source_document_type", None) or "", 0)
    updated_at = getattr(record, "updated_at", None)
    updated_key = updated_at.isoformat() if updated_at else ""
    return (priority, filled_metrics, evidence_len, updated_key)


def collapse_company_records(records: Iterable[Any]) -> list[Any]:
    grouped: dict[tuple[str, int], list[Any]] = defaultdict(list)
    for record in records:
        canonical = canonical_company_name(getattr(record, "company_name", ""))
        grouped[(canonical, getattr(record, "report_year", 0))].append(record)

    collapsed: list[Any] = []
    for (_, _), candidates in grouped.items():
        best = max(candidates, key=report_quality_score)
        best.company_name = canonical_company_name(best.company_name)
        collapsed.append(best)

    collapsed.sort(key=lambda item: (canonical_company_name(item.company_name).lower(), item.report_year))
    return collapsed

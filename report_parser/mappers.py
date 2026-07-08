"""Shared record→payload field mapping.

The 20-odd scalar metric columns of a CompanyReport row are mapped
field-by-field in several places (profile responses, merge inputs,
disclosure merge previews). This module holds the single source of truth
for that mapping so a new metric column only needs to be added once.

Callers layer their own semantics for the non-scalar fields
(primary_activities, evidence_summary), which intentionally differ per
call site.
"""
from __future__ import annotations

from typing import Any


def record_scalar_fields(record: Any) -> dict[str, Any]:
    """Return the shared scalar columns of a CompanyReport-like row."""
    return {
        "company_name": record.company_name,
        "report_year": record.report_year,
        "reporting_period_label": record.reporting_period_label,
        "reporting_period_type": record.reporting_period_type,
        "source_document_type": record.source_document_type,
        "industry_code": record.industry_code,
        "industry_sector": record.industry_sector,
        "scope1_co2e_tonnes": record.scope1_co2e_tonnes,
        "scope2_co2e_tonnes": record.scope2_co2e_tonnes,
        "scope2_basis": record.scope2_basis,
        "scope3_co2e_tonnes": record.scope3_co2e_tonnes,
        "energy_consumption_mwh": record.energy_consumption_mwh,
        "renewable_energy_pct": record.renewable_energy_pct,
        "water_usage_m3": record.water_usage_m3,
        "waste_recycled_pct": record.waste_recycled_pct,
        "total_revenue_eur": record.total_revenue_eur,
        "taxonomy_aligned_revenue_pct": record.taxonomy_aligned_revenue_pct,
        "total_capex_eur": record.total_capex_eur,
        "taxonomy_aligned_capex_pct": record.taxonomy_aligned_capex_pct,
        "total_employees": record.total_employees,
        "female_pct": record.female_pct,
    }

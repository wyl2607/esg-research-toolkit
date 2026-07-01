import json

from core.schemas import CompanyESGData

_SCALAR_FIELDS = (
    "company_name", "report_year", "reporting_period_label", "reporting_period_type",
    "source_document_type", "industry_code", "industry_sector",
    "scope1_co2e_tonnes", "scope2_co2e_tonnes", "scope2_basis", "scope3_co2e_tonnes",
    "energy_consumption_mwh", "renewable_energy_pct", "water_usage_m3", "waste_recycled_pct",
    "total_revenue_eur", "taxonomy_aligned_revenue_pct", "total_capex_eur",
    "taxonomy_aligned_capex_pct", "total_employees", "female_pct",
)


def record_to_company_esg_data(record) -> CompanyESGData:
    # tolerate partial records (taxonomy callers pass lightweight objects)
    payload = {f: getattr(record, f, None) for f in _SCALAR_FIELDS}
    payload = {k: v for k, v in payload.items() if v is not None}
    for json_field in ("primary_activities", "evidence_summary"):
        raw = getattr(record, json_field, None)
        if raw is None:
            payload[json_field] = []
        elif isinstance(raw, str):
            try:
                payload[json_field] = json.loads(raw) if raw else []
            except json.JSONDecodeError:
                payload[json_field] = []
        else:
            payload[json_field] = raw
    return CompanyESGData.model_validate(payload)

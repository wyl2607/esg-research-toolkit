from __future__ import annotations

import json

from scripts.audit_extractions import (
    AUDIT_FIELDS,
    CompanyAuditResult,
    FieldAudit,
    build_prompt,
    parse_audit_response,
)


def test_build_prompt_includes_all_fields_and_forces_quote() -> None:
    prompt = build_prompt(
        company_name="RWE AG",
        report_year=2024,
        industry_sector="Electricity production",
        extracted={"scope1_co2e_tonnes": 52600000},
        source_text="Scope 1 emissions totalled 52.6 Mt CO2e in 2024.",
    )
    assert "VERBATIM" in prompt
    assert "RWE AG" in prompt
    for field_name in AUDIT_FIELDS:
        assert field_name in prompt
    assert "52600000" in prompt


def test_parse_audit_response_builds_field_audits() -> None:
    raw = json.dumps(
        {
            "scope1_co2e_tonnes": {
                "current_value": 52600000,
                "verdict": "correct",
                "corrected_value": None,
                "source_page_hint": 64,
                "evidence_quote": "Scope 1 emissions totalled 52.6 Mt CO2e.",
                "confidence": "high",
                "reason": "Matches report",
            },
            "scope2_co2e_tonnes": {
                "current_value": None,
                "verdict": "missed",
                "corrected_value": 1230000,
                "source_page_hint": 65,
                "evidence_quote": "Scope 2 (market-based) emissions were 1.23 Mt CO2e.",
                "confidence": "high",
                "reason": "Explicitly disclosed",
            },
        }
    )
    fields = parse_audit_response(raw, {"scope1_co2e_tonnes": 52600000})
    by_name = {field_result.field: field_result for field_result in fields}
    assert by_name["scope1_co2e_tonnes"].verdict == "correct"
    assert by_name["scope2_co2e_tonnes"].verdict == "missed"
    assert by_name["scope2_co2e_tonnes"].corrected_value == 1230000
    assert by_name["scope2_co2e_tonnes"].confidence == "high"


def test_corrections_to_apply_filters_by_confidence() -> None:
    result = CompanyAuditResult(
        slug="rwe-2024",
        company_name="RWE AG",
        report_year=2024,
        fields=[
            FieldAudit(
                field="scope2_co2e_tonnes",
                current_value=None,
                verdict="missed",
                corrected_value=1230000,
                source_page_hint=65,
                evidence_quote="quote",
                confidence="high",
                reason="",
            ),
            FieldAudit(
                field="scope3_co2e_tonnes",
                current_value=None,
                verdict="missed",
                corrected_value=99999999,
                source_page_hint=None,
                evidence_quote=None,
                confidence="low",
                reason="guess",
            ),
        ],
    )
    to_apply = result.corrections_to_apply()
    assert to_apply == {"scope2_co2e_tonnes": 1230000}

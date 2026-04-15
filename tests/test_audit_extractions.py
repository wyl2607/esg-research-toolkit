from __future__ import annotations

import json
import sys
import time
import types
from pathlib import Path

from scripts.audit_extractions import (
    AUDIT_FIELDS,
    CompanyAuditResult,
    FieldAudit,
    ROOT,
    SUMMARY_PATH,
    build_prompt,
    fetch_company_profile,
    main,
    parse_audit_response,
)
from scripts.seed_german_demo import SeedCompany


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


def test_parse_audit_response_accepts_fenced_json() -> None:
    raw = """Audit result:
```json
{
  "scope1_co2e_tonnes": {
    "verdict": "correct",
    "confidence": "high",
    "evidence_quote": "Scope 1 emissions totalled 52.6 Mt CO2e."
  }
}
```
"""
    fields = parse_audit_response(raw, {"scope1_co2e_tonnes": 52600000})
    by_name = {field_result.field: field_result for field_result in fields}
    assert by_name["scope1_co2e_tonnes"].verdict == "correct"
    assert by_name["scope1_co2e_tonnes"].confidence == "high"


def test_parse_audit_response_accepts_json_embedded_in_text() -> None:
    raw = (
        "Here is the object you asked for:\n"
        '{"scope2_co2e_tonnes":{"verdict":"missed","corrected_value":123.0,"confidence":"medium"}}\n'
        "done."
    )
    fields = parse_audit_response(raw, {"scope2_co2e_tonnes": None})
    by_name = {field_result.field: field_result for field_result in fields}
    assert by_name["scope2_co2e_tonnes"].verdict == "missed"
    assert by_name["scope2_co2e_tonnes"].corrected_value == 123.0
    assert by_name["scope2_co2e_tonnes"].confidence == "medium"


def test_parse_audit_response_prefers_payload_with_audit_fields() -> None:
    raw = (
        'prefix {"meta":{"note":"irrelevant"}} middle '
        '{"scope1_co2e_tonnes":{"verdict":"incorrect","corrected_value":42,"confidence":"high"}} suffix'
    )
    fields = parse_audit_response(raw, {"scope1_co2e_tonnes": 41})
    by_name = {field_result.field: field_result for field_result in fields}
    assert by_name["scope1_co2e_tonnes"].verdict == "incorrect"
    assert by_name["scope1_co2e_tonnes"].corrected_value == 42.0


def test_parse_audit_response_rejects_json_without_audit_fields() -> None:
    raw = '{"meta":{"message":"ok"}}'
    try:
        parse_audit_response(raw, {})
    except ValueError as exc:
        assert "expected audit fields" in str(exc)
    else:
        raise AssertionError("expected ValueError for payload without audit fields")


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


def test_fetch_company_profile_falls_back_to_normalized_name(monkeypatch) -> None:
    class DummyResponse:
        def __init__(self, status_code: int, payload):
            self.status_code = status_code
            self._payload = payload

        def json(self):
            return self._payload

    class DummyClient:
        def __init__(self, *args, **kwargs) -> None:
            self.calls: list[str] = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def get(self, url: str) -> DummyResponse:
            self.calls.append(url)
            if url.endswith("/report/companies/RWE%20AG/profile"):
                return DummyResponse(404, {"detail": "not found"})
            if url.endswith("/report/companies"):
                return DummyResponse(
                    200,
                    [
                        {"company_name": "RWE", "report_year": 2024},
                        {"company_name": "BASF SE", "report_year": 2024},
                    ],
                )
            if url.endswith("/report/companies/RWE/profile"):
                return DummyResponse(
                    200,
                    {"latest_metrics": {"scope1_co2e_tonnes": 123.0}},
                )
            raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr("scripts.audit_extractions.httpx.Client", DummyClient)
    profile, resolved_name = fetch_company_profile(
        "http://localhost:8000",
        "RWE AG",
        report_year=2024,
    )
    assert resolved_name == "RWE"
    assert profile and profile["latest_metrics"]["scope1_co2e_tonnes"] == 123.0


def test_fetch_company_profile_uses_prefetched_directory(monkeypatch) -> None:
    class DummyResponse:
        def __init__(self, status_code: int, payload):
            self.status_code = status_code
            self._payload = payload

        def json(self):
            return self._payload

    class DummyClient:
        def __init__(self, *args, **kwargs) -> None:
            self.calls: list[str] = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def get(self, url: str) -> DummyResponse:
            self.calls.append(url)
            if url.endswith("/report/companies/RWE%20AG/profile"):
                return DummyResponse(404, {"detail": "not found"})
            if url.endswith("/report/companies/RWE/profile"):
                return DummyResponse(200, {"latest_metrics": {"scope1_co2e_tonnes": 321.0}})
            if url.endswith("/report/companies"):
                raise AssertionError("/report/companies should not be fetched when preloaded data is provided")
            raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr("scripts.audit_extractions.httpx.Client", DummyClient)
    profile, resolved_name = fetch_company_profile(
        "http://localhost:8000",
        "RWE AG",
        report_year=2024,
        company_directory=[{"company_name": "RWE", "report_year": 2024}],
    )
    assert resolved_name == "RWE"
    assert profile and profile["latest_metrics"]["scope1_co2e_tonnes"] == 321.0


def test_fetch_company_profile_resolves_kgaa_suffix(monkeypatch) -> None:
    class DummyResponse:
        def __init__(self, status_code: int, payload):
            self.status_code = status_code
            self._payload = payload

        def json(self):
            return self._payload

    class DummyClient:
        def __init__(self, *args, **kwargs) -> None:
            self.calls: list[str] = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def get(self, url: str) -> DummyResponse:
            self.calls.append(url)
            if url.endswith("/report/companies/Fresenius%20SE%20%26%20Co.%20KGaA/profile"):
                return DummyResponse(404, {"detail": "not found"})
            if url.endswith("/report/companies/Fresenius/profile"):
                return DummyResponse(200, {"latest_metrics": {"scope1_co2e_tonnes": 111.0}})
            if url.endswith("/report/companies"):
                raise AssertionError("/report/companies should not be fetched when preloaded data is provided")
            raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr("scripts.audit_extractions.httpx.Client", DummyClient)
    profile, resolved_name = fetch_company_profile(
        "http://localhost:8000",
        "Fresenius SE & Co. KGaA",
        report_year=2024,
        company_directory=[{"company_name": "Fresenius", "report_year": 2024}],
    )
    assert resolved_name == "Fresenius"
    assert profile and profile["latest_metrics"]["scope1_co2e_tonnes"] == 111.0


def test_main_writes_reports_in_manifest_order_with_workers(monkeypatch) -> None:
    companies = [
        SeedCompany("a-2024", "Alpha AG", 2024, "D35.11", "Power", "https://example.com/a.pdf", False),
        SeedCompany("b-2024", "Beta AG", 2024, "D35.11", "Power", "https://example.com/b.pdf", False),
        SeedCompany("c-2024", "Gamma AG", 2024, "D35.11", "Power", "https://example.com/c.pdf", False),
    ]

    monkeypatch.setattr("scripts.audit_extractions.load_manifest", lambda: companies)

    def fake_audit_one(company: SeedCompany, **kwargs) -> CompanyAuditResult:
        if company.slug == "a-2024":
            time.sleep(0.05)
        return CompanyAuditResult(
            slug=company.slug,
            company_name=company.company_name,
            report_year=company.report_year,
            fields=[],
            error="dry-run",
        )

    write_order: list[str] = []

    def fake_write_company_report(result: CompanyAuditResult) -> Path:
        write_order.append(result.slug)
        return ROOT / "scripts" / "seed_data" / "audit_reports" / f"{result.slug}.md"

    monkeypatch.setattr("scripts.audit_extractions.audit_one", fake_audit_one)
    monkeypatch.setattr("scripts.audit_extractions.write_company_report", fake_write_company_report)
    monkeypatch.setattr("scripts.audit_extractions.write_summary", lambda results: SUMMARY_PATH)

    exit_code = main(["--dry-run", "--workers", "3"])

    assert exit_code == 0
    assert write_order == [company.slug for company in companies]


def test_main_keeps_company_directory_none_when_prefetch_fails(monkeypatch) -> None:
    companies = [SeedCompany("a-2024", "Alpha AG", 2024, "D35.11", "Power", "https://example.com/a.pdf", False)]
    monkeypatch.setattr("scripts.audit_extractions.load_manifest", lambda: companies)
    monkeypatch.setattr("scripts.audit_extractions.fetch_company_directory", lambda *_args, **_kwargs: None)

    class DummyOpenAI:
        def __init__(self, *args, **kwargs) -> None:
            pass

    captured: list[list[dict] | None] = []

    def fake_audit_one(company: SeedCompany, **kwargs) -> CompanyAuditResult:
        captured.append(kwargs.get("company_directory"))
        return CompanyAuditResult(
            slug=company.slug,
            company_name=company.company_name,
            report_year=company.report_year,
            fields=[],
            error="dry-run",
        )

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=DummyOpenAI))
    monkeypatch.setattr("scripts.audit_extractions.audit_one", fake_audit_one)
    monkeypatch.setattr("scripts.audit_extractions.write_company_report", lambda result: ROOT / f"{result.slug}.md")
    monkeypatch.setattr("scripts.audit_extractions.write_summary", lambda results: SUMMARY_PATH)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    exit_code = main([])

    assert exit_code == 0
    assert captured == [None]


def test_main_continues_when_audit_worker_raises(monkeypatch) -> None:
    companies = [
        SeedCompany("a-2024", "Alpha AG", 2024, "D35.11", "Power", "https://example.com/a.pdf", False),
        SeedCompany("b-2024", "Beta AG", 2024, "D35.11", "Power", "https://example.com/b.pdf", False),
    ]
    monkeypatch.setattr("scripts.audit_extractions.load_manifest", lambda: companies)

    def fake_audit_one(company: SeedCompany, **kwargs) -> CompanyAuditResult:
        if company.slug == "a-2024":
            raise RuntimeError("boom")
        return CompanyAuditResult(
            slug=company.slug,
            company_name=company.company_name,
            report_year=company.report_year,
            fields=[],
            error="dry-run",
        )

    errors: dict[str, str | None] = {}

    def fake_write_company_report(result: CompanyAuditResult) -> Path:
        errors[result.slug] = result.error
        return ROOT / "scripts" / "seed_data" / "audit_reports" / f"{result.slug}.md"

    monkeypatch.setattr("scripts.audit_extractions.audit_one", fake_audit_one)
    monkeypatch.setattr("scripts.audit_extractions.write_company_report", fake_write_company_report)
    monkeypatch.setattr("scripts.audit_extractions.write_summary", lambda results: SUMMARY_PATH)

    exit_code = main(["--dry-run", "--workers", "2"])

    assert "worker:" in (errors.get("a-2024") or "")
    assert errors.get("b-2024") == "dry-run"
    assert exit_code == 1

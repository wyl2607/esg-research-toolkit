from __future__ import annotations

import hashlib
import json
import sys
import time
import types
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.database import Base
from report_parser.storage import ExtractionRun
from scripts.audit_extractions import (
    AUDIT_FIELDS,
    CompanyAuditResult,
    FieldAudit,
    ROOT,
    SUMMARY_PATH,
    audit_one,
    build_prompt,
    fetch_company_profile,
    main,
    parse_audit_response,
    select_prompt_source_text,
)
from scripts.seed_german_demo import SeedCompany, phase_a


@pytest.fixture
def audit_trail_session_factory(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'audit-trail.db'}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    try:
        yield TestingSessionLocal, engine
    finally:
        Base.metadata.drop_all(bind=engine)


def test_build_prompt_includes_all_fields_and_forces_quote() -> None:
    prompt = build_prompt(
        company_name="RWE AG",
        report_year=2024,
        industry_sector="Electricity production",
        extracted={"scope1_co2e_tonnes": 52600000},
        source_text="Scope 1 emissions totalled 52.6 Mt CO2e in 2024.",
    )
    assert "VERBATIM" in prompt
    assert 'Do NOT use "incorrect" to mean "unverified"' in prompt
    assert "RWE AG" in prompt
    for field_name in AUDIT_FIELDS:
        assert field_name in prompt
    assert "52600000" in prompt


def test_select_prompt_source_text_prefers_later_relevant_chunk() -> None:
    source_text = "\n\n".join(
        [
            "Table of contents\nIntroduction ........ 3\nMetrics table ........ 42",
            "Chair letter and governance highlights with generic statements.",
            "Scope 1 emissions totalled 42 tonnes CO2e in 2024.",
            "Waste recycling rate was 80 percent in 2024.",
        ]
    )

    selected = select_prompt_source_text(
        source_text,
        max_chars=210,
        extracted={"scope1_co2e_tonnes": 42.0},
    )

    assert "Scope 1 emissions totalled 42 tonnes CO2e" in selected
    assert "Table of contents" not in selected
    assert len(selected) <= 210


def test_select_prompt_source_text_respects_max_chars_budget() -> None:
    source_text = "\n\n".join(
        [f"Scope 1 emissions were {i} tonnes CO2e in 2024. " * 8 for i in range(1, 30)]
    )
    selected = select_prompt_source_text(
        source_text,
        max_chars=220,
        extracted={"scope1_co2e_tonnes": 1.0},
    )

    assert len(selected) <= 220
    assert "truncated" in selected.lower()


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


def test_phase_a_records_extract_run_on_success(monkeypatch, tmp_path: Path, audit_trail_session_factory) -> None:
    testing_session_local, testing_engine = audit_trail_session_factory
    company = SeedCompany(
        "demo-2024",
        "Demo AG",
        2024,
        "D35.11",
        "Power",
        "https://example.com/demo.pdf",
        False,
    )
    pdf_bytes = b"%PDF-1.7\n" + (b"x" * 2048)
    pdf_path = tmp_path / "demo-2024.pdf"
    pdf_path.write_bytes(pdf_bytes)

    monkeypatch.setattr("scripts.seed_german_demo.SessionLocal", testing_session_local)
    monkeypatch.setattr("scripts.seed_german_demo.engine", testing_engine)
    monkeypatch.setattr("scripts.seed_german_demo.ensure_pdf", lambda *_args, **_kwargs: pdf_path)
    monkeypatch.setattr("scripts.seed_german_demo.already_seeded", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        "scripts.seed_german_demo.upload_company",
        lambda *_args, **_kwargs: {"company_name": "Demo Parsed AG", "report_year": 2024},
    )
    monkeypatch.setattr("scripts.seed_german_demo.trigger_recompute", lambda *_args, **_kwargs: {"ok": True})
    monkeypatch.setattr("scripts.seed_german_demo.settings.openai_model", "gpt-extract-test")

    summary = phase_a("http://localhost:8000", [company], dry_run=False, timeout=5)

    with testing_session_local() as db:
        rows = db.query(ExtractionRun).all()

    assert summary["succeeded"] == ["demo-2024"]
    assert len(rows) == 1
    assert rows[0].run_kind == "extract"
    assert rows[0].file_hash == hashlib.sha256(pdf_bytes).hexdigest()
    assert rows[0].model == "gpt-extract-test"
    assert rows[0].notes == "Seed extraction succeeded for Demo Parsed AG 2024 from demo-2024.pdf."
    assert "\n" not in (rows[0].notes or "")


def test_audit_one_records_audit_run_on_success(monkeypatch, tmp_path: Path, audit_trail_session_factory) -> None:
    testing_session_local, testing_engine = audit_trail_session_factory
    company = SeedCompany(
        "audit-demo-2024",
        "Audit Demo AG",
        2024,
        "D35.11",
        "Power",
        "https://example.com/audit-demo.pdf",
        False,
    )
    pdf_bytes = b"%PDF-1.7\n" + (b"y" * 2048)
    pdf_path = tmp_path / "audit-demo-2024.pdf"
    pdf_path.write_bytes(pdf_bytes)

    monkeypatch.setattr("scripts.audit_extractions.SessionLocal", testing_session_local)
    monkeypatch.setattr("scripts.audit_extractions.engine", testing_engine)
    monkeypatch.setattr("scripts.audit_extractions.PDF_CACHE_DIR", tmp_path)
    monkeypatch.setattr(
        "scripts.audit_extractions.fetch_company_profile",
        lambda *_args, **_kwargs: ({"latest_metrics": {"scope1_co2e_tonnes": 12.0}}, company.company_name),
    )
    monkeypatch.setattr(
        "scripts.audit_extractions.extract_text_from_pdf",
        lambda _path: "Scope 1 emissions totalled 12 tonnes CO2e in 2024.",
    )

    raw_response = json.dumps(
        {
            "scope1_co2e_tonnes": {
                "current_value": 12.0,
                "verdict": "correct",
                "corrected_value": None,
                "source_page_hint": 3,
                "evidence_quote": "Scope 1 emissions totalled 12 tonnes CO2e in 2024.",
                "confidence": "high",
                "reason": "Matches report",
            }
        }
    )

    class _DummyOpenAI:
        class chat:
            class completions:
                @staticmethod
                def create(**_kwargs):
                    return types.SimpleNamespace(
                        choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=raw_response))]
                    )

    result = audit_one(
        company,
        api_base="http://localhost:8000",
        model="gpt-audit-test",
        max_chars=5000,
        openai_client=_DummyOpenAI(),
        dry_run=False,
        company_directory=[{"company_name": company.company_name, "report_year": 2024}],
    )

    with testing_session_local() as db:
        rows = db.query(ExtractionRun).all()

    assert result.error is None
    assert len(rows) == 1
    assert rows[0].run_kind == "audit"
    assert rows[0].file_hash == hashlib.sha256(pdf_bytes).hexdigest()
    assert rows[0].model == "gpt-audit-test"
    assert rows[0].verdict == "ok"
    assert rows[0].notes == (
        "Audit completed for Audit Demo AG 2024: "
        f"1 correct, 0 incorrect, 0 missed, {len(AUDIT_FIELDS) - 1} not_disclosed."
    )
    assert "\n" not in (rows[0].notes or "")


def test_audit_one_prompt_uses_later_relevant_snippets(monkeypatch, tmp_path: Path) -> None:
    company = SeedCompany(
        "audit-context-2024",
        "Audit Context AG",
        2024,
        "D35.11",
        "Power",
        "https://example.com/audit-context.pdf",
        False,
    )
    pdf_path = tmp_path / "audit-context-2024.pdf"
    pdf_path.write_bytes(b"%PDF-1.7\n" + (b"z" * 2048))
    monkeypatch.setattr("scripts.audit_extractions.PDF_CACHE_DIR", tmp_path)
    monkeypatch.setattr(
        "scripts.audit_extractions.fetch_company_profile",
        lambda *_args, **_kwargs: ({"latest_metrics": {"scope1_co2e_tonnes": 42.0}}, company.company_name),
    )

    front_matter = ("Table of contents\nGovernance overview ........ 3\n" * 30).strip()
    relevant_later = "Scope 1 emissions totalled 42 tonnes CO2e in 2024."
    source_text = "\n\n".join(
        [
            front_matter,
            "Corporate profile and board composition.",
            relevant_later,
            "Water withdrawal was 3.1 million m3.",
        ]
    )
    monkeypatch.setattr("scripts.audit_extractions.extract_text_from_pdf", lambda _path: source_text)

    raw_response = json.dumps(
        {
            "scope1_co2e_tonnes": {
                "verdict": "correct",
                "confidence": "high",
                "evidence_quote": relevant_later,
            }
        }
    )

    class _DummyOpenAI:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    prompt = kwargs["messages"][0]["content"]
                    assert relevant_later in prompt
                    return types.SimpleNamespace(
                        choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=raw_response))]
                    )

    result = audit_one(
        company,
        api_base="http://localhost:8000",
        model="gpt-audit-test",
        max_chars=260,
        openai_client=_DummyOpenAI(),
        dry_run=False,
        company_directory=[{"company_name": company.company_name, "report_year": 2024}],
    )

    assert result.error is None


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


# ── ExtractionRun audit trail tests ──────────────────────────────────────────


def test_extraction_run_written_on_audit(monkeypatch, tmp_path) -> None:
    """After a successful audit_one call, an ExtractionRun row must be persisted."""
    import json as _json

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from core.database import Base
    from report_parser.storage import ExtractionRun
    from scripts.audit_extractions import audit_one

    # Build an isolated in-memory DB.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)

    monkeypatch.setattr("scripts.audit_extractions.SessionLocal", TestSession)
    monkeypatch.setattr("scripts.audit_extractions.engine", engine)

    # Stub the PDF so audit_one can find it and hash it.
    pdf_path = tmp_path / "rwe-2024.pdf"
    pdf_path.write_bytes(b"%PDF-1.7\n" + b"x" * 1024)
    monkeypatch.setattr("scripts.audit_extractions.PDF_CACHE_DIR", tmp_path)
    monkeypatch.setattr("scripts.audit_extractions.extract_text_from_pdf", lambda _path: "Scope 1 totalled 52.6 Mt.")

    # Stub fetch_company_profile to return a minimal profile.
    monkeypatch.setattr(
        "scripts.audit_extractions.fetch_company_profile",
        lambda *_args, **_kw: ({"latest_metrics": {"scope1_co2e_tonnes": 52600000.0}}, "RWE AG"),
    )

    # Stub OpenAI completion.
    raw_json = _json.dumps(
        {
            "scope1_co2e_tonnes": {
                "verdict": "correct",
                "confidence": "high",
                "evidence_quote": "Scope 1 totalled 52.6 Mt.",
            }
        }
    )

    class _FakeChoice:
        message = type("M", (), {"content": raw_json})()

    class _FakeCompletion:
        choices = [_FakeChoice()]

    class _FakeOpenAI:
        class chat:
            class completions:
                @staticmethod
                def create(**_kw):
                    return _FakeCompletion()

    company = SeedCompany(
        slug="rwe-2024",
        company_name="RWE AG",
        report_year=2024,
        industry_code="D35.11",
        industry_sector="Electricity",
        source_url="https://example.com/rwe.pdf",
        verify=False,
    )

    result = audit_one(
        company,
        api_base="http://localhost:8000",
        model="gpt-4.1",
        max_chars=80000,
        openai_client=_FakeOpenAI(),
        dry_run=False,
    )

    assert result.error is None
    with TestSession() as db:
        rows = db.query(ExtractionRun).all()
    assert len(rows) == 1
    assert rows[0].run_kind == "audit"
    assert rows[0].model == "gpt-4.1"
    assert rows[0].verdict == "ok"
    assert rows[0].file_hash is not None


def test_extraction_run_not_fatal_on_db_error(monkeypatch, tmp_path) -> None:
    """If record_extraction_run raises, audit_one must still return a valid result."""
    import json as _json

    from scripts.audit_extractions import audit_one

    # Make record_extraction_run blow up.
    def _boom(*_args, **_kw):
        raise RuntimeError("simulated DB failure")

    monkeypatch.setattr("scripts.audit_extractions.record_extraction_run", _boom)

    # Stub PDF.
    pdf_path = tmp_path / "basf-2024.pdf"
    pdf_path.write_bytes(b"%PDF-1.7\n" + b"y" * 1024)
    monkeypatch.setattr("scripts.audit_extractions.PDF_CACHE_DIR", tmp_path)
    monkeypatch.setattr("scripts.audit_extractions.extract_text_from_pdf", lambda _path: "quote")

    # Stub profile.
    monkeypatch.setattr(
        "scripts.audit_extractions.fetch_company_profile",
        lambda *_args, **_kw: ({"latest_metrics": {"scope1_co2e_tonnes": 1.0}}, "BASF SE"),
    )

    raw_json = _json.dumps(
        {
            "scope1_co2e_tonnes": {
                "verdict": "correct",
                "confidence": "high",
                "evidence_quote": "quote",
            }
        }
    )

    class _FakeChoice:
        message = type("M", (), {"content": raw_json})()

    class _FakeCompletion:
        choices = [_FakeChoice()]

    class _FakeOpenAI:
        class chat:
            class completions:
                @staticmethod
                def create(**_kw):
                    return _FakeCompletion()

    company = SeedCompany(
        slug="basf-2024",
        company_name="BASF SE",
        report_year=2024,
        industry_code="C20.11",
        industry_sector="Chemicals",
        source_url="https://example.com/basf.pdf",
        verify=False,
    )

    result = audit_one(
        company,
        api_base="http://localhost:8000",
        model="gpt-4.1",
        max_chars=80000,
        openai_client=_FakeOpenAI(),
        dry_run=False,
    )

    # Despite the DB failure, audit must complete and return fields.
    assert result.error is None
    assert len(result.fields) == len(AUDIT_FIELDS)

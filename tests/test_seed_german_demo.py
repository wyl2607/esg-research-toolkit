from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from scripts.seed_german_demo import (
    PDF_DOWNLOAD_HEADERS,
    SeedCompany,
    ensure_pdf,
    filter_companies,
    load_manifest,
    main,
    phase_b,
    upload_company,
)


def test_manifest_parses_and_has_twenty_companies() -> None:
    companies = load_manifest()

    # Manifest expanded to include multi-year data (2022-2024) for core DAX companies
    assert len(companies) >= 20
    assert all(isinstance(company, SeedCompany) for company in companies)

    # Must remain aligned with frontend NACE picker coverage
    valid_prefixes = {
        "D35",
        "C24",
        "C20",
        "C23",
        "C29",
        "C30",  # Manufacture of electrical machinery (Siemens)
        "K64",
        "K65",
        "F41",
        "C16",
        "C10",
        "C19",
        "H49",
        "H51",
        "J61",
        "J62",
        "H53",
        "Q86",
        "C21",
        "C14",
        "C28",
    }
    for company in companies:
        assert company.industry_code.split(".")[0] in valid_prefixes


def test_manifest_entry_rejects_missing_fields() -> None:
    with pytest.raises(ValueError):
        SeedCompany.from_dict({"slug": "only-slug"})


def test_filter_companies_supports_slug_and_company_name() -> None:
    companies = [
        SeedCompany(
            slug="rwe-2024",
            company_name="RWE AG",
            report_year=2024,
            industry_code="D35.11",
            industry_sector="Electricity production",
            source_url="https://example.com/rwe-2024.pdf",
            verify=False,
        ),
        SeedCompany(
            slug="basf-2024",
            company_name="BASF SE",
            report_year=2024,
            industry_code="C20.14",
            industry_sector="Organic basic chemicals",
            source_url="https://example.com/basf-2024.pdf",
            verify=False,
        ),
        SeedCompany(
            slug="rwe-2023",
            company_name="RWE AG",
            report_year=2023,
            industry_code="D35.11",
            industry_sector="Electricity production",
            source_url="https://example.com/rwe-2023.pdf",
            verify=False,
        ),
    ]

    slug_filtered = filter_companies(companies, slugs=["rwe-2024"])
    assert [company.slug for company in slug_filtered] == ["rwe-2024"]

    company_filtered = filter_companies(companies, company_names=["rwe ag"])
    assert [company.slug for company in company_filtered] == ["rwe-2024", "rwe-2023"]

    combined_filtered = filter_companies(
        companies,
        slugs=["rwe-2024", "basf-2024"],
        company_names=["RWE AG"],
    )
    assert [company.slug for company in combined_filtered] == ["rwe-2024"]

    only_filtered = filter_companies(
        companies,
        only_filters=["rwe-2024", "BASF SE"],
    )
    assert [company.slug for company in only_filtered] == ["rwe-2024", "basf-2024"]

    comma_only_filtered = filter_companies(
        companies,
        only_filters=["rwe-2024, BASF SE"],
    )
    assert [company.slug for company in comma_only_filtered] == ["rwe-2024", "basf-2024"]


def test_main_dry_run_does_not_call_network(monkeypatch: pytest.MonkeyPatch) -> None:
    company = SeedCompany(
        slug="demo-2024",
        company_name="Demo AG",
        report_year=2024,
        industry_code="D35.11",
        industry_sector="Electricity production",
        source_url="https://example.com/demo.pdf",
        verify=True,
    )
    monkeypatch.setattr("scripts.seed_german_demo.load_manifest", lambda: [company])

    class _NoNetworkClient:
        def __init__(self, *args, **kwargs):  # noqa: D401, ANN002, ANN003
            raise AssertionError("httpx.Client should not be used in --dry-run")

    monkeypatch.setattr("scripts.seed_german_demo.httpx.Client", _NoNetworkClient)

    exit_code = main(["--dry-run"])
    assert exit_code == 0


def test_main_rejects_empty_filtered_selection(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(
        "scripts.seed_german_demo.load_manifest",
        lambda: [
            SeedCompany(
                slug="demo-2024",
                company_name="Demo AG",
                report_year=2024,
                industry_code="D35.11",
                industry_sector="Electricity production",
                source_url="https://example.com/demo.pdf",
                verify=False,
            )
        ],
    )

    exit_code = main(["--dry-run", "--slug", "missing-slug"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "no manifest entries matched" in captured.out


def test_main_only_filter_selects_slug_and_company_name(monkeypatch: pytest.MonkeyPatch) -> None:
    companies = [
        SeedCompany(
            slug="rwe-2024",
            company_name="RWE AG",
            report_year=2024,
            industry_code="D35.11",
            industry_sector="Electricity production",
            source_url="https://example.com/rwe-2024.pdf",
            verify=False,
        ),
        SeedCompany(
            slug="rwe-2023",
            company_name="RWE AG",
            report_year=2023,
            industry_code="D35.11",
            industry_sector="Electricity production",
            source_url="https://example.com/rwe-2023.pdf",
            verify=False,
        ),
        SeedCompany(
            slug="basf-2024",
            company_name="BASF SE",
            report_year=2024,
            industry_code="C20.14",
            industry_sector="Organic basic chemicals",
            source_url="https://example.com/basf-2024.pdf",
            verify=False,
        ),
    ]
    monkeypatch.setattr("scripts.seed_german_demo.load_manifest", lambda: companies)

    selected_slugs: dict[str, list[str]] = {}

    def _fake_phase_a(_api_base, phase_companies, *, dry_run, timeout):
        assert dry_run is True
        assert timeout > 0
        selected_slugs["value"] = [company.slug for company in phase_companies]
        return {"succeeded": [], "failed": [], "skipped": [], "total": len(phase_companies)}

    monkeypatch.setattr("scripts.seed_german_demo.phase_a", _fake_phase_a)

    exit_code = main(["--dry-run", "--only", "rwe-2024", "--only", "BASF SE"])
    assert exit_code == 0
    assert selected_slugs["value"] == ["rwe-2024", "basf-2024"]


def test_main_rejects_only_with_legacy_filters(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("scripts.seed_german_demo.load_manifest", lambda: [])

    exit_code = main(["--dry-run", "--only", "rwe-2024", "--slug", "rwe-2024"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "--only cannot be combined" in captured.out


def test_script_entrypoint_runs_without_manual_pythonpath() -> None:
    repo_root = os.path.dirname(os.path.dirname(__file__))
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.setdefault("OPENAI_API_KEY", "dummy")
    result = subprocess.run(
        [sys.executable, "scripts/seed_german_demo.py", "--dry-run"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "loaded" in result.stdout
    assert "Phase A summary" in result.stdout


def test_ensure_pdf_uses_browser_headers(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    company = SeedCompany(
        slug="header-check-2024",
        company_name="Header Check AG",
        report_year=2024,
        industry_code="D35.11",
        industry_sector="Electricity production",
        source_url="https://example.com/header-check.pdf",
        verify=False,
    )
    monkeypatch.setattr("scripts.seed_german_demo.PDF_CACHE_DIR", tmp_path)

    captured_headers: list[dict[str, str]] = []

    class _Response:
        status_code = 200
        content = b"%PDF-1.7\n" + (b"x" * 2048)

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def get(self, url: str, headers: dict[str, str] | None = None):
            assert url == company.source_url
            captured_headers.append(headers or {})
            return _Response()

    monkeypatch.setattr("scripts.seed_german_demo.httpx.Client", _Client)

    pdf_path = ensure_pdf(company, dry_run=False, timeout=5)
    assert pdf_path is not None
    assert pdf_path.exists()
    assert captured_headers and captured_headers[0] == PDF_DOWNLOAD_HEADERS


def test_phase_b_uses_shared_client_and_validation_model(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr("scripts.seed_german_demo.ANOMALIES_REPORT_PATH", tmp_path / "anomalies_report.md")
    monkeypatch.setattr("scripts.seed_german_demo.settings.openai_validation_model", "relay-validation-model")

    company = SeedCompany(
        slug="demo-2024",
        company_name="Demo AG",
        report_year=2024,
        industry_code="D35.11",
        industry_sector="Electricity production",
        source_url="https://example.com/demo.pdf",
        verify=False,
    )

    class _ProfileResponse:
        status_code = 200

        @staticmethod
        def json() -> dict:
            return {
                "latest_metrics": {"scope1_emissions": 123.4},
                "evidence_summary": [{"metric": "scope1_emissions", "snippet": "123.4 tCO2e"}],
            }

    class _HttpClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def get(self, url: str):
            assert "Demo%20AG" in url
            return _ProfileResponse()

    captured_calls: list[dict[str, object]] = []

    class _ChatCompletions:
        @staticmethod
        def create(**kwargs):
            captured_calls.append(kwargs)

            class _Message:
                content = json.dumps({"company": "Demo AG", "concerns": []})

            class _Choice:
                message = _Message()

            class _Completion:
                choices = [_Choice()]

            return _Completion()

    class _FakeClient:
        class chat:
            completions = _ChatCompletions()

    get_client_calls = {"count": 0}

    def _fake_get_client():
        get_client_calls["count"] += 1
        return _FakeClient()

    monkeypatch.setattr("scripts.seed_german_demo.httpx.Client", _HttpClient)
    monkeypatch.setattr("scripts.seed_german_demo.get_client", _fake_get_client)

    phase_b("http://relay.test", [company])

    assert get_client_calls["count"] == 1
    assert len(captured_calls) == 1
    assert captured_calls[0]["model"] == "relay-validation-model"


def test_phase_b_drops_no_concern_entries(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr("scripts.seed_german_demo.ANOMALIES_REPORT_PATH", tmp_path / "anomalies_report.md")

    company = SeedCompany(
        slug="demo-2024",
        company_name="Demo AG",
        report_year=2024,
        industry_code="D35.11",
        industry_sector="Electricity production",
        source_url="https://example.com/demo.pdf",
        verify=False,
    )

    class _ProfileResponse:
        status_code = 200

        @staticmethod
        def json() -> dict:
            return {
                "latest_metrics": {"scope1_co2e_tonnes": 123.4},
                "evidence_summary": [{"metric": "scope1_co2e_tonnes", "snippet": "123.4 tCO2e"}],
            }

    class _HttpClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def get(self, url: str):
            return _ProfileResponse()

    class _ChatCompletions:
        @staticmethod
        def create(**kwargs):
            class _Message:
                content = json.dumps(
                    {
                        "company": "Demo AG",
                        "concerns": [
                            {
                                "metric": "scope1_co2e_tonnes",
                                "value": 123.4,
                                "reason": "Evidence shows this is plausible. No concern.",
                            }
                        ],
                    }
                )

            class _Choice:
                message = _Message()

            class _Completion:
                choices = [_Choice()]

            return _Completion()

    class _FakeClient:
        class chat:
            completions = _ChatCompletions()

    monkeypatch.setattr("scripts.seed_german_demo.httpx.Client", _HttpClient)
    monkeypatch.setattr("scripts.seed_german_demo.get_client", lambda: _FakeClient())

    phase_b("http://relay.test", [company])

    report = (tmp_path / "anomalies_report.md").read_text(encoding="utf-8")
    assert "_No anomalies flagged." in report


def test_upload_company_sends_override_company_name(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    company = SeedCompany(
        slug="vw-2024",
        company_name="Volkswagen AG",
        report_year=2024,
        industry_code="C29.10",
        industry_sector="Manufacture of motor vehicles",
        source_url="https://example.com/vw.pdf",
        verify=False,
    )
    pdf_path = tmp_path / "vw.pdf"
    pdf_path.write_bytes(b"%PDF-1.7\n" + b"x" * 2048)

    captured: dict[str, object] = {}

    class _Response:
        status_code = 200

        @staticmethod
        def json() -> dict:
            return {"company_name": "Volkswagen AG", "report_year": 2024}

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def post(self, url: str, files=None, data=None):
            captured["url"] = url
            captured["data"] = data
            captured["files"] = files
            return _Response()

    monkeypatch.setattr("scripts.seed_german_demo.httpx.Client", _Client)

    payload = upload_company("http://api.test", company, pdf_path, timeout=10)

    assert payload == {"company_name": "Volkswagen AG", "report_year": 2024}
    assert captured["url"] == "http://api.test/report/upload"
    assert captured["data"] == {
        "industry_code": "C29.10",
        "industry_sector": "Manufacture of motor vehicles",
        "override_company_name": "Volkswagen AG",
    }

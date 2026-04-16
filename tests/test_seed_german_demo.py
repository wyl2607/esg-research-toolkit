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
    load_manifest,
    main,
    phase_b,
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

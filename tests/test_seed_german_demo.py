from __future__ import annotations

import pytest

from scripts.seed_german_demo import PDF_DOWNLOAD_HEADERS, SeedCompany, ensure_pdf, load_manifest, main


def test_manifest_parses_and_has_twenty_companies() -> None:
    companies = load_manifest()

    assert len(companies) == 20
    assert all(isinstance(company, SeedCompany) for company in companies)

    # Must remain aligned with frontend NACE picker coverage
    valid_prefixes = {
        "D35",
        "C24",
        "C20",
        "C23",
        "C29",
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

from __future__ import annotations

import pytest

from scripts.seed_german_demo import SeedCompany, load_manifest, main


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
        "H53",
        "Q86",
        "C21",
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

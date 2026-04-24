from __future__ import annotations

import importlib
import os
import sys


def _load_main(*, contract_mode: bool):
    if contract_mode:
        os.environ["ESG_CONTRACT_TEST_MODE"] = "1"
    else:
        os.environ.pop("ESG_CONTRACT_TEST_MODE", None)

    if "main" in sys.modules:
        del sys.modules["main"]
    import main  # type: ignore

    return importlib.reload(main)


def test_openapi_exposes_typegen_contract_metadata(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")

    main = _load_main(contract_mode=False)
    schema = main.app.openapi()

    assert schema["components"]["schemas"]["LCOEInput"]["properties"]["capacity_mw"]["default"] == 100.0
    assert schema["components"]["schemas"]["SensitivityResult"]["properties"]["values"]["type"] == "array"
    assert schema["paths"]["/frameworks/score"]["get"]["responses"]["400"]["description"] == "Unknown framework identifier."
    assert "/health/models" in schema["paths"]
    assert "/health/deploy" in schema["paths"]
    assert (
        schema["paths"]["/report/merge/preview"]["post"]["requestBody"]["content"]["application/json"]["examples"][
            "contractSeed"
        ]["value"]["documents"][0]["company_name"]
        == "Contract Demo AG"
    )


def test_contract_test_mode_prunes_unstable_operations(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")

    main = _load_main(contract_mode=True)
    schema = main.app.openapi()

    assert "/report/upload" not in schema["paths"]
    assert "delete" not in schema["paths"]["/report/companies/{company_name}/{report_year}"]
    assert "/taxonomy/report/pdf" not in schema["paths"]
    assert "get" in schema["paths"]["/report/companies/{company_name}/profile"]


def test_cors_origins_are_configurable(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com, https://admin.example.com")

    main = _load_main(contract_mode=False)

    assert main._cors_allowed_origins() == ["https://app.example.com", "https://admin.example.com"]

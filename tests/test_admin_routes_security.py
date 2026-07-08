from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from report_parser.admin_routes import require_admin_token, validate_admin_config


def test_admin_delete_requires_token_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_API_TOKEN", "expected-token")

    try:
        require_admin_token(x_admin_token=None)
    except HTTPException as exc:
        assert exc.status_code == 403
    else:  # pragma: no cover
        raise AssertionError("Expected admin token failure")


def test_admin_delete_disabled_in_production_without_token(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ADMIN_API_TOKEN", "")

    try:
        require_admin_token(x_admin_token=None)
    except HTTPException as exc:
        assert exc.status_code == 503
    else:  # pragma: no cover
        raise AssertionError("Expected production admin disablement")


def test_admin_token_allows_matching_header(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_API_TOKEN", "expected-token")

    assert require_admin_token(x_admin_token="expected-token") is None


@pytest.mark.parametrize(
    "path",
    ["/report/companies/export/csv", "/report/companies/export/xlsx"],
)
def test_export_endpoints_require_admin_token(monkeypatch, path: str) -> None:
    monkeypatch.setenv("ADMIN_API_TOKEN", "expected-token")

    import main

    response = TestClient(main.app).get(path)
    assert response.status_code == 403


@pytest.mark.parametrize("app_env", ["staging", "prod", "anything-unknown"])
def test_admin_disabled_in_non_local_envs_without_token(monkeypatch, app_env: str) -> None:
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("ADMIN_API_TOKEN", "")

    with pytest.raises(HTTPException) as exc:
        require_admin_token(x_admin_token=None)
    assert exc.value.status_code == 503


def test_validate_admin_config_fails_fast_without_token(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ADMIN_API_TOKEN", "")

    with pytest.raises(RuntimeError, match="ADMIN_API_TOKEN"):
        validate_admin_config()


@pytest.mark.parametrize("app_env", ["development", "test", "local"])
def test_validate_admin_config_allows_local_envs(monkeypatch, app_env: str) -> None:
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("ADMIN_API_TOKEN", "")

    validate_admin_config()


def test_validate_admin_config_allows_production_with_token(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ADMIN_API_TOKEN", "configured")

    validate_admin_config()


@pytest.mark.parametrize(
    "path",
    ["/benchmarks/recompute", "/frameworks/cache/clear"],
)
def test_mutating_maintenance_endpoints_require_admin_token(monkeypatch, path: str) -> None:
    monkeypatch.setenv("ADMIN_API_TOKEN", "expected-token")

    import main

    response = TestClient(main.app).post(path)
    assert response.status_code == 403


def test_cache_clear_accepts_admin_token(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_API_TOKEN", "expected-token")

    import main

    response = TestClient(main.app).post(
        "/frameworks/cache/clear", headers={"X-Admin-Token": "expected-token"}
    )
    assert response.status_code == 200

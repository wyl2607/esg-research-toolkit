from __future__ import annotations

import pytest

from report_parser.admin_routes import require_admin_token, validate_admin_config
from fastapi import HTTPException


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


def test_admin_rejects_wrong_token(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_API_TOKEN", "expected-token")

    with pytest.raises(HTTPException) as exc:
        require_admin_token(x_admin_token="wrong-token")
    assert exc.value.status_code == 403


def test_admin_disabled_in_unknown_nonlocal_env_without_token(monkeypatch) -> None:
    # Any non-local env (not just "production") must fail closed.
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("ADMIN_API_TOKEN", "")

    with pytest.raises(HTTPException) as exc:
        require_admin_token(x_admin_token=None)
    assert exc.value.status_code == 503


def test_admin_allowed_in_dev_without_token(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ADMIN_API_TOKEN", "")

    assert require_admin_token(x_admin_token=None) is None


def test_validate_admin_config_raises_for_nonlocal_without_token(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ADMIN_API_TOKEN", "")

    with pytest.raises(RuntimeError):
        validate_admin_config()


def test_validate_admin_config_ok_when_token_present(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ADMIN_API_TOKEN", "a-strong-token")

    assert validate_admin_config() is None

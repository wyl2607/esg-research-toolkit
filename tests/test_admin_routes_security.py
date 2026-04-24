from __future__ import annotations

from report_parser.admin_routes import require_admin_token
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
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)

    try:
        require_admin_token(x_admin_token=None)
    except HTTPException as exc:
        assert exc.status_code == 503
    else:  # pragma: no cover
        raise AssertionError("Expected production admin disablement")


def test_admin_token_allows_matching_header(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_API_TOKEN", "expected-token")

    assert require_admin_token(x_admin_token="expected-token") is None

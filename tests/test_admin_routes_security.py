from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from report_parser.admin_routes import require_admin_token


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

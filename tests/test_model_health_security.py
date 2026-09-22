from __future__ import annotations

from fastapi.testclient import TestClient

from core import models
from core.config import settings


def test_provider_failure_is_degraded_and_public_payload_is_redacted(monkeypatch) -> None:
    monkeypatch.setattr(settings, "openai_model", "gpt-5.3-codex")
    monkeypatch.setattr(settings, "openai_extraction_model", "")
    monkeypatch.setattr(settings, "openai_validation_model", "gpt-5.4-mini")
    monkeypatch.setattr(settings, "openai_audit_model", "gpt-4o")
    monkeypatch.setattr(
        models,
        "_provider_model_ids",
        lambda: (None, "provider list unavailable: Error code: 401"),
    )
    models._availability_cache.clear()

    detailed = models.health_payload()
    public = models.public_health_payload()

    assert detailed["status"] == "degraded"
    assert all(entry["available"] is False for entry in detailed["models"].values())
    assert all(entry["check_source"] == "unknown" for entry in detailed["models"].values())
    assert public["status"] == "degraded"
    assert public["ready"] is False

    for entry in public["models"].values():
        assert set(entry) == {"available"}
    public_text = repr(public)
    for sensitive in (
        "gpt-5.3-codex",
        "gpt-5.4-mini",
        "gpt-4o",
        "fallback",
        "max_tokens",
        "last_checked_at",
        "provider list unavailable",
    ):
        assert sensitive not in public_text


def test_model_details_requires_admin_token(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_API_TOKEN", "expected-token")

    import main

    monkeypatch.setattr(
        main,
        "model_health_payload",
        lambda: {
            "status": "degraded",
            "models": {
                "extraction": {
                    "model": "secret-model",
                    "max_tokens": 1024,
                    "fallback": ["secret-fallback"],
                    "available": False,
                    "check_source": "unknown",
                    "last_checked_at": "2026-08-25T00:00:00+00:00",
                    "detail": "provider failure",
                }
            },
        },
    )

    client = TestClient(main.app)
    assert client.get("/health/models/details").status_code == 403

    response = client.get(
        "/health/models/details",
        headers={"X-Admin-Token": "expected-token"},
    )
    assert response.status_code == 200
    assert response.json()["models"]["extraction"]["model"] == "secret-model"


def test_public_model_health_route_uses_safe_contract(monkeypatch) -> None:
    import main

    monkeypatch.setattr(
        main,
        "public_model_health_payload",
        lambda: {
            "status": "degraded",
            "ready": False,
            "models": {
                "extraction": {"available": False},
            },
        },
    )

    response = TestClient(main.app).get("/health/models")

    assert response.status_code == 200
    assert response.json() == {
        "status": "degraded",
        "ready": False,
        "models": {"extraction": {"available": False}},
    }

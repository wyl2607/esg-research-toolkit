from __future__ import annotations

import logging

from core import models
from core.config import settings


def test_refresh_availability_all_known_provider(monkeypatch) -> None:
    monkeypatch.setattr(settings, "openai_model", "gpt-4.1")
    monkeypatch.setattr(settings, "openai_extraction_model", "")
    monkeypatch.setattr(settings, "openai_validation_model", "gpt-5.4-mini")
    monkeypatch.setattr(settings, "openai_audit_model", "gpt-4o")
    monkeypatch.setattr(
        models,
        "_provider_model_ids",
        lambda: ({"gpt-4.1", "gpt-5.4-mini", "gpt-4o"}, None),
    )

    availability = models.refresh_availability()

    assert availability["extraction"].available is True
    assert availability["validation"].available is True
    assert availability["audit"].available is True
    assert availability["extraction"].source == "provider"


def test_refresh_availability_unknown_validation_warns(monkeypatch, caplog) -> None:
    monkeypatch.setattr(settings, "openai_model", "gpt-4.1")
    monkeypatch.setattr(settings, "openai_extraction_model", "")
    monkeypatch.setattr(settings, "openai_validation_model", "totally-unknown-validation-model")
    monkeypatch.setattr(settings, "openai_audit_model", "gpt-4o")
    monkeypatch.setattr(
        models,
        "_provider_model_ids",
        lambda: ({"gpt-4.1", "gpt-4o"}, None),
    )

    with caplog.at_level(logging.WARNING):
        availability = models.refresh_availability()

    assert availability["validation"].available is False
    assert "purpose=validation" in caplog.text


def test_refresh_availability_unknown_extraction_warns(monkeypatch, caplog) -> None:
    monkeypatch.setattr(settings, "openai_model", "")
    monkeypatch.setattr(settings, "openai_extraction_model", "unknown-extraction-model")
    monkeypatch.setattr(settings, "openai_validation_model", "gpt-5.4-mini")
    monkeypatch.setattr(settings, "openai_audit_model", "gpt-4o")
    monkeypatch.setattr(
        models,
        "_provider_model_ids",
        lambda: ({"gpt-5.4-mini", "gpt-4o"}, None),
    )

    with caplog.at_level(logging.WARNING):
        availability = models.refresh_availability()

    assert availability["extraction"].available is False
    assert "purpose=extraction" in caplog.text


def test_health_payload_contains_last_checked(monkeypatch) -> None:
    monkeypatch.setattr(settings, "openai_model", "gpt-4.1")
    monkeypatch.setattr(settings, "openai_extraction_model", "")
    monkeypatch.setattr(settings, "openai_validation_model", "gpt-5.4-mini")
    monkeypatch.setattr(settings, "openai_audit_model", "gpt-4o")
    monkeypatch.setattr(
        models,
        "_provider_model_ids",
        lambda: ({"gpt-4.1", "gpt-5.4-mini", "gpt-4o"}, None),
    )

    payload = models.health_payload()

    assert payload["status"] == "ok"
    assert payload["models"]["audit"]["model"] == "gpt-4o"
    assert payload["models"]["validation"]["last_checked_at"] is not None

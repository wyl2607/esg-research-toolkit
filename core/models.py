from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from core.config import settings

ModelPurpose = Literal["extraction", "validation", "audit"]

_logger = logging.getLogger(__name__)
_availability_lock = threading.Lock()

_KNOWN_MODEL_WHITELIST: set[str] = {
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-5.2",
    "gpt-5.3-codex",
    "gpt-5.4",
    "gpt-5.4-mini",
}


@dataclass(frozen=True)
class ModelSpec:
    purpose: ModelPurpose
    model: str
    max_tokens: int
    fallback: list[str]


@dataclass(frozen=True)
class ModelAvailability:
    purpose: ModelPurpose
    model: str
    available: bool
    source: str
    checked_at: str
    detail: str | None = None


def _registry() -> dict[ModelPurpose, ModelSpec]:
    extraction_model = (settings.openai_model or settings.openai_extraction_model).strip()
    validation_model = settings.openai_validation_model.strip()
    audit_model = settings.openai_audit_model.strip()
    return {
        "extraction": ModelSpec(
            purpose="extraction",
            model=extraction_model,
            max_tokens=1024,
            fallback=["gpt-4o", "gpt-4o-mini"],
        ),
        "validation": ModelSpec(
            purpose="validation",
            model=validation_model,
            max_tokens=1024,
            fallback=["gpt-4o", "gpt-4o-mini"],
        ),
        "audit": ModelSpec(
            purpose="audit",
            model=audit_model,
            max_tokens=2048,
            fallback=["gpt-4o", "gpt-4o-mini"],
        ),
    }


def get(purpose: ModelPurpose) -> str:
    return _registry()[purpose].model


def get_spec(purpose: ModelPurpose) -> ModelSpec:
    return _registry()[purpose]


def all_specs() -> dict[ModelPurpose, ModelSpec]:
    return _registry()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _provider_model_ids() -> tuple[set[str] | None, str | None]:
    api_key = settings.openai_api_key
    if not api_key or api_key == "dummy":
        return None, "provider skipped (missing or dummy OPENAI_API_KEY)"
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            timeout=8.0,
        )
        result = client.models.list()
        ids = {item.id for item in result.data if getattr(item, "id", None)}
        return ids, None
    except Exception as exc:  # noqa: BLE001
        return None, f"provider list unavailable: {exc}"


_availability_cache: dict[ModelPurpose, ModelAvailability] = {}


def refresh_availability() -> dict[ModelPurpose, ModelAvailability]:
    specs = _registry()
    provider_ids, provider_error = _provider_model_ids()
    checked_at = _now_iso()

    with _availability_lock:
        next_cache: dict[ModelPurpose, ModelAvailability] = {}
        for purpose, spec in specs.items():
            if provider_ids is not None:
                available = spec.model in provider_ids
                source = "provider"
                detail = None
            else:
                available = spec.model in _KNOWN_MODEL_WHITELIST
                source = "whitelist"
                detail = provider_error
            if not available:
                _logger.warning("model %s not in provider list for purpose=%s", spec.model, purpose)
            next_cache[purpose] = ModelAvailability(
                purpose=purpose,
                model=spec.model,
                available=available,
                source=source,
                checked_at=checked_at,
                detail=detail,
            )
        _availability_cache.clear()
        _availability_cache.update(next_cache)
        return dict(_availability_cache)


def get_availability() -> dict[ModelPurpose, ModelAvailability]:
    with _availability_lock:
        has_cache = bool(_availability_cache)
        cached = dict(_availability_cache)
    if has_cache:
        return cached
    return refresh_availability()


def validate_models_startup() -> None:
    try:
        refresh_availability()
    except Exception as exc:  # noqa: BLE001
        _logger.warning("model availability check failed at startup: %s", exc)


def health_payload() -> dict[str, object]:
    availability = get_availability()
    specs = _registry()
    purpose_payload: dict[str, dict[str, object]] = {}
    for purpose, spec in specs.items():
        status = availability.get(purpose)
        purpose_payload[purpose] = {
            "model": spec.model,
            "max_tokens": spec.max_tokens,
            "fallback": spec.fallback,
            "available": status.available if status else None,
            "check_source": status.source if status else None,
            "last_checked_at": status.checked_at if status else None,
            "detail": status.detail if status else None,
        }

    return {
        "status": "ok",
        "models": purpose_payload,
    }

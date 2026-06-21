from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.config import Settings


def _make(**overrides):
    base = {"openai_api_key": "test-key"}
    base.update(overrides)
    return Settings(**base)


def test_https_base_url_accepted() -> None:
    s = _make(openai_base_url="https://api.openai.com/v1")
    assert s.openai_base_url == "https://api.openai.com/v1"


def test_http_localhost_accepted() -> None:
    s = _make(openai_base_url="http://localhost:1234/v1")
    assert s.openai_base_url.startswith("http://localhost")


def test_http_remote_rejected() -> None:
    with pytest.raises(ValidationError):
        _make(openai_base_url="http://evil.example.com/v1")


def test_non_http_scheme_rejected() -> None:
    with pytest.raises(ValidationError):
        _make(openai_base_url="file:///etc/passwd")

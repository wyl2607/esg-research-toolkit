"""Tests for core.ai_client module."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch


def test_get_client_returns_singleton() -> None:
    if "core.ai_client" in sys.modules:
        del sys.modules["core.ai_client"]

    with patch("core.ai_client.OpenAI") as mock_openai_class:
        mock_client_instance = MagicMock()
        mock_openai_class.return_value = mock_client_instance

        from core import ai_client
        ai_client._client = None

        result1 = ai_client.get_client()
        result2 = ai_client.get_client()

        assert result1 is result2


def test_complete_returns_stripped_text() -> None:
    if "core.ai_client" in sys.modules:
        del sys.modules["core.ai_client"]

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "  extracted  "
    mock_client.chat.completions.create.return_value = mock_response

    with patch("core.ai_client.get_client", return_value=mock_client):
        with patch("core.ai_client.get_model_name", return_value="gpt-4"):
            with patch("core.ai_client.get_spec", return_value=MagicMock(max_tokens=500)):
                from core import ai_client
                result = ai_client.complete(system="sys", user="user")

    assert result == "extracted"


def test_complete_handles_empty_content() -> None:
    if "core.ai_client" in sys.modules:
        del sys.modules["core.ai_client"]

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = None
    mock_client.chat.completions.create.return_value = mock_response

    with patch("core.ai_client.get_client", return_value=mock_client):
        with patch("core.ai_client.get_model_name", return_value="gpt-4"):
            with patch("core.ai_client.get_spec", return_value=MagicMock(max_tokens=500)):
                from core import ai_client
                result = ai_client.complete(system="sys", user="user")

    assert result == ""


def test_complete_uses_max_tokens_override() -> None:
    if "core.ai_client" in sys.modules:
        del sys.modules["core.ai_client"]

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "test"
    mock_client.chat.completions.create.return_value = mock_response

    with patch("core.ai_client.get_client", return_value=mock_client):
        with patch("core.ai_client.get_model_name", return_value="gpt-4"):
            with patch("core.ai_client.get_spec", return_value=MagicMock(max_tokens=500)):
                from core import ai_client
                ai_client.complete(system="sys", user="user", max_tokens=200)

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["max_tokens"] == 200

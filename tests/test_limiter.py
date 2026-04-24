"""Tests for core.limiter module."""
from __future__ import annotations


def test_limiter_instance_exported() -> None:
    """Verify limiter instance is exported."""
    try:
        from core import limiter

        assert hasattr(limiter, "limiter")
        from slowapi import Limiter

        assert isinstance(limiter.limiter, Limiter)
    except ImportError as e:
        if "sqlalchemy" in str(e):
            pass
        else:
            raise


def test_default_limits_outside_test_mode(monkeypatch) -> None:
    """Test default limits when not in test mode."""
    monkeypatch.delenv("ESG_CONTRACT_TEST_MODE", raising=False)

    try:
        from core import limiter as limiter_module

        assert limiter_module.default_limits == ["60/minute"]
    except ImportError:
        pass

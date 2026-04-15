import pytest

from core.limiter import limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> None:
    limiter.reset()
    yield
    limiter.reset()

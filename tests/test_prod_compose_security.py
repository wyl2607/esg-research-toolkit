from __future__ import annotations

import re
from pathlib import Path


def test_production_api_port_is_loopback_bound() -> None:
    compose = Path("docker-compose.prod.yml").read_text(encoding="utf-8")

    assert re.search(
        r'^\s*-\s*["\\']127\\.0\\.0\\.1:8001:8000["\\']\s*$',
        compose,
        flags=re.MULTILINE,
    )
    assert not re.search(
        r'^\s*-\s*["\\']8001:8000["\\']\s*$',
        compose,
        flags=re.MULTILINE,
    )

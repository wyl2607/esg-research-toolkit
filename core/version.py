from __future__ import annotations

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def app_version() -> str:
    version_file = Path(__file__).resolve().parents[1] / "docs" / "releases" / "VERSION.md"
    for line in version_file.read_text(encoding="utf-8").splitlines():
        value = line.strip().strip("`")
        if value.startswith("v"):
            return value.removeprefix("v")
    raise RuntimeError(f"Could not read app version from {version_file}")

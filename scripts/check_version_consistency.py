from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.version import app_version  # noqa: E402


def _frontend_version() -> str:
    package_json = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    return str(package_json["version"])


def _frontend_lock_versions() -> dict[str, str]:
    package_lock = json.loads((ROOT / "frontend" / "package-lock.json").read_text(encoding="utf-8"))
    return {
        "frontend/package-lock.json": str(package_lock["version"]),
        "frontend/package-lock.json packages['']": str(package_lock["packages"][""]["version"]),
    }


def _release_version() -> str:
    text = (ROOT / "docs" / "releases" / "VERSION.md").read_text(encoding="utf-8")
    match = re.search(r"`v?([^`]+)`", text)
    if not match:
        raise RuntimeError("docs/releases/VERSION.md does not contain a backtick version")
    return match.group(1)


def main() -> int:
    versions = {
        "core.version": app_version(),
        "docs/releases/VERSION.md": _release_version(),
        "frontend/package.json": _frontend_version(),
        **_frontend_lock_versions(),
    }
    expected = versions["docs/releases/VERSION.md"]
    mismatches = {name: value for name, value in versions.items() if value != expected}
    if mismatches:
        for name, value in versions.items():
            marker = " != expected" if name in mismatches else ""
            print(f"{name}: {value}{marker}", file=sys.stderr)
        return 1
    print(f"version consistent: {expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

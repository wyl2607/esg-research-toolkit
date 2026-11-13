from __future__ import annotations

from pathlib import Path


def test_uptime_probe_follows_redirects_and_requires_200() -> None:
    workflow = Path(".github/workflows/uptime.yml").read_text(encoding="utf-8")

    assert "--max-redirs" in workflow
    assert "-fsSL" in workflow or "-L" in workflow

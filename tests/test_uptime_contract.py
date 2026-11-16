from __future__ import annotations

import re
from pathlib import Path


def test_uptime_probe_follows_redirects_and_requires_200() -> None:
    workflow = Path(".github/workflows/uptime.yml").read_text(encoding="utf-8")

    assert "-fsSL" in workflow or "-L" in workflow
    assert "-w '%{http_code}'" in workflow
    assert '[ "$code" = "200" ]' in workflow

    max_redirs = re.search(r"--max-redirs\s+(\d+)", workflow)
    assert max_redirs is not None
    assert int(max_redirs.group(1)) <= 5

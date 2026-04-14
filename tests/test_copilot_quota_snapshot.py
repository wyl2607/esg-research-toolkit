import json
import os
import subprocess
from pathlib import Path


def test_copilot_quota_snapshot_uses_terminal_dump_override(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    script = project_root / "scripts" / "copilot_quota_snapshot.sh"
    out_dir = tmp_path / "quota"

    env = dict(os.environ)
    env["OUT_DIR"] = str(out_dir)
    env["COPILOT_QUOTA_TERMINAL_DUMP"] = "Copilot UI\nRemaining reqs.: 37%\n"

    result = subprocess.run(
        [str(script)],
        cwd=project_root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    latest_json = out_dir / "latest.json"
    history = out_dir / "history.ndjson"
    assert latest_json.exists()
    assert history.exists()

    payload = json.loads(latest_json.read_text())
    assert payload["remaining_reqs_pct"] == "37%"
    assert payload["source"] == "terminal_front_tab"

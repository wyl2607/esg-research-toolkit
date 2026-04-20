#!/usr/bin/env bash
# benchmark_windows_node.sh — windows-pc (WSL) 节点性能基线采集
# 输出: runtime/perf/windows-node-baseline-<ts>.md + .json
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

HOST="windows-pc"
REMOTE_REPO="/home/wyl26/projects/esg-research-toolkit"
REMOTE_WRAP="wsl bash -lc"
ROUNDS="${ROUNDS:-3}"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="$ROOT/runtime/perf"
mkdir -p "$OUT_DIR"
OUT_JSON="$OUT_DIR/windows-node-baseline-$TS.json"
OUT_MD="$OUT_DIR/windows-node-baseline-$TS.md"

ssh_exec() {
  local cmd="$1"
  local b64
  b64="$(printf '%s' "$cmd" | base64 | tr -d '\n')"
  ssh "$HOST" "$REMOTE_WRAP 'echo $b64 | base64 -d | bash'"
}

echo "[info] syncing windows WSL repo to origin/main"
ssh_exec "cd $REMOTE_REPO && git fetch origin && git checkout main && git reset --hard origin/main >/dev/null && git rev-parse --short HEAD"

echo "[info] running rounds=$ROUNDS"
python3 - "$OUT_JSON" "$OUT_MD" "$ROUNDS" <<'PY'
import json, statistics, subprocess, sys, time
from datetime import datetime, timezone

out_json, out_md, rounds = sys.argv[1], sys.argv[2], int(sys.argv[3])

def run(cmd: str):
    start = time.perf_counter()
    p = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    dur = time.perf_counter() - start
    return {"cmd": cmd, "exit": p.returncode, "duration_sec": round(dur, 3), "stdout": p.stdout[-4000:], "stderr": p.stderr[-4000:]}

metrics = {
    "ssh_ping": [],
    "wsl_ping": [],
    "git_status": [],
    "codex_version": [],
    "dispatch_noop": [],
}
records = []

for i in range(1, rounds + 1):
    batch = {"round": i, "steps": []}
    batch["steps"].append(run("ssh windows-pc 'echo ping'"))
    batch["steps"].append(run("ssh windows-pc 'wsl bash -lc \"echo wsl-ping\"'"))
    batch["steps"].append(run("ssh windows-pc 'wsl bash -lc \"cd /home/wyl26/projects/esg-research-toolkit && git status -sb\"'"))
    batch["steps"].append(run("ssh windows-pc 'wsl bash -lc \"codex --version\"'"))
    batch["steps"].append(run("REMOTE_REPO=/home/wyl26/projects/esg-research-toolkit REMOTE_SHELL_WRAP='wsl bash -lc' ./scripts/automation/dispatch_remote_codex.sh windows-pc PERF-NOOP scripts/automation/prompts/cr-a4.txt"))

    names = ["ssh_ping", "wsl_ping", "git_status", "codex_version", "dispatch_noop"]
    for n, step in zip(names, batch["steps"]):
      metrics[n].append(step["duration_sec"])

    records.append(batch)

summary = {}
for k, vals in metrics.items():
    vals_sorted = sorted(vals)
    p50 = statistics.median(vals_sorted)
    p95 = vals_sorted[min(len(vals_sorted)-1, int(len(vals_sorted)*0.95))]
    summary[k] = {
        "n": len(vals),
        "min": round(min(vals),3),
        "max": round(max(vals),3),
        "p50": round(p50,3),
        "p95": round(p95,3),
        "avg": round(sum(vals)/len(vals),3),
    }

payload = {
    "ts_utc": datetime.now(timezone.utc).isoformat(),
    "rounds": rounds,
    "summary": summary,
    "records": records,
}

with open(out_json, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

md = []
md.append(f"# Windows Node Baseline ({payload['ts_utc']})")
md.append("")
md.append(f"Rounds: {rounds}")
md.append("")
md.append("| metric | n | min | p50 | p95 | max | avg |")
md.append("|---|---:|---:|---:|---:|---:|---:|")
for k,v in summary.items():
    md.append(f"| {k} | {v['n']} | {v['min']} | {v['p50']} | {v['p95']} | {v['max']} | {v['avg']} |")

md.append("")
md.append("## Notes")
md.append("- dispatch_noop uses existing dispatcher to execute a short codex task path on windows WSL.")
md.append("- This is node/runtime baseline timing, not frontend rendering benchmark.")

with open(out_md, "w", encoding="utf-8") as f:
    f.write("\n".join(md) + "\n")

print(out_json)
print(out_md)
PY

echo "[done] wrote:"
echo "  $OUT_JSON"
echo "  $OUT_MD"

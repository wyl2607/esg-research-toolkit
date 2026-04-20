#!/usr/bin/env bash
# benchmark_cluster_nodes_light.sh — 多节点轻量性能对比（不依赖远端修改）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

ROUNDS="${ROUNDS:-3}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="$ROOT/runtime/perf"
mkdir -p "$OUT_DIR"
OUT_JSON="$OUT_DIR/node-compare-light-$TS.json"
OUT_MD="$OUT_DIR/node-compare-light-$TS.md"

python3 - "$OUT_JSON" "$OUT_MD" "$ROUNDS" <<'PY'
import json, math, statistics, subprocess, sys, time
from datetime import datetime, timezone

out_json, out_md, rounds = sys.argv[1], sys.argv[2], int(sys.argv[3])

nodes = [
    {"name": "mac-mini", "host": "mac-mini", "repo": "/Users/yilinwang/projects/esg-research-toolkit", "wrap": None},
    {"name": "coco", "host": "coco", "repo": "~/projects/esg-research-toolkit", "wrap": None},
    {"name": "windows", "host": "windows-pc", "repo": "/home/wyl26/projects/esg-research-toolkit", "wrap": "wsl bash -lc"},
]


def run(cmd):
    st = time.perf_counter()
    p = subprocess.run(cmd, text=True, capture_output=True)
    dur = time.perf_counter() - st
    return {
        "cmd": " ".join(cmd),
        "exit": p.returncode,
        "duration_sec": round(dur, 3),
        "stdout": p.stdout[-1200:],
        "stderr": p.stderr[-1200:],
    }


def p95(vals):
    vals = sorted(vals)
    idx = max(0, math.ceil(0.95 * len(vals)) - 1)
    return vals[idx]


def stats(vals):
    if not vals:
        return None
    return {
        "n": len(vals),
        "min": round(min(vals), 3),
        "p50": round(statistics.median(vals), 3),
        "p95": round(p95(vals), 3),
        "max": round(max(vals), 3),
        "avg": round(sum(vals) / len(vals), 3),
    }

results = {"ts_utc": datetime.now(timezone.utc).isoformat(), "rounds": rounds, "nodes": {}}

for node in nodes:
    name = node["name"]
    host = node["host"]
    repo = node["repo"]
    wrap = node["wrap"]

    rounds_data = []
    metric_ok = {"ssh_ping": [], "shell_ping": [], "git_status": [], "codex_version": [], "codex_exec_probe": []}
    failures = {k: 0 for k in metric_ok}

    for i in range(1, rounds + 1):
        if wrap:
            shell_ping = run(["ssh", host, f"{wrap} 'echo shell-ping'"])
            git_status = run(["ssh", host, f"{wrap} 'cd {repo} && git status -sb'"])
            codex_version = run(["ssh", host, f"{wrap} 'codex --version'"])
            codex_probe = run(["ssh", host, f"{wrap} 'cd {repo} && codex exec --dangerously-bypass-approvals-and-sandbox \"reply with exactly: PERF_OK\"'"])
        else:
            shell_ping = run(["ssh", host, "echo shell-ping"])
            git_status = run(["ssh", host, f"cd {repo} && git status -sb"])
            codex_version = run(["ssh", host, "codex --version"])
            codex_probe = run(["ssh", host, f"cd {repo} && codex exec --dangerously-bypass-approvals-and-sandbox \"reply with exactly: PERF_OK\""])

        round_obj = {
            "round": i,
            "ssh_ping": run(["ssh", host, "echo ping"]),
            "shell_ping": shell_ping,
            "git_status": git_status,
            "codex_version": codex_version,
            "codex_exec_probe": codex_probe,
        }

        for k, v in round_obj.items():
            if k == "round":
                continue
            if v["exit"] == 0:
                metric_ok[k].append(v["duration_sec"])
            else:
                failures[k] += 1

        rounds_data.append(round_obj)

    summary = {k: stats(v) for k, v in metric_ok.items()}
    results["nodes"][name] = {"summary": summary, "failures": failures, "rounds": rounds_data}

with open(out_json, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

lines = []
lines.append(f"# Node Compare Light ({results['ts_utc']})")
lines.append("")
lines.append(f"Rounds: {rounds}")
lines.append("")
lines.append("| node | metric | p50(s) | p95(s) | avg(s) | failures |")
lines.append("|---|---|---:|---:|---:|---:|")
for node_name, node_data in results["nodes"].items():
    for metric, s in node_data["summary"].items():
        if s is None:
            lines.append(f"| {node_name} | {metric} | - | - | - | {node_data['failures'][metric]} |")
        else:
            lines.append(f"| {node_name} | {metric} | {s['p50']} | {s['p95']} | {s['avg']} | {node_data['failures'][metric]} |")

with open(out_md, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print(out_json)
print(out_md)
PY

echo "[done] wrote:"
echo "  $OUT_JSON"
echo "  $OUT_MD"

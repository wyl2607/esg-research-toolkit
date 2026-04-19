#!/usr/bin/env bash
# dispatch_remote_codex.sh — ESG-Research-Toolkit 远端 Codex 单任务分发器
#
# 用途：把一个 CR 级整改 prompt 发到指定内网节点（mac-mini / coco / usa-vps），
#      等 Codex 执行完后回收 commit SHA + test summary，写入 runtime/ai-trace/。
#
# 遵循 docs/policies/project-consistency-rules.md §6 远程分发前置准则：
#   1) 同步 HEAD；2) 依赖一致；3) worktree 隔离；4) 回传路径；5) 合并审核
#
# Usage:
#   ./scripts/automation/dispatch_remote_codex.sh <host> <task_id> <prompt_file>
#
# Example:
#   ./scripts/automation/dispatch_remote_codex.sh coco CR-02 prompts/cr-02.txt
#
set -euo pipefail

HOST="${1:?usage: $0 <host> <task_id> <prompt_file>}"
TASK_ID="${2:?missing task_id}"
PROMPT_FILE="${3:?missing prompt_file}"

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

[[ -f "$PROMPT_FILE" ]] || { echo "prompt file not found: $PROMPT_FILE" >&2; exit 2; }

TS="$(date -u +%Y%m%dT%H%M%SZ)"
TRACE_DIR="$REPO_ROOT/runtime/ai-trace"
mkdir -p "$TRACE_DIR"
TRACE_FILE="$TRACE_DIR/remote-roundtrip-${TASK_ID}-${HOST}-${TS}.json"

LOCAL_HEAD="$(git rev-parse HEAD)"
echo "[local] HEAD=$LOCAL_HEAD"

# --- §6.1 HEAD sync precondition --------------------------------------------
REMOTE_HEAD="$(ssh -o ConnectTimeout=5 "$HOST" \
  "cd ~/projects/esg-research-toolkit && git fetch --quiet origin && git rev-parse HEAD" 2>/dev/null || echo "UNKNOWN")"
echo "[$HOST] HEAD=$REMOTE_HEAD"

if [[ "$REMOTE_HEAD" != "$LOCAL_HEAD" ]]; then
  echo "[gate] remote HEAD != local; attempting fast-forward pull on $HOST ..." >&2
  ssh "$HOST" "cd ~/projects/esg-research-toolkit && git pull --ff-only origin main" || {
    echo "[abort] $HOST cannot fast-forward to $LOCAL_HEAD" >&2
    exit 3
  }
  REMOTE_HEAD="$(ssh "$HOST" 'cd ~/projects/esg-research-toolkit && git rev-parse HEAD')"
  [[ "$REMOTE_HEAD" == "$LOCAL_HEAD" ]] || { echo "[abort] post-pull HEAD mismatch" >&2; exit 3; }
fi

# --- Dispatch prompt --------------------------------------------------------
PROMPT_CONTENT="$(cat "$PROMPT_FILE")"
echo "[dispatch] $TASK_ID -> $HOST ($(wc -c < "$PROMPT_FILE") bytes)"

START_EPOCH="$(date +%s)"
set +e
REMOTE_OUT="$(ssh "$HOST" "cd ~/projects/esg-research-toolkit && codex exec --dangerously-bypass-approvals-and-sandbox -C . \
  \"[TASK=$TASK_ID] $PROMPT_CONTENT\" 2>&1")"
REMOTE_EXIT=$?
set -e
END_EPOCH="$(date +%s)"
DURATION=$((END_EPOCH - START_EPOCH))

# --- Collect remote git state ----------------------------------------------
REMOTE_POST_HEAD="$(ssh "$HOST" 'cd ~/projects/esg-research-toolkit && git rev-parse HEAD' 2>/dev/null || echo "UNKNOWN")"
REMOTE_STATUS="$(ssh "$HOST" 'cd ~/projects/esg-research-toolkit && git status --porcelain | head -20' 2>/dev/null || true)"

# --- Write trace record (valid JSON via python) -----------------------------
python3 - "$TRACE_FILE" <<PYEOF
import json, os, sys
path = sys.argv[1]
record = {
    "ts": "$TS",
    "task_id": "$TASK_ID",
    "host": "$HOST",
    "local_head": "$LOCAL_HEAD",
    "remote_head_before": "$REMOTE_HEAD",
    "remote_head_after": "$REMOTE_POST_HEAD",
    "exit_code": $REMOTE_EXIT,
    "duration_seconds": $DURATION,
    "prompt_file": "$PROMPT_FILE",
    "remote_status_porcelain": """$REMOTE_STATUS""",
    "codex_output_tail": """$(printf '%s' "$REMOTE_OUT" | tail -c 4000 | python3 -c 'import sys,json;print(json.dumps(sys.stdin.read())[1:-1])')""",
}
with open(path, "w") as f:
    json.dump(record, f, indent=2, ensure_ascii=False)
print(f"[trace] wrote {path}")
PYEOF

echo "[$TASK_ID@$HOST] exit=$REMOTE_EXIT duration=${DURATION}s head_delta=$([[ "$REMOTE_POST_HEAD" != "$REMOTE_HEAD" ]] && echo YES || echo no)"
echo "[trace] $TRACE_FILE"

exit $REMOTE_EXIT

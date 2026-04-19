#!/usr/bin/env bash
# Push-time review guard: scan outgoing commits for local-only files and non-engineering prose.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

BASE_REF="${1:-}"
if [ -z "$BASE_REF" ]; then
  BASE_REF='@{u}'
fi
if ! git rev-parse --verify "$BASE_REF" >/dev/null 2>&1; then
  echo "[guard] base ref not found: $BASE_REF"
  echo "[guard] tip: pass an explicit base, e.g. scripts/review_push_guard.sh origin/main"
  exit 2
fi

RANGE="$BASE_REF..HEAD"
CHANGED_FILES="$(git diff --name-only "$RANGE")"

if [ -z "$CHANGED_FILES" ]; then
  echo "[guard] no outgoing changes"
  exit 0
fi

echo "[guard] scanning range: $RANGE"

FAILED=0

# Worktree 收敛守卫：默认启用，可用 CONVERGE_WORKTREE_GUARD=0 临时关闭。
if [ "${CONVERGE_WORKTREE_GUARD:-1}" = "1" ] && [ -x scripts/automation/converge_worktrees.sh ]; then
  if ! scripts/automation/converge_worktrees.sh --assert-no-lanes --assert-no-lane-artifacts >/tmp/review_push_guard_converge.out 2>&1; then
    echo "[guard][FAIL] worktree converge guard failed"
    cat /tmp/review_push_guard_converge.out
    FAILED=1
  fi
fi

# 文件分区审计：必须归类，且 local-only 变更默认阻断（删除 local 文件允许）
if ! scripts/review_file_zones.sh --range "$RANGE" --block-local; then
  FAILED=1
fi

LOCAL_ONLY_LIST=".guard/local-only-files.txt"
if [ -f "$LOCAL_ONLY_LIST" ]; then
  while IFS= read -r local_only; do
    [ -z "$local_only" ] && continue
    case "$local_only" in
      \#*) continue ;;
    esac
    if printf '%s\n' "$CHANGED_FILES" | grep -Fx "$local_only" >/dev/null 2>&1; then
      # 删除本地专用文件允许推送；其他变更类型阻断。
      if git diff --name-status "$RANGE" -- "$local_only" \
        | grep -E '^(A|M|R|C|T|U|X|B)' >/dev/null 2>&1; then
        echo "[guard][FAIL] local-only file changed in push range: $local_only"
        FAILED=1
      fi
    fi
  done < "$LOCAL_ONLY_LIST"
fi

BLOCKED_PROSE_PATTERNS=(
  "现在你可以睡觉"
  "祝你好梦"
  "联系方式"
  "明天醒来后"
)

for prose in "${BLOCKED_PROSE_PATTERNS[@]}"; do
  if git diff "$RANGE" -- "*.md" "*.txt" \
    | grep -E '^\+' | grep -vE '^\+\+\+' \
    | grep -F "$prose" >/dev/null 2>&1; then
    echo "[guard][FAIL] blocked prose found: $prose"
    FAILED=1
  fi
done

if git diff "$RANGE" \
  | grep -E '^\+' | grep -vE '^\+\+\+' \
  | grep -E "(relay\\.nf\\.video|api\\.longcat\\.chat|ark\\.cn-beijing\\.volces\\.com)" >/dev/null 2>&1; then
  echo "[guard][FAIL] relay/third-party API endpoint found in outgoing changes"
  FAILED=1
fi

if git diff "$RANGE" \
  | grep -E '^\+' | grep -vE '^\+\+\+' \
  | grep -E "OPENAI_BASE_URL\\s*=\\s*https?://" \
  | grep -vE "OPENAI_BASE_URL\\s*=\\s*https://api\\.openai\\.com/v1" >/dev/null 2>&1; then
  echo "[guard][FAIL] OPENAI_BASE_URL must be official endpoint or omitted"
  FAILED=1
fi

EMAIL_REGEX="[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}"

if git diff "$RANGE" \
  | grep -E '^\+' | grep -vE '^\+\+\+' \
  | grep -E "$EMAIL_REGEX" | grep -v "example@" >/dev/null 2>&1; then
  echo "[guard][FAIL] email address detected in outgoing changes"
  FAILED=1
fi

# SSoT consistency guard (docs/policies/project-consistency-rules.md §1).
# CONSISTENCY_GUARD=0 可临时关闭（不建议；违规意味着单一事实源被破坏）。
if [ "${CONSISTENCY_GUARD:-1}" = "1" ] && [ -x scripts/consistency_check.sh ]; then
  if ! scripts/consistency_check.sh >/tmp/review_push_guard_consistency.out 2>&1; then
    echo "[guard][FAIL] SSoT consistency_check.sh reported violations"
    cat /tmp/review_push_guard_consistency.out
    FAILED=1
  fi
fi

if [ "$FAILED" -ne 0 ]; then
  echo "[guard] push review failed"
  exit 1
fi

echo "[guard] push review passed"
exit 0

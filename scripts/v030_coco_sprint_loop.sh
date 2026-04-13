#!/usr/bin/env bash
# v0.3.0 sprint loop for coco build host
# Model: gpt-5.3-codex, reasoning effort: medium

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

RUN_TAG="$(date +%Y%m%d_%H%M%S)"
MAIN_LOG="$LOG_DIR/v030_sprint_${RUN_TAG}.log"
STATUS_LOG="$LOG_DIR/v030_sprint_status_${RUN_TAG}.log"
MAX_RETRIES=3

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" | tee -a "$MAIN_LOG"
}

status() {
  printf '%s\n' "$1" | tee -a "$STATUS_LOG"
}

run_codex_task() {
  local task_id="$1"
  local task_file="$2"
  local retry=1

  local prompt="读取 docs/codex-tasks/${task_file}，
严格按文件中的步骤执行实现与验证。
每个 step 完成后立即运行对应验证命令。
如果失败，按文档自愈流程修复并继续，最多重试 3 次。
任务结束前必须完成文档要求的验证并提交。
最后输出 TASK_${task_id}_DONE。"

  while [ "$retry" -le "$MAX_RETRIES" ]; do
    log "Task ${task_id} attempt ${retry}/${MAX_RETRIES} (${task_file})"
    if codex exec \
      --skip-git-repo-check \
      --dangerously-bypass-approvals-and-sandbox \
      -m gpt-5.3-codex \
      -c model_reasoning_effort='"medium"' \
      "$prompt" 2>&1 | tee -a "$MAIN_LOG"; then
      log "Task ${task_id} SUCCESS"
      status "TASK_${task_id}=SUCCESS"
      return 0
    fi
    log "Task ${task_id} failed on attempt ${retry}"
    retry=$((retry + 1))
    sleep 2
  done

  log "Task ${task_id} FAILED after ${MAX_RETRIES} attempts"
  status "TASK_${task_id}=FAILED"
  return 1
}

run_batch_parallel() {
  local failed=0
  local pids=()
  local labels=()

  while [ "$#" -gt 0 ]; do
    local task_id="$1"
    local task_file="$2"
    shift 2
    (
      run_codex_task "$task_id" "$task_file"
    ) &
    pids+=("$!")
    labels+=("${task_id}:${task_file}")
  done

  local idx=0
  for pid in "${pids[@]}"; do
    if ! wait "$pid"; then
      log "Parallel item FAILED -> ${labels[$idx]}"
      failed=1
    else
      log "Parallel item DONE -> ${labels[$idx]}"
    fi
    idx=$((idx + 1))
  done

  return "$failed"
}

final_verify() {
  local verify_failed=0
  log "Final verification: backend tests"
  if command -v pytest >/dev/null 2>&1; then
    if ! pytest tests/ -v 2>&1 | tee -a "$MAIN_LOG"; then
      verify_failed=1
      status "VERIFY_BACKEND=FAILED"
    else
      status "VERIFY_BACKEND=SUCCESS"
    fi
  else
    log "pytest not found, skip backend verify"
    status "VERIFY_BACKEND=SKIPPED_NO_PYTEST"
  fi

  log "Final verification: frontend build"
  if [ -f "$PROJECT_DIR/frontend/package.json" ]; then
    if ! (cd "$PROJECT_DIR/frontend" && npm run build) 2>&1 | tee -a "$MAIN_LOG"; then
      verify_failed=1
      status "VERIFY_FRONTEND=FAILED"
    else
      status "VERIFY_FRONTEND=SUCCESS"
    fi
  else
    log "frontend/package.json missing, skip frontend verify"
    status "VERIFY_FRONTEND=SKIPPED_NO_FRONTEND"
  fi

  return "$verify_failed"
}

cd "$PROJECT_DIR"
log "=== v0.3.0 sprint start ==="
log "PROJECT_DIR=$PROJECT_DIR"
log "MODEL=gpt-5.3-codex, reasoning=medium"
status "RUN_TAG=$RUN_TAG"
status "MAIN_LOG=$MAIN_LOG"

batch_a_ok=0
batch_b_ok=0
batch_c_ok=0

# Batch A: core chain (19 -> 20 -> 21)
if run_codex_task 19 task_19_us_esg_standard.md \
  && run_codex_task 20 task_20_three_region_comparison.md \
  && run_codex_task 21 task_21_comparison_page.md; then
  batch_a_ok=1
  status "BATCH_A=SUCCESS"
else
  status "BATCH_A=FAILED"
fi

# Batch B: parallel independent tasks (22 + 24)
if run_batch_parallel \
  22 task_22_ui_ux_polish.md \
  24 task_24_pdf_cjk_charts.md; then
  batch_b_ok=1
  status "BATCH_B=SUCCESS"
else
  status "BATCH_B=FAILED"
fi

# Batch C: after A and B
if [ "$batch_a_ok" -eq 1 ] && [ "$batch_b_ok" -eq 1 ]; then
  if run_batch_parallel \
    23 task_23_dashboard_analytics.md \
    25 task_25_company_profile.md \
    26 task_26_api_perf_cache.md; then
    batch_c_ok=1
    status "BATCH_C=SUCCESS"
  else
    status "BATCH_C=FAILED"
  fi
else
  log "Skip Batch C because Batch A/B not fully successful"
  status "BATCH_C=SKIPPED_DEPENDENCY"
fi

if final_verify; then
  status "FINAL_VERIFY=SUCCESS"
else
  status "FINAL_VERIFY=FAILED"
fi

if [ "$batch_a_ok" -eq 1 ] && [ "$batch_b_ok" -eq 1 ] && [ "$batch_c_ok" -eq 1 ]; then
  log "=== v0.3.0 sprint COMPLETE ==="
  status "SPRINT_RESULT=SUCCESS"
  exit 0
fi

log "=== v0.3.0 sprint INCOMPLETE ==="
status "SPRINT_RESULT=INCOMPLETE"
exit 1

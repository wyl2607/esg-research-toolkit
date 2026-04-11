#!/bin/bash
# Codex Loop 自动执行脚本（多 provider 成本优化版）
# 用法: ./scripts/codex_loop.sh [task_number]
#
# Provider 路由策略（按成本从低到高）：
#   简单任务（文档/翻译）  → LongCat-Flash-Chat  (免费)
#   中等任务（单模块实现） → ark-code-latest     (火山，便宜)
#   复杂任务（架构/多文件）→ gpt-5.3-codex       (relay，默认)

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/codex_$(date +%Y%m%d_%H%M%S).log"
MAX_RETRIES=3

# API Keys（从环境变量读取，不硬编码）
VOLC_API_KEY="${VOLC_API_KEY:-}"
LONGCAT_API_KEY="${LONGCAT_API_KEY:-}"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 按复杂度选择 provider
# $1: complexity = simple | medium | complex
build_codex_cmd() {
  local complexity="$1"
  local prompt="$2"

  case "$complexity" in
    simple)
      # 文档、翻译、格式化 → LongCat 免费
      if [ -n "$LONGCAT_API_KEY" ]; then
        log "  [provider] LongCat-Flash-Chat (免费)"
        echo "LONGCAT_API_KEY=$LONGCAT_API_KEY codex exec -m LongCat-Flash-Chat --provider longcat"
      else
        log "  [provider] gpt-5.3-codex (LONGCAT_API_KEY 未设置，回退默认)"
        echo "codex exec"
      fi
      ;;
    medium)
      # 单模块实现、测试编写 → 火山 ark-code-latest
      if [ -n "$VOLC_API_KEY" ]; then
        log "  [provider] ark-code-latest (火山)"
        echo "VOLC_API_KEY=$VOLC_API_KEY codex exec -m ark-code-latest --provider volc"
      else
        log "  [provider] gpt-5.3-codex (VOLC_API_KEY 未设置，回退默认)"
        echo "codex exec"
      fi
      ;;
    complex|*)
      # 架构、多文件重构 → relay 默认
      log "  [provider] gpt-5.3-codex (relay，默认)"
      echo "codex exec"
      ;;
  esac
}

run_task() {
  local task_num="$1"
  local task_name="$2"
  local complexity="$3"   # simple | medium | complex
  local prompt="$4"

  log "=== 开始 Task $task_num: $task_name [${complexity}] ==="

  local retry=0
  while [ $retry -lt $MAX_RETRIES ]; do
    local success=0

    # 根据复杂度和重试次数选择 provider
    if [ $retry -ge 2 ] || [ "$complexity" = "complex" ]; then
      # 重试 2 次后或复杂任务，用默认 relay
      log "  [provider] gpt-5.3-codex (relay，默认)"
      if codex exec "$prompt" 2>&1 | tee -a "$LOG_FILE"; then
        success=1
      fi
    elif [ "$complexity" = "simple" ] && [ -n "$LONGCAT_API_KEY" ]; then
      # 简单任务用 LongCat
      log "  [provider] LongCat-Flash-Chat (免费)"
      if LONGCAT_API_KEY="$LONGCAT_API_KEY" codex exec -m LongCat-Flash-Chat --provider longcat "$prompt" 2>&1 | tee -a "$LOG_FILE"; then
        success=1
      fi
    elif [ "$complexity" = "medium" ] && [ -n "$VOLC_API_KEY" ]; then
      # 中等任务用火山
      log "  [provider] ark-code-latest (火山)"
      if VOLC_API_KEY="$VOLC_API_KEY" codex exec -m ark-code-latest --provider volc "$prompt" 2>&1 | tee -a "$LOG_FILE"; then
        success=1
      fi
    else
      # 回退到默认
      log "  [provider] gpt-5.3-codex (回退默认)"
      if codex exec "$prompt" 2>&1 | tee -a "$LOG_FILE"; then
        success=1
      fi
    fi

    if [ $success -eq 1 ]; then
      log "✓ Task $task_num 完成"
      return 0
    else
      retry=$((retry + 1))
      log "✗ Task $task_num 失败，重试 $retry/$MAX_RETRIES"
      sleep 10
    fi
  done

  log "✗✗✗ Task $task_num 失败，已达最大重试次数，跳过"
  echo "Task $task_num ($task_name) FAILED after $MAX_RETRIES retries" >> "$LOG_DIR/codex_errors.log"
  return 1
}

verify_task() {
  local task_num="$1"
  log "--- 验证 Task $task_num ---"

  case $task_num in
    1)
      if ls "$PROJECT_DIR/docs/USER_GUIDE.md" \
            "$PROJECT_DIR/docs/USER_GUIDE.zh.md" \
            "$PROJECT_DIR/docs/USER_GUIDE.de.md" > /dev/null 2>&1; then
        log "✓ Task 1 验证通过"
        return 0
      else
        log "✗ Task 1 验证失败：用户手册文件缺失"
        return 1
      fi
      ;;
    2)
      if ls "$PROJECT_DIR/examples/mock_esg_data.json" \
            "$PROJECT_DIR/workflows/end_to_end.py" > /dev/null 2>&1; then
        log "✓ Task 2 验证通过"
        return 0
      else
        log "✗ Task 2 验证失败：工作流文件缺失"
        return 1
      fi
      ;;
    3)
      if ls "$PROJECT_DIR/Dockerfile" \
            "$PROJECT_DIR/docker-compose.yml" > /dev/null 2>&1; then
        log "✓ Task 3 验证通过"
        return 0
      else
        log "✗ Task 3 验证失败：Docker 文件缺失"
        return 1
      fi
      ;;
    4)
      if ls "$PROJECT_DIR/.github/workflows/test.yml" \
            "$PROJECT_DIR/.github/workflows/lint.yml" > /dev/null 2>&1; then
        log "✓ Task 4 验证通过"
        return 0
      else
        log "✗ Task 4 验证失败：GitHub Actions 文件缺失"
        return 1
      fi
      ;;
  esac
}

cd "$PROJECT_DIR"

# 格式：task_num | task_name | complexity | prompt
# complexity: simple=文档/翻译, medium=单模块实现, complex=架构/多文件
TASKS=(
  "1|三语言用户手册|simple|读取 docs/codex-tasks/task_01_user_guide.md，按照规格创建三语言用户手册（docs/USER_GUIDE.md 英文、docs/USER_GUIDE.zh.md 中文、docs/USER_GUIDE.de.md 德文）。先读取 main.py 和各模块 api.py 了解实际端点，确保代码示例可运行。"
  "2|模块联动集成|medium|读取 docs/codex-tasks/task_02_integration.md，创建模块联动工作流：1) examples/mock_esg_data.json，2) workflows/end_to_end.py，3) workflows/batch_analysis.py，4) examples/companies/ 下 3 个示例企业数据。先读取 core/schemas.py 了解数据结构。"
  "3|Docker 部署|medium|读取 docs/codex-tasks/task_03_docker.md，创建 Docker 部署配置：1) Dockerfile，2) docker-compose.yml，3) .dockerignore，4) 在三个 README 文件中添加 Docker 部署章节。"
  "4|CI/CD Pipeline|medium|读取 docs/codex-tasks/task_04_cicd.md，创建 GitHub Actions CI/CD：1) .github/workflows/test.yml，2) .github/workflows/lint.yml，3) .github/workflows/docker.yml，4) 在三个 README 文件顶部添加 CI 徽章。"
)

SPECIFIC_TASK="${1:-}"

log "=== ESG Research Toolkit — Codex Loop 开始 ==="
log "日志文件: $LOG_FILE"
log "Provider 状态: VOLC=$([ -n "$VOLC_API_KEY" ] && echo '✓' || echo '✗ 未设置') | LONGCAT=$([ -n "$LONGCAT_API_KEY" ] && echo '✓' || echo '✗ 未设置')"

for task_entry in "${TASKS[@]}"; do
  IFS='|' read -r num name complexity prompt <<< "$task_entry"

  if [ -n "$SPECIFIC_TASK" ] && [ "$num" != "$SPECIFIC_TASK" ]; then
    continue
  fi

  if run_task "$num" "$name" "$complexity" "$prompt"; then
    verify_task "$num"
  fi
done

log "=== 运行最终测试 ==="
if source .venv/bin/activate && pytest tests/ -q 2>&1 | tee -a "$LOG_FILE"; then
  log "✓ 所有测试通过"
else
  log "✗ 测试失败，请检查日志"
fi

log "=== Codex Loop 完成 ==="
log "日志保存在: $LOG_FILE"


verify_task() {
  local task_num="$1"
  log "--- 验证 Task $task_num ---"

  case $task_num in
    1)
      if ls "$PROJECT_DIR/docs/USER_GUIDE.md" \
            "$PROJECT_DIR/docs/USER_GUIDE.zh.md" \
            "$PROJECT_DIR/docs/USER_GUIDE.de.md" > /dev/null 2>&1; then
        log "✓ Task 1 验证通过"
        return 0
      else
        log "✗ Task 1 验证失败：用户手册文件缺失"
        return 1
      fi
      ;;
    2)
      if ls "$PROJECT_DIR/examples/mock_esg_data.json" \
            "$PROJECT_DIR/workflows/end_to_end.py" > /dev/null 2>&1; then
        log "✓ Task 2 验证通过"
        return 0
      else
        log "✗ Task 2 验证失败：工作流文件缺失"
        return 1
      fi
      ;;
    3)
      if ls "$PROJECT_DIR/Dockerfile" \
            "$PROJECT_DIR/docker-compose.yml" > /dev/null 2>&1; then
        log "✓ Task 3 验证通过"
        return 0
      else
        log "✗ Task 3 验证失败：Docker 文件缺失"
        return 1
      fi
      ;;
    4)
      if ls "$PROJECT_DIR/.github/workflows/test.yml" \
            "$PROJECT_DIR/.github/workflows/lint.yml" > /dev/null 2>&1; then
        log "✓ Task 4 验证通过"
        return 0
      else
        log "✗ Task 4 验证失败：GitHub Actions 文件缺失"
        return 1
      fi
      ;;
  esac
}

cd "$PROJECT_DIR"

TASKS=(
  "1|三语言用户手册|task_01_user_guide.md|读取 docs/codex-tasks/task_01_user_guide.md，按照规格创建三语言用户手册（docs/USER_GUIDE.md 英文、docs/USER_GUIDE.zh.md 中文、docs/USER_GUIDE.de.md 德文）。先读取 main.py 和各模块 api.py 了解实际端点，确保代码示例可运行。"
  "2|模块联动集成|task_02_integration.md|读取 docs/codex-tasks/task_02_integration.md，创建模块联动工作流：1) examples/mock_esg_data.json，2) workflows/end_to_end.py，3) workflows/batch_analysis.py，4) examples/companies/ 下 3 个示例企业数据。先读取 core/schemas.py 了解数据结构。"
  "3|Docker 部署|task_03_docker.md|读取 docs/codex-tasks/task_03_docker.md，创建 Docker 部署配置：1) Dockerfile，2) docker-compose.yml，3) .dockerignore，4) 在三个 README 文件中添加 Docker 部署章节。"
  "4|CI/CD Pipeline|task_04_cicd.md|读取 docs/codex-tasks/task_04_cicd.md，创建 GitHub Actions CI/CD：1) .github/workflows/test.yml，2) .github/workflows/lint.yml，3) .github/workflows/docker.yml，4) 在三个 README 文件顶部添加 CI 徽章。"
)

SPECIFIC_TASK="${1:-}"

log "=== ESG Research Toolkit — Codex Loop 开始 ==="
log "日志文件: $LOG_FILE"

for task_entry in "${TASKS[@]}"; do
  IFS='|' read -r num name file prompt <<< "$task_entry"

  # 如果指定了特定任务，只执行该任务
  if [ -n "$SPECIFIC_TASK" ] && [ "$num" != "$SPECIFIC_TASK" ]; then
    continue
  fi

  if run_task "$num" "$name" "$file" "$prompt"; then
    verify_task "$num"
  fi
done

# 最终测试
log "=== 运行最终测试 ==="
if source .venv/bin/activate && pytest tests/ -q 2>&1 | tee -a "$LOG_FILE"; then
  log "✓ 所有测试通过"
else
  log "✗ 测试失败，请检查日志"
fi

log "=== Codex Loop 完成 ==="
log "日志保存在: $LOG_FILE"

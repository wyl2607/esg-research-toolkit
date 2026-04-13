#!/bin/bash
# Git 提交前安全检查脚本
# 防止敏感信息和个人配置泄露

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "🔒 开始安全检查..."

STAGED_FILES="$(git diff --cached --name-only)"

# 检查是否有敏感文件被暂存
SENSITIVE_PATTERNS=(
  "\.env$"
  "\.env\.local$"
  "\.env\.production$"
  ".*_key$"
  ".*_secret$"
  ".*token.*"
  "credentials\.json"
  "secrets\.json"
  "\.omx/"
  "\.codex/"
  "\.claude/"
  "PERSONAL_"
  "PRIVATE_"
  "_PRIVATE\."
  "_PERSONAL\."
)

FOUND_SENSITIVE=0

for pattern in "${SENSITIVE_PATTERNS[@]}"; do
  if printf '%s\n' "$STAGED_FILES" | grep -E "$pattern" > /dev/null 2>&1; then
    echo "❌ 发现敏感文件: $(printf '%s\n' "$STAGED_FILES" | grep -E "$pattern")"
    FOUND_SENSITIVE=1
  fi
done

# 本地专用文件黑名单（禁止提交到远端）
LOCAL_ONLY_LIST=".guard/local-only-files.txt"
if [ -f "$LOCAL_ONLY_LIST" ]; then
  while IFS= read -r local_only; do
    [ -z "$local_only" ] && continue
    case "$local_only" in
      \#*) continue ;;
    esac
    if printf '%s\n' "$STAGED_FILES" | grep -Fx "$local_only" > /dev/null 2>&1; then
      # 删除本地专用文件（D）是允许的；新增/修改/重命名不允许。
      local_status="$(git diff --cached --name-status -- "$local_only" | awk 'NR==1 {print $1}')"
      if [ -n "$local_status" ] && [ "$local_status" != "D" ]; then
        echo "❌ 本地专用文件禁止提交: $local_only (status=$local_status)"
        FOUND_SENSITIVE=1
      fi
    fi
  done < "$LOCAL_ONLY_LIST"
fi

# 检查是否有 API key 在代码中（检查常见代码/配置/脚本文件，不检查文档）
if git diff --cached -- "*.py" "*.toml" "*.yaml" "*.yml" "*.json" "*.sh" \
  | grep -E '^\+' | grep -vE '^\+\+\+' \
  | grep -iE "(api[_-]?key|secret[_-]?key|openai[_-]?key|anthropic[_-]?key)\s*=\s*['\"][a-zA-Z0-9_\-]{20,}" > /dev/null 2>&1; then
  echo "❌ 发现可能的 API key 硬编码（代码/配置/脚本文件）"
  git diff --cached -- "*.py" "*.toml" "*.yaml" "*.yml" "*.json" "*.sh" \
    | grep -E '^\+' | grep -vE '^\+\+\+' \
    | grep -iE "(api[_-]?key|secret[_-]?key)" | head -5
  FOUND_SENSITIVE=1
fi

# GitHub 策略：禁止提交中转/第三方 API 端点
if git diff --cached \
  | grep -E '^\+' | grep -vE '^\+\+\+' \
  | grep -E "(relay\\.nf\\.video|api\\.longcat\\.chat|ark\\.cn-beijing\\.volces\\.com)" > /dev/null 2>&1; then
  echo "❌ 检测到中转/第三方 API 端点，禁止提交到 GitHub"
  git diff --cached \
    | grep -E '^\+' | grep -vE '^\+\+\+' \
    | grep -E "(relay\\.nf\\.video|api\\.longcat\\.chat|ark\\.cn-beijing\\.volces\\.com)" | head -5
  FOUND_SENSITIVE=1
fi

# GitHub 策略：OPENAI_BASE_URL 如出现 URL，仅允许官方端点
if git diff --cached \
  | grep -E '^\+' | grep -vE '^\+\+\+' \
  | grep -E "OPENAI_BASE_URL\\s*=\\s*https?://" \
  | grep -vE "OPENAI_BASE_URL\\s*=\\s*https://api\\.openai\\.com/v1" > /dev/null 2>&1; then
  echo "❌ OPENAI_BASE_URL 仅允许官方端点 https://api.openai.com/v1"
  git diff --cached \
    | grep -E '^\+' | grep -vE '^\+\+\+' \
    | grep -E "OPENAI_BASE_URL\\s*=\\s*https?://" \
    | grep -vE "OPENAI_BASE_URL\\s*=\\s*https://api\\.openai\\.com/v1" | head -5
  FOUND_SENSITIVE=1
fi

# 阻断非工程化/私人化文案，避免误推送到仓库
BLOCKED_PROSE_PATTERNS=(
  "现在你可以睡觉"
  "祝你好梦"
  "联系方式"
  "明天醒来后"
)

for prose in "${BLOCKED_PROSE_PATTERNS[@]}"; do
  if git diff --cached -- "*.md" "*.txt" \
    | grep -E '^\+' | grep -vE '^\+\+\+' \
    | grep -F "$prose" > /dev/null 2>&1; then
    echo "❌ 检测到非工程化文案，禁止提交: $prose"
    FOUND_SENSITIVE=1
  fi
done

# 检查是否有邮箱地址（仅允许示例邮箱）
EMAIL_REGEX="[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}"

if git diff --cached \
  | grep -E '^\+' | grep -vE '^\+\+\+' \
  | grep -E "$EMAIL_REGEX" | grep -v "example@" > /dev/null 2>&1; then
  echo "❌ 发现邮箱地址，请改为 issue 链接或示例邮箱"
  git diff --cached \
    | grep -E '^\+' | grep -vE '^\+\+\+' \
    | grep -E "$EMAIL_REGEX" | grep -v "example@" | head -3
  FOUND_SENSITIVE=1
fi

# 检查是否有 IP 地址或内网地址
if git diff --cached \
  | grep -E '^\+' | grep -vE '^\+\+\+' \
  | grep -E "192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\." > /dev/null 2>&1; then
  echo "⚠️  发现内网 IP 地址，请确认是否需要脱敏"
  git diff --cached \
    | grep -E '^\+' | grep -vE '^\+\+\+' \
    | grep -E "192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\." | head -3
fi

# 检查是否有绝对路径（可能泄露用户名）
if git diff --cached \
  | grep -E '^\+' | grep -vE '^\+\+\+' \
  | grep -E "/Users/[^/]+/" | grep -v "/Users/yumei/" > /dev/null 2>&1; then
  echo "⚠️  发现其他用户的绝对路径"
  git diff --cached \
    | grep -E '^\+' | grep -vE '^\+\+\+' \
    | grep -E "/Users/[^/]+/" | grep -v "/Users/yumei/" | head -3
fi

if [ $FOUND_SENSITIVE -eq 1 ]; then
  echo ""
  echo "❌ 安全检查失败！发现敏感信息。"
  echo "请移除敏感文件后再提交。"
  echo ""
  echo "如果确认要提交，使用: git commit --no-verify"
  exit 1
fi

echo "✅ 安全检查通过"
exit 0

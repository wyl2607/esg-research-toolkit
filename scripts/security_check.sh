#!/bin/bash
# Git 提交前安全检查脚本
# 防止敏感信息和个人配置泄露

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "🔒 开始安全检查..."

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
  if git diff --cached --name-only | grep -E "$pattern" > /dev/null 2>&1; then
    echo "❌ 发现敏感文件: $(git diff --cached --name-only | grep -E "$pattern")"
    FOUND_SENSITIVE=1
  fi
done

# 检查是否有 API key 在代码中（只检查 .py 文件，不检查文档）
if git diff --cached -- "*.py" | grep -iE "(api[_-]?key|secret[_-]?key|openai[_-]?key|anthropic[_-]?key)\s*=\s*['\"][a-zA-Z0-9_\-]{20,}" > /dev/null 2>&1; then
  echo "❌ 发现可能的 API key 硬编码（Python 文件）"
  git diff --cached -- "*.py" | grep -iE "(api[_-]?key|secret[_-]?key)" | head -5
  FOUND_SENSITIVE=1
fi

# 检查是否有邮箱地址（除了示例邮箱）
if git diff --cached | grep -E "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" | grep -v "wyl2607@gmail.com" | grep -v "example@" > /dev/null 2>&1; then
  echo "⚠️  发现新的邮箱地址，请确认是否需要脱敏"
  git diff --cached | grep -E "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" | grep -v "wyl2607@gmail.com" | head -3
fi

# 检查是否有 IP 地址或内网地址
if git diff --cached | grep -E "192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\." > /dev/null 2>&1; then
  echo "⚠️  发现内网 IP 地址，请确认是否需要脱敏"
  git diff --cached | grep -E "192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\." | head -3
fi

# 检查是否有绝对路径（可能泄露用户名）
if git diff --cached | grep -E "/Users/[^/]+/" | grep -v "/Users/yumei/" > /dev/null 2>&1; then
  echo "⚠️  发现其他用户的绝对路径"
  git diff --cached | grep -E "/Users/[^/]+/" | grep -v "/Users/yumei/" | head -3
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

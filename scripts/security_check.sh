#!/bin/bash
# Git 提交前安全检查脚本：防止敏感信息和个人配置泄露。
# 与 push 门禁（review_push_guard.sh）共享同一套规则：scripts/guard_lib.sh。
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"
# shellcheck source=scripts/guard_lib.sh
source scripts/guard_lib.sh

echo "🔒 开始安全检查..."

GUARD_SCOPE="--cached"
GUARD_MODE_ARGS=("--staged")
GUARD_FAILED=0

guard_subguards
guard_content_all

if [ "$GUARD_FAILED" -ne 0 ]; then
  echo ""
  echo "❌ 安全检查失败！发现敏感信息。"
  echo "请移除敏感文件后再提交。"
  echo ""
  echo "如果确认要提交，使用: git commit --no-verify"
  exit 1
fi

echo "✅ 安全检查通过"
exit 0

#!/usr/bin/env bash
# compliance_check.sh — 上线前合规自动校验
# 用法: bash scripts/compliance_check.sh [--remote]
# --remote: 同时对 https://esg.meichen.beauty 执行线上检查

set -euo pipefail
REMOTE=${1:-""}
BASE_URL="http://localhost:8000"
[[ "$REMOTE" == "--remote" ]] && BASE_URL="https://esg.meichen.beauty/api"

PASS=0; FAIL=0
ok()   { echo "  ✅ $1"; PASS=$((PASS+1)); }
fail() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }
head_check() { echo ""; echo "▶ $1"; }

echo "================================================"
echo " ESG Toolkit — 合规检查清单"
echo " Target: $BASE_URL"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================"

# ── 1. 文件层面 ───────────────────────────────────────────────────────────
head_check "1. 合规文件"
[ -f NOTICE.md ] && ok "NOTICE.md 存在" || fail "NOTICE.md 缺失"
[ -f LICENSE ]   && ok "LICENSE 存在"   || fail "LICENSE 缺失（建议 MIT）"
grep -q "source_url"     report_parser/storage.py 2>/dev/null \
                         && ok "storage.py 含 source_url 字段"  || fail "source_url 字段缺失"
grep -q "file_hash"      report_parser/storage.py 2>/dev/null \
                         && ok "storage.py 含 file_hash 字段"   || fail "file_hash 字段缺失"
grep -q "deletion_requested" report_parser/storage.py 2>/dev/null \
                         && ok "storage.py 含 deletion_requested" || fail "deletion_requested 字段缺失"
grep -q "request-deletion" report_parser/api.py 2>/dev/null \
                         && ok "删除请求 API 端点存在"  || fail "删除请求 API 端点缺失"

# ── 2. PDF 不对外公开 ─────────────────────────────────────────────────────
head_check "2. PDF 访问控制（原始文件不可公开下载）"
grep -r "StaticFiles\|mount.*reports\|FileResponse.*reports" main.py report_parser/ 2>/dev/null \
    | grep -v "^#" | grep -q "." \
    && fail "发现 data/reports/ 静态挂载——PDF 可能被公开访问！" \
    || ok "data/reports/ 未挂载为静态目录"

# Nginx 层面：确认没有暴露 /data/ 路径
if [ -f /etc/nginx/sites-enabled/esg.conf ]; then
    grep -q "location.*data" /etc/nginx/sites-enabled/esg.conf \
        && fail "nginx 存在 /data/ location，请确认是否暴露 PDF" \
        || ok "nginx 无 /data/ 暴露配置"
fi

# ── 3. API 端点验证 ───────────────────────────────────────────────────────
head_check "3. 关键 API 端点"
if command -v curl &>/dev/null; then
    status=$(curl -sf -o /dev/null -w "%{http_code}" "$BASE_URL/health" 2>/dev/null || echo "000")
    [ "$status" = "200" ] && ok "健康检查端点 /health → 200" || fail "/health 返回 $status"

    status=$(curl -sf -o /dev/null -w "%{http_code}" "$BASE_URL/frameworks/list" 2>/dev/null || echo "000")
    [ "$status" = "200" ] && ok "框架列表 /frameworks/list → 200" || fail "/frameworks/list 返回 $status"

    # 确认 PDF 路径不可访问
    status=$(curl -sf -o /dev/null -w "%{http_code}" "$BASE_URL/../data/reports/" 2>/dev/null || echo "000")
    [ "$status" != "200" ] && ok "data/reports/ 路径不可通过 API 访问（$status）" \
        || fail "data/reports/ 可通过 API 访问！"
fi

# ── 4. 数据库检查 ─────────────────────────────────────────────────────────
head_check "4. 数据库 schema"
if [ -f data/esg_toolkit.db ]; then
    cols=$(python3 -c "
import sqlite3
conn = sqlite3.connect('data/esg_toolkit.db')
cols = [r[1] for r in conn.execute(\"PRAGMA table_info(company_reports)\")]
print(','.join(cols))
" 2>/dev/null || echo "")
    echo "  columns: $cols"
    echo "$cols" | grep -q "source_url"          && ok "DB: source_url 列存在"     || fail "DB: source_url 列缺失（需迁移）"
    echo "$cols" | grep -q "file_hash"            && ok "DB: file_hash 列存在"      || fail "DB: file_hash 列缺失（需迁移）"
    echo "$cols" | grep -q "deletion_requested"   && ok "DB: deletion_requested 存在" || fail "DB: deletion_requested 缺失（需迁移）"
else
    echo "  ℹ️  本地 DB 不存在（跳过 schema 检查）"
fi

# ── 5. 待删除记录检查 ─────────────────────────────────────────────────────
head_check "5. 待处理删除请求"
if [ -f data/esg_toolkit.db ]; then
    count=$(python3 -c "
import sqlite3
conn = sqlite3.connect('data/esg_toolkit.db')
try:
    row = conn.execute(\"SELECT COUNT(*) FROM company_reports WHERE deletion_requested=1\").fetchone()
    print(row[0])
except:
    print(0)
" 2>/dev/null || echo "0")
    [ "$count" -eq 0 ] && ok "无待处理删除请求" \
        || fail "有 $count 条待处理删除请求！请尽快处理。"
fi

# ── 结果 ─────────────────────────────────────────────────────────────────
echo ""
echo "================================================"
echo " 结果：✅ $PASS 通过   ❌ $FAIL 失败"
echo "================================================"
[ $FAIL -eq 0 ] && exit 0 || exit 1

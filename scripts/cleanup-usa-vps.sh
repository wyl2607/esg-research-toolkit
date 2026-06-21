#!/usr/bin/env bash
# cleanup-usa-vps.sh - 清理 USA VPS 磁盘空间
#
# DESTRUCTIVE: runs `rm -rf` and `docker system prune --volumes` on a REMOTE host.
# Target host is the SSH alias in $SSH_HOST (default: usa-vps). Override with
#   SSH_HOST=other-host bash scripts/cleanup-usa-vps.sh
# Skip the interactive prompt for automation with FORCE=1 or --yes.

set -euo pipefail

SSH_HOST="${SSH_HOST:-usa-vps}"
FORCE="${FORCE:-0}"
[ "${1:-}" = "--yes" ] && FORCE=1

# Confirm exactly which machine we are about to wipe data on.
echo "=== USA VPS 磁盘清理 ==="
echo "目标主机 (SSH_HOST): $SSH_HOST"
RESOLVED_HOST="$(ssh -o BatchMode=yes -o ConnectTimeout=10 "$SSH_HOST" 'hostname; echo "  uptime:"; uptime' 2>/dev/null)" || {
    echo "ERROR: cannot reach SSH host '$SSH_HOST'. Check your ~/.ssh/config." >&2
    exit 1
}
echo "已连接到: $RESOLVED_HOST"

if [ "$FORCE" != "1" ]; then
    printf "这将在 '%s' 上永久删除数据并清理 Docker 卷。输入 'yes' 继续: " "$SSH_HOST"
    read -r reply
    if [ "$reply" != "yes" ]; then
        echo "已取消。"
        exit 0
    fi
fi

echo "开始时间: $(date)"

# 1. 清理 photos 备份（最大占用 12GB）
echo "→ 移除 photos 备份（12GB）"
ssh "$SSH_HOST" "rm -rf /opt/backups/photos"

# 2. 清理重复的 meichen-web 目录
echo "→ 清理重复的 meichen-web 目录"
ssh "$SSH_HOST" "rm -rf /opt/meichen-web-live"  # 1.3GB
ssh "$SSH_HOST" "rm -rf /opt/apps/meichen-web"   # 1.7GB

# 3. 清理 codex-projects（应该在 coco 上构建）
echo "→ 清理 codex-projects"
ssh "$SSH_HOST" "rm -rf /opt/codex-projects"  # 1.6GB

# 4. 清理 Docker 未使用的镜像
echo "→ 清理 Docker 缓存"
ssh "$SSH_HOST" "docker system prune -af --volumes"

# 5. 清理 APT 缓存
echo "→ 清理 APT 缓存"
ssh "$SSH_HOST" "apt-get clean && apt-get autoremove -y"

# 6. 清理日志
echo "→ 清理旧日志"
ssh "$SSH_HOST" "journalctl --vacuum-time=7d"
ssh "$SSH_HOST" "find /var/log -name '*.gz' -mtime +7 -delete"

echo ""
echo "=== 清理完成 ==="
ssh "$SSH_HOST" "df -h /"
ssh "$SSH_HOST" "free -h"

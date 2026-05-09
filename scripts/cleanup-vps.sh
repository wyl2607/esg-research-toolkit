#!/usr/bin/env bash
# cleanup-vps.sh - 清理远程 VPS 磁盘空间

set -euo pipefail

: "${ESG_VPS_HOST:?set ESG_VPS_HOST to the deployment host}"

if [ "${CONFIRM_REMOTE_CLEANUP:-}" != "YES" ]; then
  echo "Refusing to run remote cleanup without CONFIRM_REMOTE_CLEANUP=YES"
  exit 2
fi

echo "=== VPS 磁盘清理 ==="
echo "开始时间: $(date)"

# 1. 清理 photos 备份（最大占用 12GB）
echo "→ 移除 photos 备份（12GB）"
ssh "$ESG_VPS_HOST" "rm -rf /opt/backups/photos"

# 2. 清理重复的 meichen-web 目录
echo "→ 清理重复的 meichen-web 目录"
ssh "$ESG_VPS_HOST" "rm -rf /opt/meichen-web-live"  # 1.3GB
ssh "$ESG_VPS_HOST" "rm -rf /opt/apps/meichen-web"   # 1.7GB

# 3. 清理 codex-projects（应该在 coco 上构建）
echo "→ 清理 codex-projects"
ssh "$ESG_VPS_HOST" "rm -rf /opt/codex-projects"  # 1.6GB

# 4. 清理 Docker 未使用的镜像
echo "→ 清理 Docker 缓存"
ssh "$ESG_VPS_HOST" "docker system prune -af --volumes"

# 5. 清理 APT 缓存
echo "→ 清理 APT 缓存"
ssh "$ESG_VPS_HOST" "apt-get clean && apt-get autoremove -y"

# 6. 清理日志
echo "→ 清理旧日志"
ssh "$ESG_VPS_HOST" "journalctl --vacuum-time=7d"
ssh "$ESG_VPS_HOST" "find /var/log -name '*.gz' -mtime +7 -delete"

echo ""
echo "=== 清理完成 ==="
ssh "$ESG_VPS_HOST" "df -h /"
ssh "$ESG_VPS_HOST" "free -h"

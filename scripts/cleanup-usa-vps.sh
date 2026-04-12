#!/usr/bin/env bash
# cleanup-usa-vps.sh - 清理 USA VPS 磁盘空间

set -euo pipefail

echo "=== USA VPS 磁盘清理 ==="
echo "开始时间: $(date)"

# 1. 清理 photos 备份（最大占用 12GB）
echo "→ 移除 photos 备份（12GB）"
ssh usa-vps "rm -rf /opt/backups/photos"

# 2. 清理重复的 meichen-web 目录
echo "→ 清理重复的 meichen-web 目录"
ssh usa-vps "rm -rf /opt/meichen-web-live"  # 1.3GB
ssh usa-vps "rm -rf /opt/apps/meichen-web"   # 1.7GB

# 3. 清理 codex-projects（应该在 coco 上构建）
echo "→ 清理 codex-projects"
ssh usa-vps "rm -rf /opt/codex-projects"  # 1.6GB

# 4. 清理 Docker 未使用的镜像
echo "→ 清理 Docker 缓存"
ssh usa-vps "docker system prune -af --volumes"

# 5. 清理 APT 缓存
echo "→ 清理 APT 缓存"
ssh usa-vps "apt-get clean && apt-get autoremove -y"

# 6. 清理日志
echo "→ 清理旧日志"
ssh usa-vps "journalctl --vacuum-time=7d"
ssh usa-vps "find /var/log -name '*.gz' -mtime +7 -delete"

echo ""
echo "=== 清理完成 ==="
ssh usa-vps "df -h /"
ssh usa-vps "free -h"

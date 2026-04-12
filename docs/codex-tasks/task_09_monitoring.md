# Task 09: 监控和日志配置

**目标**: 配置系统监控、日志收集和告警机制

**优先级**: P1

**预计时间**: 15-20 分钟

---

## 前置条件

- Task 08 已完成（端到端验证通过）
- 服务稳定运行

---

## 任务清单

### 1. 配置 Docker 日志轮转

```bash
ssh usa-vps "cat > /etc/docker/daemon.json << 'EOF'
{
  \"log-driver\": \"json-file\",
  \"log-opts\": {
    \"max-size\": \"10m\",
    \"max-file\": \"3\"
  }
}
EOF"

ssh usa-vps "systemctl restart docker"
```

**验证点**:
```bash
ssh usa-vps "docker info | grep 'Logging Driver'"
```

### 2. 创建日志查看脚本

```bash
ssh usa-vps "cat > /opt/esg-research-toolkit/scripts/logs.sh << 'EOF'
#!/usr/bin/env bash
# logs.sh - 快速查看 ESG Toolkit 日志

echo \"=== Docker Container Logs ===\"
docker compose -f /opt/esg-research-toolkit/docker-compose.prod.yml logs --tail=50

echo -e \"\n=== Nginx Access Log (last 20) ===\"
tail -20 /var/log/nginx/access.log

echo -e \"\n=== Nginx Error Log (last 20) ===\"
tail -20 /var/log/nginx/error.log
EOF"

ssh usa-vps "chmod +x /opt/esg-research-toolkit/scripts/logs.sh"
```

**验证点**:
```bash
ssh usa-vps "/opt/esg-research-toolkit/scripts/logs.sh"
```

### 3. 配置健康检查脚本

```bash
ssh usa-vps "cat > /opt/esg-research-toolkit/scripts/health-check.sh << 'EOF'
#!/usr/bin/env bash
# health-check.sh - 检查 ESG Toolkit 服务健康状态

set -euo pipefail

API_URL=\"http://127.0.0.1:8001/health\"
FRONTEND_URL=\"http://127.0.0.1/\"

echo \"[$(date '+%Y-%m-%d %H:%M:%S')] Starting health check...\"

# 检查 Docker 容器
if ! docker ps | grep -q esg-research-toolkit; then
    echo \"ERROR: Docker container not running\"
    exit 1
fi

# 检查 API
if ! curl -sf \$API_URL > /dev/null; then
    echo \"ERROR: API health check failed\"
    exit 1
fi

# 检查前端
if ! curl -sf \$FRONTEND_URL > /dev/null; then
    echo \"ERROR: Frontend not accessible\"
    exit 1
fi

# 检查磁盘空间
DISK_USAGE=\$(df /opt/esg-data | tail -1 | awk '{print \$5}' | sed 's/%//')
if [ \$DISK_USAGE -gt 80 ]; then
    echo \"WARN: Disk usage at \${DISK_USAGE}%\"
fi

echo \"✓ All checks passed\"
EOF"

ssh usa-vps "chmod +x /opt/esg-research-toolkit/scripts/health-check.sh"
```

**验证点**:
```bash
ssh usa-vps "/opt/esg-research-toolkit/scripts/health-check.sh"
```

### 4. 配置 Cron 定时健康检查

```bash
ssh usa-vps "crontab -l > /tmp/cron.bak 2>/dev/null || true"
ssh usa-vps "echo '*/5 * * * * /opt/esg-research-toolkit/scripts/health-check.sh >> /var/log/esg-health.log 2>&1' | crontab -"
```

**验证点**:
```bash
ssh usa-vps "crontab -l | grep health-check"
```

### 5. 配置 Nginx 访问日志格式

```bash
ssh usa-vps "cat > /etc/nginx/conf.d/log_format.conf << 'EOF'
log_format esg_combined '\$remote_addr - \$remote_user [\$time_local] '
                        '\"\$request\" \$status \$body_bytes_sent '
                        '\"\$http_referer\" \"\$http_user_agent\" '
                        '\$request_time';
EOF"

# 更新 esg.conf 使用新格式
ssh usa-vps "sed -i '/server {/a \    access_log /var/log/nginx/esg-access.log esg_combined;' /etc/nginx/sites-available/esg.conf"
ssh usa-vps "nginx -t && systemctl reload nginx"
```

**验证点**:
```bash
ssh usa-vps "tail -5 /var/log/nginx/esg-access.log"
```

### 6. 创建备份脚本

```bash
ssh usa-vps "cat > /opt/esg-research-toolkit/scripts/backup.sh << 'EOF'
#!/usr/bin/env bash
# backup.sh - 备份 ESG Toolkit 数据

set -euo pipefail

BACKUP_DIR=\"/opt/esg-backups\"
DATE=\$(date +%Y%m%d_%H%M%S)

mkdir -p \$BACKUP_DIR

echo \"[$(date)] Starting backup...\"

# 备份数据库
cp /opt/esg-data/esg_toolkit.db \$BACKUP_DIR/esg_toolkit_\${DATE}.db

# 压缩旧备份（保留最近 7 天）
find \$BACKUP_DIR -name \"*.db\" -mtime +7 -delete

echo \"[$(date)] Backup complete: \$BACKUP_DIR/esg_toolkit_\${DATE}.db\"
EOF"

ssh usa-vps "chmod +x /opt/esg-research-toolkit/scripts/backup.sh"
ssh usa-vps "mkdir -p /opt/esg-backups"
```

**验证点**:
```bash
ssh usa-vps "/opt/esg-research-toolkit/scripts/backup.sh"
ssh usa-vps "ls -lh /opt/esg-backups"
```

### 7. 配置每日自动备份

```bash
ssh usa-vps "echo '0 3 * * * /opt/esg-research-toolkit/scripts/backup.sh >> /var/log/esg-backup.log 2>&1' | crontab -"
```

**验证点**:
```bash
ssh usa-vps "crontab -l | grep backup"
```

### 8. 创建监控仪表板脚本

```bash
ssh usa-vps "cat > /opt/esg-research-toolkit/scripts/status.sh << 'EOF'
#!/usr/bin/env bash
# status.sh - 显示 ESG Toolkit 运行状态

echo \"=== ESG Research Toolkit Status ===\"
echo \"Time: \$(date)\"
echo \"\"

echo \"--- Docker Container ---\"
docker ps --filter name=esg-research-toolkit --format \"table {{.Names}}\t{{.Status}}\t{{.Ports}}\"
echo \"\"

echo \"--- Resource Usage ---\"
docker stats --no-stream --format \"table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\"
echo \"\"

echo \"--- Disk Usage ---\"
df -h /opt/esg-data /opt/esg-reports | tail -2
echo \"\"

echo \"--- Recent Requests (last 10) ---\"
tail -10 /var/log/nginx/esg-access.log 2>/dev/null || echo \"No access log yet\"
echo \"\"

echo \"--- Health Check ---\"
curl -sf http://127.0.0.1:8001/health && echo \"✓ API healthy\" || echo \"✗ API unhealthy\"
EOF"

ssh usa-vps "chmod +x /opt/esg-research-toolkit/scripts/status.sh"
```

**验证点**:
```bash
ssh usa-vps "/opt/esg-research-toolkit/scripts/status.sh"
```

---

## 完成标准

- [ ] Docker 日志轮转配置完成
- [ ] 日志查看脚本可用
- [ ] 健康检查脚本运行正常
- [ ] Cron 定时任务配置成功
- [ ] Nginx 日志格式优化
- [ ] 备份脚本可用
- [ ] 每日自动备份配置完成
- [ ] 监控仪表板脚本可用

---

## 自愈策略

### Cron 任务未执行

```bash
# 检查 cron 服务
ssh usa-vps "systemctl status cron"

# 重启 cron
ssh usa-vps "systemctl restart cron"

# 检查 cron 日志
ssh usa-vps "grep CRON /var/log/syslog | tail -20"
```

### 健康检查脚本失败

```bash
# 手动运行并查看详细输出
ssh usa-vps "bash -x /opt/esg-research-toolkit/scripts/health-check.sh"

# 检查依赖命令
ssh usa-vps "which curl docker df"
```

### 备份失败（磁盘空间不足）

```bash
# 清理旧备份
ssh usa-vps "find /opt/esg-backups -name '*.db' -mtime +3 -delete"

# 清理 Docker 缓存
ssh usa-vps "docker system prune -f"
```

### 日志文件过大

```bash
# 手动轮转日志
ssh usa-vps "logrotate -f /etc/logrotate.d/nginx"

# 清空旧日志
ssh usa-vps "truncate -s 0 /var/log/nginx/esg-access.log.1"
```

---

## 依赖

- Task 08: 端到端功能验证

---

## 后续任务

- 无（部署流程完成）

---

## 运维命令速查

```bash
# 查看实时日志
ssh usa-vps "docker compose -f /opt/esg-research-toolkit/docker-compose.prod.yml logs -f"

# 查看系统状态
ssh usa-vps "/opt/esg-research-toolkit/scripts/status.sh"

# 手动备份
ssh usa-vps "/opt/esg-research-toolkit/scripts/backup.sh"

# 重启服务
ssh usa-vps "docker compose -f /opt/esg-research-toolkit/docker-compose.prod.yml restart"

# 查看健康检查历史
ssh usa-vps "tail -50 /var/log/esg-health.log"
```

# Task 08: 端到端功能验证

**目标**: 验证 ESG Toolkit 核心功能在生产环境正常工作

**优先级**: P0

**预计时间**: 20-30 分钟

---

## 前置条件

- Task 07 已完成（前端和 Nginx 部署完成）
- 网站可通过 `http://esg.meichen.beauty` 或 `https://esg.meichen.beauty` 访问

---

## 任务清单

### 1. 验证前端加载

```bash
# 检查首页
curl -sL http://esg.meichen.beauty | grep -o '<title>.*</title>'

# 检查静态资源
curl -I http://esg.meichen.beauty/assets/index.js
```

**预期**:
- 页面标题包含 "ESG Research Toolkit"
- 静态资源返回 200

### 2. 验证 API 健康检查

```bash
curl -sf http://esg.meichen.beauty/api/health | jq
```

**预期输出**:
```json
{"status":"healthy"}
```

### 3. 测试 PDF 上传功能

**准备测试文件**:
```bash
# 在本地创建一个简单的测试 PDF
echo "Test ESG Report 2024" > /tmp/test_esg.txt
ssh usa-vps "apt-get install -y pandoc texlive-xetex"
ssh usa-vps "echo 'Test ESG Report 2024' | pandoc -o /tmp/test_esg.pdf"
```

**上传测试**:
```bash
ssh usa-vps "curl -X POST http://127.0.0.1:8001/report/upload \
  -F 'file=@/tmp/test_esg.pdf' \
  -F 'company_name=Test Company' \
  -F 'year=2024' | jq"
```

**预期输出**: 返回 200，包含 `company_name`, `year`, `extracted_data` 字段

### 4. 测试 Taxonomy 评分

```bash
ssh usa-vps "curl -X POST http://127.0.0.1:8001/taxonomy/score \
  -H 'Content-Type: application/json' \
  -d '{
    \"company_name\": \"Test Company\",
    \"year\": 2024,
    \"activities\": [
      {\"name\": \"Solar Power\", \"revenue\": 1000000, \"category\": \"renewable_energy\"}
    ]
  }' | jq"
```

**预期输出**: 返回 200，包含 `climate_mitigation`, `climate_adaptation` 等评分

### 5. 测试 LCOE 计算

```bash
ssh usa-vps "curl -X POST http://127.0.0.1:8001/techno/lcoe \
  -H 'Content-Type: application/json' \
  -d '{
    \"capex\": 1000000,
    \"opex_annual\": 50000,
    \"capacity_mw\": 1.0,
    \"capacity_factor\": 0.25,
    \"lifetime_years\": 25,
    \"discount_rate\": 0.08
  }' | jq"
```

**预期输出**: 返回 200，包含 `lcoe`, `npv`, `irr` 字段

### 6. 测试 PDF 报告生成

```bash
ssh usa-vps "curl -X POST http://127.0.0.1:8001/taxonomy/report \
  -H 'Content-Type: application/json' \
  -d '{
    \"company_name\": \"Test Company\",
    \"year\": 2024,
    \"scores\": {
      \"climate_mitigation\": 85,
      \"climate_adaptation\": 70,
      \"water\": 60,
      \"circular_economy\": 75,
      \"pollution\": 65,
      \"biodiversity\": 55
    }
  }' -o /tmp/test_report.pdf"

# 检查生成的 PDF
ssh usa-vps "file /tmp/test_report.pdf"
ssh usa-vps "ls -lh /tmp/test_report.pdf"
```

**预期**:
- 文件类型为 PDF
- 文件大小 > 10KB

### 7. 测试数据库持久化

```bash
# 查询已上传的公司
ssh usa-vps "curl -sf http://127.0.0.1:8001/report/companies | jq"

# 检查数据库文件
ssh usa-vps "ls -lh /opt/esg-data/esg_toolkit.db"
ssh usa-vps "sqlite3 /opt/esg-data/esg_toolkit.db 'SELECT COUNT(*) FROM companies;'"
```

**预期**:
- 返回公司列表（至少包含 Test Company）
- 数据库文件存在且大小 > 0

### 8. 性能和资源检查

```bash
# 检查容器资源占用
ssh usa-vps "docker stats --no-stream"

# 检查磁盘使用
ssh usa-vps "df -h /opt/esg-data /opt/esg-reports"

# 检查内存使用
ssh usa-vps "free -h"
```

**预期**:
- 容器内存占用 < 500MB
- 磁盘剩余空间 > 2GB
- 系统内存剩余 > 500MB

---

## 完成标准

- [ ] 前端页面加载正常
- [ ] API 健康检查通过
- [ ] PDF 上传功能正常
- [ ] Taxonomy 评分计算正确
- [ ] LCOE 计算正确
- [ ] PDF 报告生成成功
- [ ] 数据库持久化正常
- [ ] 系统资源占用合理

---

## 自愈策略

### PDF 上传失败（文件大小限制）

```bash
# 检查 Nginx 配置
ssh usa-vps "grep client_max_body_size /etc/nginx/sites-available/esg.conf"

# 如果限制太小，修改配置
ssh usa-vps "sed -i 's/client_max_body_size.*/client_max_body_size 50M;/' /etc/nginx/sites-available/esg.conf"
ssh usa-vps "nginx -t && systemctl reload nginx"
```

### API 调用超时

```bash
# 检查容器日志
ssh usa-vps "docker compose -f /opt/esg-research-toolkit/docker-compose.prod.yml logs --tail=100"

# 检查 OpenAI API 连通性
ssh usa-vps "curl -I https://api.openai.com/v1/models"

# 重启容器
ssh usa-vps "docker compose -f /opt/esg-research-toolkit/docker-compose.prod.yml restart"
```

### PDF 生成失败（中文字体问题）

```bash
# 安装中文字体
ssh usa-vps "apt-get install -y fonts-noto-cjk"

# 重启容器以加载新字体
ssh usa-vps "docker compose -f /opt/esg-research-toolkit/docker-compose.prod.yml restart"
```

### 数据库锁定

```bash
# 检查数据库文件权限
ssh usa-vps "ls -l /opt/esg-data/esg_toolkit.db"

# 修复权限
ssh usa-vps "chown root:root /opt/esg-data/esg_toolkit.db"
ssh usa-vps "chmod 644 /opt/esg-data/esg_toolkit.db"
```

### 内存不足

```bash
# 清理 Docker 缓存
ssh usa-vps "docker system prune -f"

# 重启容器
ssh usa-vps "docker compose -f /opt/esg-research-toolkit/docker-compose.prod.yml restart"
```

---

## 依赖

- Task 07: 前端构建和部署

---

## 后续任务

- Task 09: 监控和日志配置

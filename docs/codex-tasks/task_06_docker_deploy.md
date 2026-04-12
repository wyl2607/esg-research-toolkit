# Task 06: Docker 容器构建和启动

**目标**: 构建 Docker 镜像并启动 FastAPI 后端服务

**优先级**: P0

**预计时间**: 10-15 分钟

---

## 前置条件

- Task 05 已完成（VPS 环境准备完成）
- `/opt/esg-research-toolkit/.env.prod` 存在且有效

---

## 任务清单

### 1. 验证 Dockerfile 和 docker-compose.prod.yml

```bash
ssh usa-vps "cd /opt/esg-research-toolkit && cat Dockerfile | head -10"
ssh usa-vps "cd /opt/esg-research-toolkit && cat docker-compose.prod.yml"
```

**验证点**: 文件存在且格式正确

### 2. 构建 Docker 镜像

```bash
ssh usa-vps "cd /opt/esg-research-toolkit && docker compose -f docker-compose.prod.yml build --no-cache"
```

**预期输出**: 
- 成功拉取 `python:3.11-slim` 基础镜像
- 安装 requirements.txt 依赖
- 构建完成，无错误

**验证点**:
```bash
ssh usa-vps "docker images | grep esg-research-toolkit"
```

### 3. 启动容器

```bash
ssh usa-vps "cd /opt/esg-research-toolkit && docker compose -f docker-compose.prod.yml up -d"
```

**验证点**:
```bash
ssh usa-vps "docker ps | grep esg-research-toolkit"
```

### 4. 检查容器日志

```bash
ssh usa-vps "docker compose -f /opt/esg-research-toolkit/docker-compose.prod.yml logs --tail=50"
```

**预期输出**:
- Uvicorn 启动成功
- 监听 `0.0.0.0:8000`
- 无 Python 错误

### 5. 健康检查

```bash
ssh usa-vps "curl -sf http://127.0.0.1:8001/health"
```

**预期输出**:
```json
{"status":"healthy"}
```

### 6. 测试 API 端点

```bash
ssh usa-vps "curl -sf http://127.0.0.1:8001/ | jq"
```

**预期输出**: 包含 `message`, `version`, `docs_url` 字段

---

## 完成标准

- [ ] Docker 镜像构建成功
- [ ] 容器启动成功，状态为 `Up`
- [ ] 容器日志无错误
- [ ] `/health` 端点返回 200
- [ ] 根路径 `/` 返回 API 信息

---

## 自愈策略

### 构建失败（依赖安装问题）

```bash
# 检查 requirements.txt 是否存在
ssh usa-vps "cat /opt/esg-research-toolkit/requirements.txt | head -10"

# 如果缺少依赖，手动安装
ssh usa-vps "cd /opt/esg-research-toolkit && docker compose -f docker-compose.prod.yml run --rm api pip install -r requirements.txt"
```

### 容器启动失败（端口占用）

```bash
# 检查端口占用
ssh usa-vps "lsof -i :8001"

# 停止旧容器
ssh usa-vps "docker compose -f /opt/esg-research-toolkit/docker-compose.prod.yml down"

# 重新启动
ssh usa-vps "docker compose -f /opt/esg-research-toolkit/docker-compose.prod.yml up -d"
```

### 健康检查失败

```bash
# 查看详细日志
ssh usa-vps "docker compose -f /opt/esg-research-toolkit/docker-compose.prod.yml logs --tail=100"

# 检查 .env.prod 配置
ssh usa-vps "cat /opt/esg-research-toolkit/.env.prod"

# 重启容器
ssh usa-vps "docker compose -f /opt/esg-research-toolkit/docker-compose.prod.yml restart"
```

### 数据库初始化问题

```bash
# 检查数据目录权限
ssh usa-vps "ls -la /opt/esg-data"

# 如果权限不对，修复
ssh usa-vps "chmod 755 /opt/esg-data && chown -R root:root /opt/esg-data"
```

---

## 依赖

- Task 05: VPS 环境准备

---

## 后续任务

- Task 07: 前端构建和部署

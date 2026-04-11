# Task 3: Docker 部署

**优先级**: 中  
**预计时间**: 2 小时  
**依赖**: Task 2（模块联动）

---

## 目标

让项目可以用 Docker 一键部署，方便在任何环境运行。

## 输出文件

### 1. `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data reports

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. `docker-compose.yml`

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./data:/app/data
      - ./reports:/app/reports
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 3. `.dockerignore`

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
.git/
.env
.omx/
logs/
```

### 4. 更新三个 README 文件

在 README.md、README.zh.md、README.de.md 中添加 Docker 部署章节：

```markdown
## Docker Deployment

### Quick Start
```bash
# Build and run
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Environment Variables
Create a `.env` file:
```
OPENAI_API_KEY=your_key_here
```
```

## 验证标准

- [ ] `docker build -t esg-toolkit .` 成功（无错误）
- [ ] `docker-compose up -d` 启动服务
- [ ] `curl http://localhost:8000/health` 返回 `{"status": "ok"}`
- [ ] 容器重启后数据持久化（volumes 正确挂载）
- [ ] `.env` 中的 OPENAI_API_KEY 正确传递到容器

## 自愈规则

1. 如果 `docker build` 失败：
   - 检查 requirements.txt 是否有不兼容的包
   - 检查 Python 版本是否匹配
   - 尝试添加 `--no-cache` 重新构建

2. 如果容器启动失败：
   - 检查端口 8000 是否被占用（`lsof -i :8000`）
   - 检查 .env 文件是否存在
   - 查看容器日志（`docker-compose logs`）

3. 如果健康检查失败：
   - 检查 uvicorn 是否正常启动
   - 检查数据库初始化是否成功

## 参考文件

- `requirements.txt` — 依赖列表
- `main.py` — 应用入口
- `core/database.py` — 数据库初始化

## Codex 执行命令

```bash
codex exec -m gpt-5.4 \
  --prompt "读取 docs/codex-tasks/task_03_docker.md，创建 Docker 部署配置：1) Dockerfile，2) docker-compose.yml，3) .dockerignore，4) 在三个 README 文件中添加 Docker 部署章节。验证 docker build 成功。"
```

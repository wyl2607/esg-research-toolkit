# Codex 自动化开发 — 快速开始

**项目**: ESG Research Toolkit  
**当前版本**: v0.1.0  
**目标版本**: v0.2.0

---

## 一分钟上手

### 1. 查看任务清单
```bash
cat docs/codex-tasks/TASK_LIST.md
```

### 2. 执行单个任务
```bash
# Task 1: 三语言用户手册
codex exec -m gpt-5.4 \
  --prompt "读取 docs/codex-tasks/task_01_user_guide.md，按照规格创建三语言用户手册。"

# Task 2: 模块联动集成
codex exec -m gpt-5.4 \
  --prompt "读取 docs/codex-tasks/task_02_integration.md，创建模块联动工作流。"
```

### 3. 自动执行所有任务（Loop 模式）
```bash
./scripts/codex_loop.sh
```

### 4. 只执行特定任务
```bash
./scripts/codex_loop.sh 1  # 只执行 Task 1
./scripts/codex_loop.sh 2  # 只执行 Task 2
```

---

## 文件结构

```
docs/codex-tasks/
├── README.md                 # 总指南（你现在看的这个）
├── TASK_LIST.md              # 任务总览
├── task_01_user_guide.md     # Task 1: 用户手册
├── task_02_integration.md    # Task 2: 模块联动
├── task_03_docker.md         # Task 3: Docker
└── task_04_cicd.md           # Task 4: CI/CD

scripts/
└── codex_loop.sh             # Loop 自动执行脚本

logs/
├── codex_YYYYMMDD_HHMMSS.log # 执行日志
└── codex_errors.log          # 错误记录
```

---

## 任务优先级

1. **Task 1** (高) — 三语言用户手册
2. **Task 2** (高) — 模块联动集成
3. **Task 3** (中) — Docker 部署
4. **Task 4** (中) — CI/CD Pipeline

---

## 自愈机制

每个任务失败时会自动：
1. 读取错误信息
2. 检查依赖文件
3. 修复问题
4. 重试（最多 3 次）
5. 记录到 `logs/codex_errors.log`

---

## 验证方法

### Task 1 验证
```bash
ls docs/USER_GUIDE*.md
# 应该看到 3 个文件
```

### Task 2 验证
```bash
# 启动服务器
uvicorn main:app --reload &
sleep 3

# 运行端到端工作流
python workflows/end_to_end.py

# 应该生成报告到 reports/ 目录
```

### Task 3 验证
```bash
docker build -t esg-toolkit .
docker-compose up -d
curl http://localhost:8000/health
docker-compose down
```

### Task 4 验证
```bash
ls .github/workflows/
# 应该看到 test.yml, lint.yml, docker.yml
```

---

## 常见问题

### Q: Codex 找不到命令？
A: 确保已安装 Codex CLI：
```bash
# 检查安装
which codex

# 如果未安装，参考 Codex 文档安装
```

### Q: 任务失败怎么办？
A: 查看日志文件：
```bash
tail -f logs/codex_errors.log
```

### Q: 如何跳过某个任务？
A: 编辑 `scripts/codex_loop.sh`，注释掉对应的任务行。

### Q: 可以并行执行任务吗？
A: 不建议。任务之间有依赖关系，按顺序执行更安全。

---

## 完成后

所有任务完成后：

1. 运行测试
```bash
pytest tests/ -v
```

2. 提交代码
```bash
git add .
git commit -m "feat: v0.2.0 - 用户手册、模块联动、Docker、CI/CD"
git push origin main
```

3. 打 tag
```bash
git tag v0.2.0
git push origin v0.2.0
```

4. 更新 PROJECT_PROGRESS.md

---

## 联系方式

- GitHub: https://github.com/wyl2607/esg-research-toolkit
- Issues: https://github.com/wyl2607/esg-research-toolkit/issues
- Email: wyl2607@gmail.com

# Task List — ESG Research Toolkit

**最后更新**: 2026-04-12  
**版本目标**: v0.2.0

---

## 任务总览

| # | 任务 | 优先级 | 状态 | 依赖 |
|---|------|--------|------|------|
| 1 | 三语言用户手册 | 高 | 待执行 | 无 |
| 2 | 模块联动集成 | 高 | 待执行 | Task 1 |
| 3 | Docker 部署 | 中 | 待执行 | Task 2 |
| 4 | CI/CD Pipeline | 中 | 待执行 | Task 3 |
| 5 | 前端界面 | 低 | 可选 | Task 2 |

---

## 执行顺序

```
Task 1 → Task 2 → Task 3 → Task 4
                ↘
                Task 5（可选，并行）
```

---

## 快速执行命令

### 执行 Task 1（用户手册）
```bash
codex --model gpt-5.4 --approval-policy on-failure \
  --prompt "读取 docs/codex-tasks/task_01_user_guide.md，按照规格创建三语言用户手册。先读取 main.py 和各模块 api.py 了解实际端点。"
```

### 执行 Task 2（模块联动）
```bash
codex --model gpt-5.4 --approval-policy on-failure \
  --prompt "读取 docs/codex-tasks/task_02_integration.md，创建模块联动工作流和示例数据。先读取 core/schemas.py 了解数据结构。"
```

### 执行 Task 3（Docker）
```bash
codex --model gpt-5.4 --approval-policy on-failure \
  --prompt "读取 docs/codex-tasks/task_03_docker.md，创建 Docker 部署配置并更新 README。"
```

### 执行 Task 4（CI/CD）
```bash
codex --model gpt-5.4 --approval-policy on-failure \
  --prompt "读取 docs/codex-tasks/task_04_cicd.md，创建 GitHub Actions 工作流并添加 CI 徽章。"
```

### 一键执行所有任务（Loop 模式）
```bash
./scripts/codex_loop.sh
```

---

## 验证清单

每个任务完成后检查：

### Task 1 验证
```bash
ls docs/USER_GUIDE*.md
# 应该看到：USER_GUIDE.md, USER_GUIDE.zh.md, USER_GUIDE.de.md
```

### Task 2 验证
```bash
ls examples/mock_esg_data.json workflows/end_to_end.py workflows/batch_analysis.py
# 启动服务器后测试
uvicorn main:app --reload &
sleep 3
python workflows/end_to_end.py
```

### Task 3 验证
```bash
docker build -t esg-toolkit . && echo "✓ Docker build OK"
docker-compose up -d && sleep 5
curl http://localhost:8000/health
docker-compose down
```

### Task 4 验证
```bash
ls .github/workflows/
# 应该看到：test.yml, lint.yml, docker.yml
python -c "import yaml; [yaml.safe_load(open(f'.github/workflows/{f}')) for f in ['test.yml','lint.yml','docker.yml']]; print('✓ YAML OK')"
```

---

## 完成标准（v0.2.0）

- [ ] Task 1: 三语言用户手册完整
- [ ] Task 2: 端到端工作流可运行
- [ ] Task 3: Docker 一键部署
- [ ] Task 4: CI/CD 自动测试
- [ ] 所有测试通过（pytest tests/ -v）
- [ ] 代码推送到 GitHub
- [ ] 发布 v0.2.0 tag

---

## 自愈机制

如果任何任务失败：

1. 读取错误信息
2. 检查依赖文件是否存在
3. 修复问题
4. 重新执行（最多 3 次）
5. 如果 3 次后仍失败，记录到 `logs/codex_errors.log` 并跳过

---

## 注意事项

- 所有代码必须遵循第一性原理：直接服务于企业 ESG 分析
- 不添加无关功能
- 保持代码简洁，不加多余注释
- Python 3.11+ 类型注解
- 不使用 Anthropic API，只用 OpenAI

# Codex 任务索引

ESG Research Toolkit VPS 部署任务列表

---

## 任务概览

| 任务 | 文件 | 优先级 | 预计时间 | 状态 |
|------|------|--------|---------|------|
| Task 05 | task_05_vps_prep.md | P0 | 15-20min | 待执行 |
| Task 06 | task_06_docker_deploy.md | P0 | 10-15min | 待执行 |
| Task 07 | task_07_frontend_deploy.md | P0 | 15-20min | 待执行 |
| Task 08 | task_08_e2e_validation.md | P0 | 20-30min | 待执行 |
| Task 09 | task_09_monitoring.md | P1 | 15-20min | 待执行 |

---

## 执行顺序

```
Task 05 (VPS 环境准备)
   ↓
Task 06 (Docker 容器构建)
   ↓
Task 07 (前端和 Nginx 部署)
   ↓
Task 08 (端到端功能验证)
   ↓
Task 09 (监控和日志配置)
```

---

## 如何使用 Codex 执行

### 方法 1: 单任务执行（推荐用于调试）

```bash
cd ~/projects/esg-research-toolkit
codex "执行 docs/codex-tasks/task_05_vps_prep.md，使用自愈 loop 模式"
```

### 方法 2: 批量执行（推荐用于生产）

```bash
cd ~/projects/esg-research-toolkit

# 依次执行所有任务
for task in task_05 task_06 task_07 task_08 task_09; do
  echo "=== 执行 $task ==="
  codex "执行 docs/codex-tasks/${task}_*.md，使用自愈 loop 模式，失败后自动重试 3 次"
  
  # 检查退出码
  if [ $? -ne 0 ]; then
    echo "ERROR: $task 失败，停止执行"
    break
  fi
  
  echo "✓ $task 完成"
  sleep 5
done
```

### 方法 3: 并行执行（仅限独立任务）

⚠️ **注意**: Task 05-09 有依赖关系，不能并行执行

---

## 自愈 Loop 模式说明

每个任务都包含：
- **验证点**: 每步完成后的检查命令
- **预期输出**: 正常情况下应该看到的结果
- **自愈策略**: 遇到常见错误时的自动修复方案

Codex 会：
1. 执行任务步骤
2. 运行验证点检查
3. 如果失败，尝试自愈策略
4. 重试最多 3 次
5. 如果仍失败，记录错误并停止

---

## 前置准备

### 1. 确保 SSH 连接正常

```bash
ssh usa-vps "echo 'SSH OK'"
```

### 2. 准备 OpenAI API Key

Task 05 需要配置 `.env.prod`，请准备好：
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`（可选，默认 https://api.openai.com/v1）
- `OPENAI_MODEL`（可选，默认 gpt-4o-mini）

### 3. 确认 DNS 解析

```bash
nslookup esg.meichen.beauty
```

如果 DNS 未生效，Task 07 的 HTTPS 配置会跳过，需要稍后手动配置。

---

## 完成后验证

所有任务完成后，运行：

```bash
ssh usa-vps "/opt/esg-research-toolkit/scripts/status.sh"
```

应该看到：
- Docker 容器运行中
- API 健康检查通过
- 前端可访问
- 资源占用正常

---

## 故障排查

如果某个任务失败：

1. **查看 Codex 输出日志**，找到失败的具体步骤
2. **手动运行验证点命令**，确认问题
3. **查看任务文件中的自愈策略**，尝试手动修复
4. **重新执行该任务**

常见问题：
- **SSH 连接失败**: 检查 VPS 是否在线，SSH key 是否正确
- **Docker 构建失败**: 检查网络连接，尝试使用国内镜像
- **Nginx 配置错误**: 运行 `nginx -t` 查看详细错误
- **API 健康检查失败**: 查看 Docker 日志，检查 `.env.prod` 配置

---

## 下一步

部署完成后：
- 访问 `https://esg.meichen.beauty` 测试前端
- 上传真实 ESG 报告 PDF 验证功能
- 监控系统资源占用
- 开始多框架支持的设计（EU Taxonomy + CSRC + CSRD）

#!/usr/bin/env bash
# deploy-three-tier-parallel.sh - 三层部署自动化脚本（任务内并发）

set -euo pipefail

cd ~/projects/esg-research-toolkit

echo "=== ESG Toolkit 三层部署 ==="
echo "架构: 本地 → coco (构建) → VPS (生产)"
echo "开始时间: $(date)"
echo ""

# 任务列表
TASKS=(
  "10:配置 coco 环境:task_10_setup_coco.md"
  "11:推送代码到 coco:task_11_push_to_coco.md"
  "12:coco 构建:task_12_build_on_coco.md"
  "13:推送到 VPS:task_13_push_to_vps.md"
  "14:启动 VPS 服务:task_14_start_vps_service.md"
)

# 执行每个任务
for task_info in "${TASKS[@]}"; do
  # 使用 read 分隔字符串
  task_num=$(echo "$task_info" | cut -d':' -f1)
  task_name=$(echo "$task_info" | cut -d':' -f2)
  task_file=$(echo "$task_info" | cut -d':' -f3)

  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "📋 Task $task_num: $task_name"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""

  # 调用 Codex，让它内部并发调用子代理
  codex "执行 docs/codex-tasks/${task_file}。

要求：
1. 使用自愈 loop 模式
2. 对于可以并发的步骤，启动多个子代理并行执行
3. 每个子代理负责独立的子任务
4. 等待所有子代理完成后再继续
5. 如果任何子代理失败，自动重试 3 次
6. 记录每个子代理的执行日志

并发策略：
- Task 10: 可以并发检查环境、安装 Docker、安装 Node.js、配置 SSH
- Task 11: 串行执行（rsync 不适合并发）
- Task 12: 可以并发构建 Docker 镜像和前端（如果 coco 资源足够）
- Task 13: 可以并发推送 Docker 镜像、前端文件、配置文件
- Task 14: 可以并发测试多个 API 端点、配置 Nginx、检查资源

失败重试 3 次，记录详细日志到 logs/task_${task_num}.log"

  EXIT_CODE=$?

  if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "❌ Task $task_num 失败（退出码: $EXIT_CODE）"
    echo "查看日志: logs/task_${task_num}.log"
    echo "停止执行"
    exit 1
  fi

  echo ""
  echo "✅ Task $task_num 完成"
  echo ""
  sleep 3
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 所有任务完成！"
echo "完成时间: $(date)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 最终验证
echo "=== 最终验证 ==="
ssh usa-vps "/opt/esg-research-toolkit/scripts/status.sh"

echo ""
echo "=== 访问地址 ==="
echo "HTTP:  http://esg.meichen.beauty"
echo "HTTPS: https://esg.meichen.beauty"
echo "API:   http://esg.meichen.beauty/api/health"

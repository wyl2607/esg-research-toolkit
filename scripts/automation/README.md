# Automation Toolkit

这里是项目日常开发 / 验证 / 发版用的自动化脚本。目标是少记命令、多复用、出问题能自愈。

## 快速上手（今天就能跑）

```bash
# 1) 一键启前后端（前台，Ctrl+C 停）
scripts/automation/run_fullstack.sh

# 1') 同一个命令，后台跑
scripts/automation/run_fullstack.sh --detach
scripts/automation/run_fullstack.sh --status
scripts/automation/run_fullstack.sh --stop

# 2) 验证整套（pytest + lint + build + smoke），失败自动写 fix-prompt
scripts/automation/auto_fix_smoke.sh
scripts/automation/auto_fix_smoke.sh --backend          # 只验后端
scripts/automation/auto_fix_smoke.sh --frontend         # 只验前端
scripts/automation/auto_fix_smoke.sh --max-rounds 3     # 最多重试 3 轮

# 3) 交互式菜单（查 DB、测 API、跑 pytest、触发 recompute……）
.venv/bin/python scripts/automation/interactive_dev.py
.venv/bin/python scripts/automation/interactive_dev.py --pick db_summary  # 直接跑某项
.venv/bin/python scripts/automation/interactive_dev.py --list              # 列出所有动作

# 4) UI 美学自评（需要前端已启动）
.venv/bin/python scripts/automation/ui_autopolish.py                    # 截图 + critique + 生成 task list
.venv/bin/python scripts/automation/ui_autopolish.py --screenshot-only  # 仅截图，不调用 LLM
.venv/bin/python scripts/automation/ui_autopolish.py --pages /,/taxonomy,/benchmarks

# 5) 压力/烟雾并发测试
scripts/automation/stress_test.sh             # API + 前端全套
scripts/automation/stress_test.sh --quick     # 轻量（10 req）
scripts/automation/stress_test.sh --api-only

# 6) 多 lane 收敛（默认 dry-run，仅做体检）
scripts/automation/converge_worktrees.sh
scripts/automation/converge_worktrees.sh --clean-artifacts
scripts/automation/converge_worktrees.sh --apply --clean-artifacts --remove-worktrees
# 守卫模式：确保没有额外 lane / 没有 lane 重型产物回流
scripts/automation/converge_worktrees.sh --assert-no-lanes --assert-no-lane-artifacts
```

## 脚本清单

| 脚本 | 作用 | 主要输出 |
|---|---|---|
| `run_fullstack.sh` | 启动/停止 uvicorn + vite，含健康检查 | `logs/backend.log`, `logs/frontend.log` |
| `auto_fix_smoke.sh` | 跑完整验证套件，失败生成 Claude/Codex 可直接粘的 fix-prompt | `logs/autofix_prompt_*.md` |
| `interactive_dev.py` | 交互式菜单：DB summary、API health、pytest、trend peek 等 | `logs/interactive_log.md` |
| `ui_autopolish.py` | Playwright 截图 + 视觉 LLM 美学评审 + 生成任务清单 | `screenshots/<ts>/`, `ui_reports/<ts>/critique.md`, `docs/exec-plans/ui_autopolish_tasks.md` |
| `stress_test.sh` | API 并发 + 前端页面可达性扫描 + 限流探测 | `logs/stress_<ts>.md` |
| `converge_worktrees.sh` | lane worktree 体检、产物清理、worktree 回收、分支收敛（默认 dry-run），支持守卫断言防止 lane 膨胀复发 | 终端收敛报告（ahead/behind、dirty、唯一提交） |

## 自测矩阵（5 脚本）

> 目的：每次脚本修改后，有一套固定最小验证动作，避免“脚本在作者机器可跑、在 CI/他人机器不可跑”。

| 脚本 | 最小验证命令 | 深度验证命令 | 通过标准 |
|---|---|---|---|
| `run_fullstack.sh` | `scripts/automation/run_fullstack.sh --detach && scripts/automation/run_fullstack.sh --status && scripts/automation/run_fullstack.sh --stop` | `scripts/automation/run_fullstack.sh --detach && curl -fsS http://127.0.0.1:8000/health && curl -fsS http://127.0.0.1:5173/ > /dev/null && scripts/automation/run_fullstack.sh --stop` | 后端/前端端口可达；`--status` 显示 RUNNING；日志文件生成 |
| `auto_fix_smoke.sh` | `scripts/automation/auto_fix_smoke.sh --backend --max-rounds 1` | `scripts/automation/auto_fix_smoke.sh --max-rounds 1` | backend 模式通过；全量模式失败时生成 `logs/autofix_prompt_*.md` |
| `interactive_dev.py` | `.venv/bin/python scripts/automation/interactive_dev.py --list` | `.venv/bin/python scripts/automation/interactive_dev.py --pick api_health` | `--list` 正常列动作；`--pick` 成功写入 `logs/interactive_log.md` |
| `ui_autopolish.py` | `.venv/bin/python scripts/automation/ui_autopolish.py --screenshot-only --pages /` | `.venv/bin/python scripts/automation/ui_autopolish.py --pages /,/companies` | 截图目录产生；全量模式生成 `ui_reports/<ts>/critique.md` 与任务建议 |
| `stress_test.sh` | `scripts/automation/stress_test.sh --quick` | `scripts/automation/stress_test.sh` | 生成 `logs/stress_<ts>.md`；API 压测 + 页面可达性结果完整 |
| `converge_worktrees.sh` | `scripts/automation/converge_worktrees.sh --assert-no-lanes --assert-no-lane-artifacts` | `scripts/automation/converge_worktrees.sh --apply --clean-artifacts --remove-worktrees` | 守卫模式可直接用于日常/CI 防复发；`--apply` 才执行清理/回收，且会打印每个 lane 的 ahead/behind + dirty |

### CI 对齐

- CI（`.github/workflows/test.yml`）已接入 `run_fullstack.sh` 门控：
  - 创建本地 `.venv` 并安装后端依赖
  - `run_fullstack.sh --detach` 启动全栈
  - 对 `:8000/health` 与 `:5173/` 做硬检查
  - 失败时上传 `scripts/automation/logs/` 作为定位证据

## 常见工作流

### 日常"早上开工"

```bash
scripts/automation/run_fullstack.sh --detach        # 启动服务
.venv/bin/python scripts/automation/interactive_dev.py --pick db_summary
.venv/bin/python scripts/automation/interactive_dev.py --pick trend_peek
```

### "改完代码要交差"

```bash
scripts/automation/auto_fix_smoke.sh --max-rounds 2
# 绿了就可以 commit；红了 logs/autofix_prompt_<ts>.md 粘给 Codex 修
```

### "UI 丑/想让 AI 帮我审美"

```bash
scripts/automation/run_fullstack.sh --detach
.venv/bin/python scripts/automation/ui_autopolish.py
# 看 scripts/automation/ui_reports/<ts>/critique.md
# 任务清单自动追加到 docs/exec-plans/ui_autopolish_tasks.md
# 把 top_3_quick_wins 贴给 Claude 直接改
```

### "发版前最后一遍验证"

```bash
scripts/automation/auto_fix_smoke.sh --max-rounds 1
scripts/automation/stress_test.sh --quick
.venv/bin/python scripts/automation/interactive_dev.py --pick api_health
```

## 环境变量（可选）

| 变量 | 默认值 | 说明 |
|---|---|---|
| `API_BASE` | `http://localhost:8000` | 后端 URL |
| `FRONTEND_URL` | `http://localhost:5173` | 前端 URL |
| `VISION_MODEL` | `$OPENAI_MODEL` | UI autopolish 的评审模型（建议 gpt-4o / gpt-4.1） |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` | 从 `.env` 读取 | 已支持第三方中转站 |

## 设计原则

1. **幂等**：每个脚本重复跑不会破坏状态；`run_fullstack.sh --start` 发现端口已占用会复用
2. **留痕**：所有输出写 `scripts/automation/logs/`，日期时间戳文件名
3. **可拼接**：脚本间输出尽量结构化（markdown / JSON），便于喂给 LLM
4. **自愈友好**：出错时生成"可粘贴给 AI 的 prompt"而不是闷声退出

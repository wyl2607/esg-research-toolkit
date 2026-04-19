# ESG Research Toolkit — Project-Level Consistency Rules

**Version**: v1 (2026-04-19)
**Scope**: 所有 AI/人类 贡献者（Claude / Codex / 本地开发）
**Enforcement**: 写入 `scripts/review_push_guard.sh` + `scripts/security_check.sh` + PR review 自动 gate

---

## 1. 单一事实源（SSoT）准则

每个关键概念只能有一个 canonical 定义。下列项目必须遵守：

| 概念 | Canonical 位置 | 禁止重复定义的位置 |
|------|---------------|------------------|
| Framework version 字符串 | `esg_frameworks/schemas.py::FRAMEWORK_VERSIONS` | scorer 文件内的字面量（当前违规：`eu_taxonomy.py` `csrd.py` `csrc_2023.py` `gri_standards.py` `sec_climate.py` `sasb_standards.py`）→ **必须改为 `from .schemas import FRAMEWORK_VERSIONS; framework_version=FRAMEWORK_VERSIONS["<id>"]`** |
| Framework display name | `esg_frameworks/schemas.py::FRAMEWORK_DISPLAY_NAMES` | scorer 文件内的字面量 |
| Benchmark 指标清单 | `benchmark/compute.py::BENCHMARK_METRICS` | 任何重复列表（api/by-industry endpoint 已正确引用） |
| NACE 行业映射 | `frontend/src/lib/nace-codes.ts` | 后端硬编码列表 |
| i18n key namespace | `frontend/src/i18n/locales/{en,de,zh}.json` | 组件内硬编码中文/英文/德文字符串 |
| API response schema | `core/schemas.py` Pydantic 模型 | endpoint handler 内联 dict return（必须用 `response_model=`） |

**违反检测**：`scripts/consistency_check.sh`（待建）grep 硬编码 framework_version 字面量，出现>1次即 fail。

---

## 2. 死代码清除准则

合并新 endpoint/模块时，**必须同时清理被替代的旧路径**。出现孤立/未 include 的 router 文件即违规。

**当前违规清单**：
- `report_parser/industry_routes.py` — T30F 把 `/companies/by-industry` 移到主 router 后未删除。

**Action**: 下一轮任务必须清除或在 `main.py` 重新 include。

---

## 3. i18n 完整性准则

新页面落地时 **必须** 满足：

- [ ] `useTranslation()` 勾子 + `t('<namespace>.<key>')` 取串
- [ ] `en.json / de.json / zh.json` 三语全量 key 齐备
- [ ] 不得在 JSX 字面硬编码中文/德文

**当前覆盖**：14 pages 中 12 使用 i18n。缺口 2 页需补齐（扫描脚本待建）。

---

## 4. 测试矩阵准则

| 层级 | 必选 | 可选 | 禁止 |
|------|------|------|------|
| Backend | `pytest -q`（sqlite in-memory） | schemathesis contract | 真实 OpenAI 调用（用 `dummy` key） |
| Frontend | lint + build + smoke (desktop-chrome) | a11y / mobile-chrome / desktop-firefox | 跳过 `trackBrowserIssues` 断言 |
| E2E 旅程 | 新增用户可见功能必须配 1 个 `workflow-*.spec.ts` | — | 手动测试代替 |

**CI gate**：三项 must-pass，二项可选。

---

## 5. 版本化与可追溯准则

- 任何存入 DB 的"分析结果"必须携带 `framework_version / analyzed_at / stored_at`（已实现）
- Profile 页面每个 framework score 展示 **版本徽章 + 分析时间**（已实现）
- 合并同 framework_id 多次评分时，渲染 key 必须包含 `analyzed_at` 防 React 重复 key（已修复）
- 下一步：为 DB 迁移增加 Alembic 正式迁移（目前 additive runtime migration 是 tech-debt）

---

## 6. 远程分发前置准则（多节点 Codex）

分发任务到 mac-mini / coco / usa-vps 之前 **必须**：

1. **同步 HEAD**：远端 repo 落后任何提交即 abort（`git fetch && git rev-parse HEAD` 校验）
2. **依赖一致**：`requirements.txt` / `package.json` 的 lockfile 与远端 .venv / node_modules 对齐
3. **任务隔离**：每个远端节点在独立 worktree 下工作，不碰 main
4. **回传路径**：commit SHA + test summary 打包写入 `runtime/ai-trace/remote-roundtrip-<ts>.json`
5. **合并审核**：任何远端 commit 合并前由本地 Claude 做 review + 回归跑 `pytest -q + test:smoke`

违反任何一条即不得分发。

---

## 7. 下一步整改任务（自动生成 Codex prompt 种子）

优先级排序（P0 必做）：

1. **CR-01 framework_version 去重**：scorer 文件全部改为从 `schemas.FRAMEWORK_VERSIONS` 读取
2. **CR-02 清理 industry_routes.py**：确认无外部引用后 `git rm`，或恢复 include
3. **CR-03 i18n 缺口**：识别未 i18n 的两页并补齐三语 key
4. **CR-04 Alembic 正式迁移引导**：移除 runtime additive migration，改 `alembic upgrade head`
5. **CR-05 consistency_check.sh 守卫**：把本文件的 SSoT 规则变成 grep-based gate 脚本

每项均可独立分发到一台远端 Codex 节点。建议分配：
- mac-mini → CR-01（熟悉 python scorer 路径）
- coco → CR-02 + CR-03（前端 + python 清理，coco 算力最足）
- usa-vps → CR-05（脚本编写，与运行时解耦）
- CR-04 由本地 Claude 领衔（高风险 DB 迁移，不外包）

---

## 8. 记录与回流

- 本文件修改必须在 `PROJECT_PROGRESS.md` 留一行
- 每次远程分发的 SHA + 结果追加到 `INCIDENT_LOG.md`（若失败）或 `PROJECT_PROGRESS.md` 近期完成表（若成功）
- 跨 AI 账本：`/Users/yumei/tools/automation/runtime/ai-trace/`（遵循 `ai-collaboration-traceability-standard.md`）

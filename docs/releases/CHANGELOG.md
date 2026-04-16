# Changelog

本项目从 `v0.1.0` 开始建立正式版本记录。

记录规则：

- 每天如有可交付变化，更新 `docs/releases/VERSION.md`
- 在本文件追加版本摘要
- 在 `docs/releases/` 下新增同日详细日报

## [0.2.1] - 2026-04-16

### Added

- 多年趋势 3 年回归测试 `test_company_history_three_year_trend_ordering_and_yoy`，守护 `/companies/{name}/history` 排序与 `years_available` 契约。
- `scripts/automation/` 自动化工具链（5 脚本 + README）：`run_fullstack.sh` 全栈启停、`auto_fix_smoke.sh` 自愈式 smoke、`interactive_dev.py` 交互菜单、`ui_autopolish.py` 视觉 LLM 自评审、`stress_test.sh` 并发 + 页面可达性探测。
- `scripts/seed_german_demo.py` 新增 `--only` / `--slug` / `--company` 过滤，便于对单公司做小样本重跑；配套 4 条单测。
- `_upload_evidence_summary` 回退逻辑：优先使用分析器产出的 evidence，缺失时按非空指标填充 placeholder；2 条单测钉死行为。
- 新增版本日报 `docs/releases/2026-04-16-v0.2.1.md`。

### Changed

- `OPENAI_VALIDATION_MODEL` 默认值从 `gpt-4o-mini` 升级到 `gpt-5.4-mini`；seed runbook 文案对齐。
- `phase_b` 在写入 anomalies 报告前丢弃 `"no concern"` 占位 concern，减少噪声。

### Fixed

- `.gitignore` 补齐 `scripts/automation/screenshots/` / `ui_reports/` / `*.png` / `PHASE_*.md`，避免本地运行时产物被意外提交。

### Verified

- `OPENAI_API_KEY=dummy .venv/bin/pytest -q` → `120 passed`
- `scripts/automation/run_fullstack.sh --detach` → backend 8000 + frontend 5173 均 200
- `cd frontend && npm run lint && npm run build` → pass

## [0.2.0] - 2026-04-16

### Added

- 多年趋势数据首轮落地：SAP / BASF / Volkswagen / Deutsche Telekom / RWE 五家公司覆盖 2022–2024。
- Skeleton loader 组件 + BenchmarkPage 渲染体验改进。
- 数据导出 CSV 新增 metadata / Historical Trends 分区与时间戳文件名。
- Company Profile 多年趋势 YoY 卡片可视化。

### Changed

- Audit Trail（PeerComparisonCard）改为 mobile-first 响应式栅格（1 → 2 → 3 列）。
- 数据质量告警组件：趋势数据 < 2 点时显示多语言提示。

### Verified

- `cd frontend && npm run lint && npm run build && npm run test:smoke` → all pass
- benchmark 校验：72 行 0 violations

## [0.1.0] - 2026-04-15

### Added

- Q1-Q7 数据架构硬化首轮完整落地：L0 物理边界校验、ExtractionRun 审计表、verified export/import/sync 流程、nightly burn 维护脚本、上传 PDF 魔数/尺寸校验、batch job TTL 淘汰、Postgres-ready 连接池与迁移/硬化 runbook。
- Company Profile 新增 Source trail，可从页面直接查看 ExtractionRun 审计链路。
- Dashboard 新增 coverage 排序、横向指标卡、可点击字段 drill-down 页面和公司排名表。
- 20 家德国 demo 数据 seed / audit / benchmark 校验链路补齐。
- 新增版本化发布记录机制：`docs/releases/VERSION.md` + `docs/releases/CHANGELOG.md` + `docs/releases/每日版本日报`。

### Changed

- EU Taxonomy `taxonomy_aligned_revenue_pct` / `taxonomy_aligned_capex_pct` 改为支持有符号百分比 `[-100, 100]`。
- thyssenkrupp 2024 CapEx alignment 修复脚本改为恢复披露值 `-9.0`，不再把负值强行归一化为正数。
- ExtractionRun 审计链路从“仅存储层准备好”推进到“脚本写入 + API 暴露 + 前端展示”全链路可追溯。
- 前端版本号从占位的 `0.0.0` 升级到项目首个正式版本 `0.1.0`。

### Fixed

- 修复 dashboard JSX 历史问题与若干前端 lint 问题。
- 修复 CoverageFieldPage 中的 irregular whitespace，恢复 `npm run lint` 通过。
- 修复 upload API 限流回归测试覆盖缺口。
- 修复 thyssenkrupp 负值 Taxonomy 百分比被校验层误判的问题。

### Verified

- `OPENAI_API_KEY=dummy .venv/bin/pytest -q` → `107 passed`
- `cd frontend && npm run lint`
- `cd frontend && npm run build`

### Pending

- 观测性仍是 P2：Sentry / OpenTelemetry 尚未接入。
- Postgres 仅完成 cutover 准备，尚未达到 runbook 定义的迁移触发阈值。
- Vite dynamic-import warning 与 FastAPI `on_event` deprecation 仍为非阻断待办。

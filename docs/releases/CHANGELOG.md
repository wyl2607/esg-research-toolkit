# Changelog

本项目从 `v0.1.0` 开始建立正式版本记录。

记录规则：

- 每天如有可交付变化，更新 `docs/releases/VERSION.md`
- 在本文件追加版本摘要
- 在 `docs/releases/` 下新增同日详细日报

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

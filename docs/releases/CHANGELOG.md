# Changelog

本项目从 `v0.1.0` 开始建立正式版本记录。

记录规则：

- 每天如有可交付变化，更新 `docs/releases/VERSION.md`
- 在本文件追加版本摘要
- 在 `docs/releases/` 下新增同日详细日报

## [0.3.1] - 2026-04-24

### Added

- Production startup guardrails now require the Alembic-managed path for production-oriented startup checks.
- Core module unit tests were expanded for AI client behavior and limiter isolation.
- Additional OpenAPI contract assertions cover request parse failures and production-safety surfaces.

### Changed

- Deployment and CI workflows were tightened around production safety defaults.
- Repository hygiene classification was strengthened so local-only artifacts remain outside the public GitHub surface.
- Generated frontend API types were aligned with the CI dependency set to avoid local/CI OpenAPI drift.
- Dependabot postcss update was merged into the frontend dev dependency set.

### Fixed

- JSON request parse errors are documented as `400` API responses.
- Regex fallback unit conversion normalization was corrected.
- GitHub branch protection now requires the real Actions check run name `leak-guard`, avoiding mismatch with legacy context naming.
- Schemathesis v4 contract workflow and generated type drift blockers were resolved.

### Verified

- Latest `main` head: `e650838f3ac629715dbb94d414b03634a9de2d9f`.
- GitHub Actions on latest `main`: `security-guard`, `Lint`, `API Contracts`, and `Tests` all succeeded.
- Open PR queue drained after PRs #14, #16, #19, #22, #24, and #25 merged or were superseded.

## [0.3.0] - 2026-04-19

### Added

- **F1 CompanyYearPicker**：新增两步联动选择组件（`frontend/src/components/CompanyYearPicker.tsx`），支持公司→年份级联，已导入年份高亮（check 图标），缺失年份直接深链到 `/upload?company=X&year=Y`。Benchmark / Regional / Frameworks / Taxonomy / Upload 5 个页面统一接入。
- **F1 `/report/companies/v2` 端点**：返回 `imported_years[]` 与 `suggested_years[]`，前端通过 `listCompaniesWithYearCoverage()` 消费。
- **F2 PendingDisclosuresPage**：新增 `/disclosures` 路由（`frontend/src/pages/PendingDisclosuresPage.tsx`）+ 侧边栏条目（`nav.pendingDisclosures`），analyst 可在此集中处理所有待审抓取记录。
- **F2 disclosures lane 全链路**：`POST /disclosures/fetch`、`GET /disclosures/pending`、`POST /disclosures/{id}/approve|reject`、`GET /disclosures/lane-stats`；审批走字段级 merge，fetch 失败写 attempted_urls 审计；lane-stats 按近期 evidence 质量推荐来源通道顺序。
- **F2 多来源通道**：`source_hint` / `source_hints` 支持 `company_site` / `sec_edgar` / `hkex` / `csrc` 串行尝试回退，pending evidence 落盘 `lane_stats` + `success_lane`。
- **B-level 多年趋势回填**：`scripts/seed_data/backfill_via_disclosures.py` + `tests/test_backfill_via_disclosures.py`，结合 disclosures lane 将核心公司扩到 ≥3 年历史覆盖（6/5 公司达标）。
- **F3/F4 LCOE 区域化默认**：`LcoePage` 根据 UI 语言自动切换 EUR/USD 币种与默认电价，USD 新增 EIA 美国批发电价参考块（2021-2024）。
- **Playwright 工作流 e2e**：`frontend/tests/workflow-gap-fill.spec.ts` 覆盖"picker 缺失年份 → Upload 深链 → /disclosures 审批 → 公司入库"完整闭环。
- **Automation 保护**：`scripts/automation/converge_worktrees.sh` 增加 `--assert-no-lanes` / `--assert-no-lane-artifacts`，`scripts/review_push_guard.sh` 在推送前调用该 guard；`docs/design-docs/company_year_dual_picker.md` 与 `docs/design-docs/auto_disclosure_fetch.md` 两份设计文档落地。
- 继承自 v0.2.3-beta.1 周期的 Auto Fetch 面板 / source-hint 契约 / README 合规声明。

### Changed

- Frameworks / Taxonomy / Benchmark / Regional / Upload 五页迁移到 CompanyYearPicker；`queryKey` 统一到 `['companies-v2']`。
- `taxonomy_scorer/api.py::_record_to_company_esg()` 在反序列化时同时处理 `primary_activities` 与 `evidence_summary`（修 BASF 2024 500 错误）。
- EU Taxonomy / CSRD / CSRC 2023 scorer 的 `DimensionScore.name` 统一改为稳定 snake_case 键（`climate_mitigation` / `e1_climate` / `csrc_environment` 等），前端按 `frameworks.dim.*` 做 i18n 渲染；`tests/fixtures/company_profile_v1/profile_response.json` 同步更新。
- `main.py` 版本号对齐到 `0.3.0`；侧栏新增 `/disclosures` 快捷入口，Sidebar / App 路由表一致。

### Fixed

- **B1**：Benchmark 页的 NoticeBanner 缺少外部间距 → 包一层 `div.mt-4`。
- **B2**：BASF 2024 触发 500（`ValidationError` on `evidence_summary`）→ 在 record→schema 时反序列化 JSON 字符串列表。
- **B3**：框架雷达图/维度卡片的维度名硬编码中文 → 改为 snake_case key + i18n 查表。
- **B4**：Upload 深链丢失用户上下文 → 识别 `?company=&year=` 后渲染 gap banner。

### Verified

- `OPENAI_API_KEY=dummy .venv/bin/pytest -q` → `163 passed`
- `cd frontend && npm run lint && npm run build` → pass
- `cd frontend && npm run test:smoke` → `26 passed`（含 `workflow-gap-fill.spec.ts`）
- `scripts/seed_data/backfill_via_disclosures.py` → 6/5 公司 ≥3 年 history 覆盖达标。

## [Unreleased-legacy] - 2026-04-18

### Added

- 新增 `report_parser/disclosures_api.py`：`POST /disclosures/fetch` 与 `GET /disclosures/pending`，用于 F2 auto-fetch 队列骨架。
- 新增 `pending_disclosures` 存储模型与 upsert/list 辅助函数，写入 `report_parser/storage.py` 并接入 SQLite schema 自愈。
- Upload 页面新增 Auto Fetch 面板：支持 company/year 预填触发抓取、查看 pending 队列。
- Upload Auto Fetch 面板补充 `source_type` 选择（`pdf` / `html` / `filing`）及三语文案，避免前端请求被硬编码为 PDF。
- Upload Auto Fetch 面板新增 `source_hint` 官方来源通道（`company_site` / `sec_edgar` / `hkex` / `csrc`）选择，支持 analyst 按区域监管来源发起补录。
- Upload Auto Fetch 面板新增“附加来源通道”勾选（multi-source），可一次 fetch 串行尝试多个官方来源。
- Upload Auto Fetch pending 队列新增字段级审核面板：可按指标勾选后再 approve，支持对照当前值/待审值做差异确认。
- `frontend/tests/workflow.spec.ts` 新增 F2 e2e：深链进入 Upload 后触发 auto-fetch 并 approve，断言缺失年份记录可回读。
- README（en/zh/de）补充 Auto-Fetch 合规声明：支持来源、排除来源、User-Agent 标识与 pending 审核入库策略。

### Changed

- Benchmark 页接入 `CompanyYearPicker`，支持从公司+年份上下文快速跳转缺失年份补录路径（D1=b）。
- `core/schemas.py` 新增 disclosure 请求/响应契约，`main.py` 注册 disclosures router。
- 前端 i18n（en/zh/de）补齐 auto-fetch 文案与 backendOffline 英文缺失项。
- `disclosures` 抓取后端改为 source-type aware：默认 `source_url` 与候选 URL 列表按 `source_type` 分支，不再对非 PDF 类型直接短路跳过。
- `disclosures` 请求契约新增 `source_hint`，默认 URL 与候选来源对 hint 做分支回退，同时保留 `source_url` override 优先级。
- `POST /disclosures/{id}/approve` 请求契约新增 `include_metrics`，支持仅合并选中字段；后端按已入库基线+待审 payload 进行字段级合并。
- `disclosures` 官方来源通道（SEC/HKEX/CSRC）默认/候选 URL 统一改为 canonical 公司名 query token，减少 slug 检索导致的无效命中；fetch 失败时把 `attempted_urls` 与尝试次数写入 pending evidence，便于 Upload 审核与排障追踪。
- `disclosures` 请求契约新增 `source_hints`（兼容保留 `source_hint`），支持一次任务按多来源候选列表串行回退尝试。
- `disclosures` pending evidence 新增 `lane_stats`（按来源通道统计 attempted/succeeded/failed）与 `success_lane`，用于 Upload 侧实时展示来源可靠性。
- `tests/test_report_parser.py` 新增参数化回归，锁定 html/filing 默认 URL 生成行为。
- `tests/test_report_parser.py` 增加 source-hint 回归，锁定 SEC/HKEX/CSRC 默认入口与 override 语义。
- `tests/test_report_parser.py` 增加字段级合并回归（selected metrics only）与非法 metric 422 契约校验。
- `tests/test_report_parser.py` 新增回归，锁定 SEC query token 保真与 fetch 失败路径 attempt 审计落盘。
- `frontend/tests/workflow.spec.ts` auto-fetch e2e 新增断言：附加 HKEX 通道后 pending payload 中 `source_hints` 正确落盘。

### Verified

- `OPENAI_API_KEY=dummy .venv/bin/pytest -q` → `161 passed`
- `.venv/bin/ruff check core report_parser taxonomy_scorer esg_frameworks techno_economics benchmark tests main.py --ignore E501` → pass
- `cd frontend && npm run gen:types && npm run lint && npm run build` → pass
- `cd frontend && npm run test:playwright -- tests/workflow.spec.ts` → `8 passed`
- `cd frontend && npx playwright test --config=playwright.config.ts tests/workflow.spec.ts -g "upload auto-fetch can queue and approve a deep-linked missing year"` → `2 passed`
- `cd frontend && npm run test:smoke && npm run test:a11y` → `20 passed`, `10 passed`

## [0.2.3-beta.1] - 2026-04-17

### Added

- 新增后端模型注册中心 `core/models.py`，将 extraction / validation / audit 三类模型配置、fallback 和可用性检查集中管理。
- 新增 `GET /health/models` 运维健康接口，暴露每类模型的当前配置、fallback、availability、检查来源与最近检查时间。
- 新增 `docs/ops/models.md` 与 `docs/ops/data-integrity.md`，把模型配置和数据完整性控制写成面向团队的操作文档。
- 新增 `report_parser/admin_routes.py` 与 `report_parser/industry_routes.py`，把管理/导出与行业查询路由从主 API 中拆出。
- 新增 `tests/test_models_registry.py`，补齐模型健康与 provider/whitelist 回退行为覆盖。

### Changed

- `main.py` 版本号与发布文档正式对齐到 `v0.2.3-beta.1`，避免继续出现运行时版本和 release 元数据不一致。
- `report_parser/api.py`、`taxonomy_scorer/api.py`、`esg_frameworks/api.py` 补齐更多 `response_model` 契约，降低 OpenAPI 漂移风险。
- `report_parser/storage.py` 与 `esg_frameworks/storage.py` 强化唯一性与去重逻辑，为生产环境数据完整性收紧约束。
- `.gitignore` 现忽略 `docs/archive/`，把本地归档材料从 GitHub 发布面移出。

### Fixed

- 修复发布卫生问题：移除会触发安全钩子的本地 archive 产物，恢复远端推送为面向公开仓库的干净状态。
- 修复模型配置分散在多个入口的问题，统一默认模型解析逻辑，减少脚本与 API 之间的配置漂移。

### Verified

- `OPENAI_API_KEY=dummy .venv/bin/pytest -q tests/test_models_registry.py tests/test_openapi_contract.py tests/test_report_parser.py` → `44 passed`
- `OPENAI_API_KEY=dummy .venv/bin/pytest -q tests/test_frameworks_comparison.py tests/test_profile_contract.py tests/test_taxonomy_scorer.py` → `15 passed`

## [0.2.2] - 2026-04-17

### Added

- 9 个 canonical aliases（BMW Group / Deutsche Telekom / Fresenius / Linde / PUMA / RWE / SAP / Volkswagen Group / thyssenkrupp → 对应 canonical name），从根上阻断同一公司被拆成多条记录。
- `/report/upload` 新增可选表单字段 `override_company_name`，允许上传方强制 canonical 名字，不再被 AI extractor 的命名波动污染。
- `scripts/migrate_canonical_company_names.py`：一次性迁移脚本，自动备份 DB → 重写 legacy 行 → 按 `report_quality_score` 去重冲突记录。
- `scripts/dev_tasks/` 五脚本审计工具链（identity audit / seed gap / UI autopolish / migration plan / commit readiness）+ `scripts/comprehensive_health_check.sh` 全流程健康检测。
- 新增 3 个测试文件（`tests/test_company_identity.py`、`tests/test_rate_limit.py`，`tests/test_seed_german_demo.py` 扩展），pytest 127 → 131。
- 新增版本日报 `docs/releases/2026-04-17-v0.2.2.md`。

### Changed

- `scripts/seed_german_demo.py::upload_company()` 现在自动把 manifest 的 `company_name` 作为 `override_company_name` 传给后端，确保 seed 永远落在 canonical 身份。
- `frontend`：Dashboard / Benchmark / LanguageSwitcher 首轮视觉微调（来自 UI autopolish 的 CRITICAL / HIGH 建议）。
- `.gitignore` 扩展 `*.db.bak*` / `*.sqlite*.bak*`，避免 migration 备份被意外 commit。

### Fixed

- 清理孤立测试 drift 行 `Slash/Like Name Co / 2026`（无 PDF / 无 hash / 未来年份，来自历史集成测试 fixture）。
- Migration 去重删除 6 条低质量重复记录（ids 3, 51, 52, 24, 36, 45）。

### Data Impact

- 多年趋势覆盖：**5 家 → 8 家**（BASF / BMW / DHL / Deutsche Telekom / RWE / SAP / Volkswagen 7 家完整 2022-2024，Henkel 2 年）。
- DB 条目：51 → 36（去重后），每条都对应 manifest 中唯一 (company, year)。
- manifest ↔ DB 完美对齐：0 missing, 0 drift。

### Verified

- `OPENAI_API_KEY=dummy .venv/bin/pytest -q` → `131 passed`
- `scripts/dev_tasks/01_company_identity_audit.py` → 0 clusters
- `scripts/dev_tasks/02_seed_gap_analysis.py` → 0 missing, 0 drift
- `scripts/dev_tasks/04_identity_migration_plan.py` → 0 renames needed

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

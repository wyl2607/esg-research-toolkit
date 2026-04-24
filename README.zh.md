# ESG Research Toolkit

🌐 [English](README.md) · [中文](README.zh.md) · [Deutsch](README.de.md)

> 面向企业 ESG 报告分析的开源平台，支持 EU Taxonomy 合规评分、
> 多框架对比（EU Taxonomy 2020 · 中国证监会 CSRC 2023 · 欧盟 CSRD/ESRS），
> 以及可再生能源技术经济分析（LCOE/NPV/IRR）。

![Python](https://img.shields.io/badge/Python-3.12%2B-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688) ![React](https://img.shields.io/badge/React-18%2B-61DAFB) ![License](https://img.shields.io/badge/License-MIT-green) ![Live Demo](https://img.shields.io/badge/Live-Demo-orange)

## ✨ 功能特性

- 📄 解析上传的 ESG 报告，并抽取结构化可持续发展指标。
- 🧮 基于后端规则计算 EU Taxonomy 的收入、CapEx、OpEx 对齐度。
- 🧠 在 EU Taxonomy 2020、中国证监会 CSRC 2023、欧盟 CSRD/ESRS 之间做多框架评分对比。
- ⚡ 输出合规缺口分析，并给出可执行改进建议。
- 📊 支持公司记录导出为 CSV/XLSX，并生成 PDF 报告。
- 🔬 计算 LCOE，并执行新能源项目敏感性分析。
- 🖥️ 提供 React 前端，覆盖上传、看板、对比、公司记录等核心流程。
- 🎯 **公司+年份缺口选择器**：高亮已导入/缺失年份，点击缺失年份直接深链到上传 / 自动抓取流程。
- 📥 **Pending Disclosures 审核台**：对官方来源（公司官网、SEC EDGAR、HKEX、中国证监会/CNINFO）自动抓取的披露做字段级审批，按来源通道可靠性排序推荐。
- 💱 LCOE 区域化默认值（EUR / USD），英文 UI 下附带 EIA 美国批发电价参考面板。
- 🐳 支持 Docker 本地部署，持久化 `data/` 与 `reports/`。

## 🚀 快速开始

### 前置要求

- Python 3.12+
- Node.js 18+
- Docker（可选）

### 本地开发

1. 克隆仓库并进入目录：

```bash
git clone https://github.com/wyl2607/esg-research-toolkit.git
cd esg-research-toolkit
```

2. 安装后端依赖并启动 FastAPI：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
```

3. 在新终端启动前端开发服务：

```bash
cd frontend
npm install
npm run dev
```

### 工作日前端健康检查

运行完整前端健康检查（lint、build、Playwright smoke、axe、Lighthouse）：

```bash
cd frontend
npm run health:check
```

当检查发现失败、bundle 回归、明显布局问题或新的 console/network 错误时，汇总报告会生成在：

```text
frontend/health-reports/latest/summary.md
```

### Docker

使用 Docker Compose 一键启动后端栈：

```bash
cp .env.example .env
docker-compose up -d --build
```

Backend API 默认暴露在 `http://localhost:8000`。

## 📡 API 参考

下表由 `main.py` 当前 FastAPI 路由自动整理。

| Method | Endpoint | 说明 |
|---|---|---|
| GET | `/` | 根路径信息与基础可用性响应。 |
| GET | `/docs` | Swagger UI 交互式 API 文档。 |
| GET | `/docs/oauth2-redirect` | Swagger UI 使用的 OAuth 回调辅助路径。 |
| GET | `/frameworks/compare` | 对比不同 ESG 框架的评分结果。 |
| GET | `/frameworks/list` | 获取已支持 ESG 框架列表与元信息。 |
| GET | `/frameworks/score` | 通过查询参数执行跨框架评分。 |
| POST | `/frameworks/score/upload` | 上传报告并触发跨框架评分。 |
| GET | `/health` | 服务健康检查接口。 |
| GET | `/openapi.json` | OpenAPI Schema 文档。 |
| GET | `/redoc` | ReDoc 风格 API 文档页。 |
| GET | `/report/companies` | 查询已存储公司报告记录列表。 |
| GET | `/report/companies/v2` | 带年份覆盖信息的公司列表（驱动缺口感知选择器）。 |
| POST | `/disclosures/fetch` | 针对 `(公司, 年份)` 发起官方来源自动抓取。 |
| GET | `/disclosures/pending` | 获取待审核的自动抓取披露列表。 |
| POST | `/disclosures/{id}/approve` | 将选中字段的待审披露合入公司历史。 |
| POST | `/disclosures/{id}/reject` | 按备注驳回一条待审披露。 |
| GET | `/disclosures/lane-stats` | 按来源通道的抓取可靠性遥测与推荐顺序。 |
| GET | `/report/companies/export/csv` | 导出公司记录为 CSV。 |
| GET | `/report/companies/export/xlsx` | 导出公司记录为 Excel。 |
| GET | `/report/companies/{company_name}/{report_year:int}` | 按公司与年份获取单条记录。 |
| DELETE | `/report/companies/{company_name}/{report_year:int}` | 硬删除对应公司记录。 |
| POST | `/report/companies/{company_name}/{report_year:int}/request-deletion` | 创建记录删除申请流程。 |
| GET | `/report/jobs/{batch_id}` | 查询批量上传任务状态。 |
| POST | `/report/upload` | 上传并解析单个 ESG 报告。 |
| POST | `/report/upload/batch` | 批量上传并解析多个 ESG 报告。 |
| GET | `/taxonomy/activities` | 获取 taxonomy 活动目录。 |
| POST | `/taxonomy/report` | 由结构化输入生成 taxonomy 报告。 |
| GET | `/taxonomy/report` | 按公司/年份读取 taxonomy 报告。 |
| GET | `/taxonomy/report/pdf` | 生成并下载 taxonomy PDF 报告。 |
| POST | `/taxonomy/report/text` | 生成 narrative 文本版 taxonomy 报告。 |
| POST | `/taxonomy/score` | 基于输入指标执行 EU Taxonomy 评分。 |
| GET | `/techno/benchmarks` | 获取技术经济分析基准参数。 |
| POST | `/techno/lcoe` | 计算项目 LCOE。 |
| POST | `/techno/sensitivity` | 运行技术经济敏感性分析。 |

## 🛡 Auto-Fetch 合规边界（F2）

披露补录链路（`POST /disclosures/fetch` + Upload 页待审核队列）默认受以下约束：

- **支持的官方来源通道：** 公司官网披露页、SEC EDGAR、HKEX、CSRC/CNINFO。
- **明确排除：** 付费/专有 ESG 数据商，以及第三方爬虫聚合站。
- **请求标识：** 抓取请求携带项目 User-Agent（`esg-research-toolkit/<ver> (+contact)`）。
- **速率与入库策略：** 限制 host 级节奏与全局并发；抓取结果先写入 `pending_disclosures`，必须经人工 approve/reject 后才可并入主表。

## 🏗 架构

```text
React Frontend (Vite)
        |
        v
      Nginx
        |
        v
 FastAPI Backend (main.py)
        |
        v
 SQLite (data/esg_toolkit.db) + File Reports (reports/)
```

前端负责上传、评分、看板与结果展示流程；FastAPI 提供计算与报告 API。持久化数据存储在 SQLite，生成文件输出到 `reports/`。

## 🌍 多框架 ESG

### EU Taxonomy 2020

EU Taxonomy 以活动级标准和收入/CapEx/OpEx 对齐比例衡量环境合规性。项目中实现了 DNSH 检查与面向缺口的建议生成。

### 中国证监会 CSRC 2023

CSRC 2023 聚焦上市公司 ESG 强制信息披露，覆盖 E/S/G 三个维度。工具可将报告提取结果映射为 CSRC 兼容评分输出。

### 欧盟 CSRD / ESRS

CSRD/ESRS 对环境、社会与治理提出更广泛披露要求。平台支持跨框架并排对比，帮助识别重叠项与差异项。

## 📊 前端页面

- `DashboardPage.tsx`：展示核心评分指标与总览信息。
- `UploadPage.tsx`：单文件/批量文件上传与解析入口（识别 `?company=&year=` 深链并提示缺口补录）。
- `PendingDisclosuresPage.tsx`：官方来源自动抓取披露的 analyst 审核工作台（`/disclosures`）。
- `TaxonomyPage.tsx`：EU Taxonomy 评分与报告生成工作区。
- `FrameworksPage.tsx`：多框架评分视图与标准说明。
- `ComparePage.tsx`：不同框架结果并排对比。
- `LcoePage.tsx`：LCOE 与敏感性分析计算页面。
- `CompaniesPage.tsx`：公司历史记录查询与导出管理。

## 🔧 配置说明

环境变量通过 `.env` 加载。

| 变量 | 示例 | 说明 |
|---|---|---|
| `OPENAI_API_KEY` | `sk-...` | 用于模型增强解析与补全功能。 |
| `APP_ENV` | `development` | 运行环境模式，影响日志与开关策略。 |
| `APP_HOST` | `0.0.0.0` | 后端绑定主机地址。 |
| `APP_PORT` | `8000` | 后端监听端口。 |
| `DATABASE_URL` | `sqlite:///./data/esg_toolkit.db` | SQLAlchemy 数据库连接字符串。 |
| `ARXIV_MAX_RESULTS` | `20` | 文献流水线单次检索上限。 |
| `ARXIV_DOWNLOAD_PDF` | `true` | 是否下载文献 PDF。 |
| `LOG_LEVEL` | `INFO` | 日志输出级别。 |
| `BATCH_MAX_WORKERS` | `2` | 批量解析任务并发 worker 数。 |

## 🗄️ 数据库初始化（Alembic 优先）

使用 Alembic 应用数据库 schema 变更：

```bash
./scripts/db_init.sh
# or
alembic upgrade head
```

如果生产数据库已经存在 schema 或业务数据，请先遵循：

- `docs/runbooks/alembic_cutover.md`（包含 `alembic stamp 0001_baseline` + `alembic upgrade head` 流程）

兼容性说明：

- `scripts/migrate_db.py` 仅作为旧入口兼容 shim 保留，会输出 Alembic 指引，不再直接写 schema。

## 🤝 贡献指南

1. Fork 本仓库并创建特性分支。
2. 为行为变更补充或更新测试。
3. 本地完成检查后再提交 Pull Request。
4. 在 PR 中写清范围、验证证据和必要迁移说明。

## 📄 许可证

MIT

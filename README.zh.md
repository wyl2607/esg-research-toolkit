[![Tests](https://github.com/wyl2607/esg-research-toolkit/actions/workflows/test.yml/badge.svg)](https://github.com/wyl2607/esg-research-toolkit/actions/workflows/test.yml)
[![Lint](https://github.com/wyl2607/esg-research-toolkit/actions/workflows/lint.yml/badge.svg)](https://github.com/wyl2607/esg-research-toolkit/actions/workflows/lint.yml)

# ESG Research Toolkit

ESG Research Toolkit 是一个面向企业 ESG 分析的开源工具集，将 PDF 报告解析、EU Taxonomy 合规评分与可再生能源项目技术经济建模整合为统一的 FastAPI 服务。

## 项目简介

本项目只有一个明确目标：以可复现、可编排、接口优先的方式，分析真实企业的 ESG 披露数据，并评估其可再生能源项目的经济性。

当前发布状态：

- 版本：`v0.1.0`
- 仓库：`https://github.com/wyl2607/esg-research-toolkit`
- 快照日期：`2026-04-12`

## 核心模块

### 1. `report_parser`

解析企业 PDF 报告，并将非结构化披露内容转换为结构化 ESG 数据。

- 使用 `pdfplumber` 提取上传 PDF 的文本内容
- 使用 OpenAI API 识别和抽取 ESG 指标
- 通过 SQLAlchemy ORM 持久化结构化结果
- 输出标准化的 `CompanyESGData`，供后续评分模块复用

### 2. `taxonomy_scorer`

基于 EU Taxonomy 框架对企业数据进行合规评分。

- 覆盖 6 个环境目标的对齐度评估
- 应用 Do No Significant Harm（`DNSH`，不造成重大损害）原则
- 对支持的经济活动使用 Technical Screening Criteria（`TSC`，技术筛选标准）阈值
- 生成机器可读报告和纯文本摘要
- 提供差距分析，严重级别包括 `critical`、`high`、`medium`、`low`

### 3. `techno_economics`

执行可再生能源项目经济性计算与情景分析。

- 计算平准化度电成本（`LCOE`）
- 计算净现值（`NPV`）、内部收益率（`IRR`）和回收期指标
- 执行 CAPEX 与 OPEX 敏感性分析
- 提供部分技术路线的参考 LCOE 区间

## 快速开始

### 前置要求

- Python `3.11+`
- 可用的 OpenAI API Key

### 安装

```bash
git clone https://github.com/wyl2607/esg-research-toolkit.git
cd esg-research-toolkit

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 配置

```bash
cp .env.example .env
```

至少配置以下变量：

```env
OPENAI_API_KEY=your_openai_api_key_here
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
DATABASE_URL=sqlite:///./data/esg_toolkit.db
```

### 启动服务

```bash
uvicorn main:app --reload
```

交互式 API 文档：

- Swagger UI：`http://localhost:8000/docs`
- ReDoc：`http://localhost:8000/redoc`

### 运行测试

```bash
pytest tests/ -v
```

## Docker 部署

### 快速开始

```bash
cp .env.example .env
docker compose up -d
docker compose ps
docker compose logs -f
docker compose down
```

### 环境变量

请在 `.env` 中至少配置：

```env
OPENAI_API_KEY=your_openai_api_key_here
```

容器默认使用 `DATABASE_URL=sqlite:///./data/esg_toolkit.db`，并挂载 `./data` 与 `./reports` 作为持久化卷。

## API 端点

### 系统端点

| 方法 | 端点 | 说明 |
| --- | --- | --- |
| `GET` | `/` | 返回服务元数据与模块列表 |
| `GET` | `/health` | 健康检查 |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc |
| `GET` | `/openapi.json` | OpenAPI schema |

### Report Parser

| 方法 | 端点 | 说明 |
| --- | --- | --- |
| `POST` | `/report/upload` | 上传 PDF 报告并返回结构化 `CompanyESGData` |
| `GET` | `/report/companies` | 列出已存储的企业报告 |
| `GET` | `/report/companies/{company_name}/{report_year}` | 获取指定企业与年份的报告 |

### Taxonomy Scorer

| 方法 | 端点 | 说明 |
| --- | --- | --- |
| `POST` | `/taxonomy/score` | 对 `CompanyESGData` 执行 EU Taxonomy 评分 |
| `POST` | `/taxonomy/report` | 生成包含差距分析的结构化 taxonomy 报告 |
| `POST` | `/taxonomy/report/text` | 生成纯文本 taxonomy 摘要 |
| `GET` | `/taxonomy/activities` | 列出当前支持的 EU Taxonomy 活动 |

### Techno Economics

| 方法 | 端点 | 说明 |
| --- | --- | --- |
| `POST` | `/techno/lcoe` | 计算 `LCOE`、`NPV` 和 `IRR` |
| `POST` | `/techno/sensitivity` | 执行 CAPEX 与 OPEX 敏感性分析 |
| `GET` | `/techno/benchmarks` | 返回部分技术路线的参考 LCOE 区间 |

## 技术栈

- 后端：FastAPI、Uvicorn
- 数据校验：Pydantic v2
- 数据库：SQLAlchemy 2.0、SQLite
- AI 抽取：OpenAI API
- PDF 处理：pdfplumber
- 科学计算：NumPy、SciPy
- 数据工具：pandas、openpyxl
- 报告生成：ReportLab、python-docx
- 测试：pytest、pytest-asyncio

## 项目统计

`v0.1.0` 项目快照：

| 指标 | 数值 |
| --- | --- |
| 已跟踪文件数 | 37 |
| 核心模块数 | 3 |
| API 端点数 | 15 |
| 自动化测试数 | 19 |
| 已记录测试通过率 | 100% |
| Python 版本 | 3.11+ |

## 设计原则

- 第一性原理范围控制：只保留直接服务于 ESG 合规分析和可再生能源项目评估的能力
- API 优先：核心能力全部通过文档化 HTTP 接口暴露
- 类型安全：使用 Pydantic schema 与显式 Python 类型注解
- 模块化：报告解析、taxonomy 评分与技术经济分析可独立演进，也可组合使用
- 测试支撑开发：核心业务逻辑具备自动化测试覆盖

## 贡献指南

欢迎贡献代码、文档和测试。

1. Fork 仓库。
2. 创建功能分支。
3. 保持改动小而清晰，并确保与项目的第一性原理范围一致。
4. 提交 Pull Request 前运行 lint 与测试。
5. 在 Pull Request 中清楚说明变更动机与验证结果。

贡献时，优先考虑那些能够提升 ESG 分析流程、taxonomy 评分准确性或技术经济建模质量的改进，避免引入与核心目标无关的额外范围。

## 许可证

本项目基于 MIT License 发布。

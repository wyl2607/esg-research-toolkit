# ESG Research Toolkit

🌐 [English](README.md) · [中文](README.zh.md) · [Deutsch](README.de.md)

> 面向企业 ESG 报告分析的开源平台，支持 EU Taxonomy 合规评分、
> 多框架对比（EU Taxonomy 2020 · 中国证监会 CSRC 2023 · 欧盟 CSRD/ESRS），
> 以及可再生能源技术经济分析（LCOE/NPV/IRR）。

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](#) [![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?logo=fastapi&logoColor=white)](#) [![React 19](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](#) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](#) [![Live Demo](https://img.shields.io/badge/Live%20Demo-Coming%20Soon-lightgrey)](#)

## ✨ 功能特性
- 🔍 通过 FastAPI 上传接口解析单份或批量 ESG PDF 报告。
- 🧠 使用 OpenAI 辅助文本分析提取结构化 ESG 指标。
- 🗂 基于 SQLAlchemy + SQLite 持久化企业报告数据。
- 📏 提供包含 DNSH/TSC 检查的 EU Taxonomy 评分流程。
- 🌍 支持三框架对比：EU Taxonomy 2020、CSRC 2023、CSRD/ESRS。
- 📉 提供可再生能源项目技术经济计算（LCOE、NPV、IRR、回收期）。
- 📊 在 React 前端中展示基准值与敏感性图表。
- 📄 输出结构化 JSON 报告与可下载 PDF 摘要。

## 🚀 快速开始

### 前置条件
- Python 3.12+, Node 18+, Docker（可选）

### 本地开发
1. 克隆仓库并进入目录：
   ```bash
   git clone https://github.com/wyl2607/esg-research-toolkit.git
   cd esg-research-toolkit
   ```
2. 启动后端 API：
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```
3. 启动前端控制台：
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

### Docker
```bash
cp .env.example .env
docker compose up --build
```

## 📡 API 参考

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/` | 服务元数据与模块概览 |
| `GET` | `/docs` | Swagger UI 文档 |
| `GET` | `/docs/oauth2-redirect` | Swagger 的 OAuth2 跳转辅助地址 |
| `GET` | `/frameworks/compare` | 按企业生成三框架对比结果 |
| `GET` | `/frameworks/list` | 列出支持的 ESG 框架与元信息 |
| `GET` | `/frameworks/score` | 按单一框架对企业进行评分 |
| `POST` | `/frameworks/score/upload` | 对上传的 CompanyESGData 执行三框架评分 |
| `GET` | `/health` | 服务健康检查 |
| `GET` | `/openapi.json` | OpenAPI Schema 输出 |
| `GET` | `/redoc` | ReDoc 文档 |
| `GET` | `/report/companies` | 列出已存储企业 ESG 报告 |
| `GET` | `/report/companies/{company_name}/{report_year}` | 读取单个企业报告 |
| `GET` | `/report/jobs/{batch_id}` | 查询批量上传异步任务状态 |
| `POST` | `/report/upload` | 上传单个 PDF 并提取 ESG 数据 |
| `POST` | `/report/upload/batch` | 批量上传（最多 20 份）并异步提取 |
| `GET` | `/taxonomy/activities` | 列出支持的 EU Taxonomy 活动 |
| `POST` | `/taxonomy/report` | 生成结构化 Taxonomy 报告（JSON） |
| `GET` | `/taxonomy/report` | 生成结构化 Taxonomy 报告（JSON） |
| `GET` | `/taxonomy/report/pdf` | 下载 Taxonomy PDF 报告 |
| `POST` | `/taxonomy/report/text` | 生成纯文本 Taxonomy 摘要 |
| `POST` | `/taxonomy/score` | 返回 EU Taxonomy 评分结果 |
| `GET` | `/techno/benchmarks` | 返回 LCOE 基准区间 |
| `POST` | `/techno/lcoe` | 计算 LCOE、NPV、IRR 与回收期 |
| `POST` | `/techno/sensitivity` | 执行 CAPEX/OPEX 敏感性分析 |

## 🏗 系统架构

```text
React Frontend (Vite)
        ↓
Nginx (production reverse proxy)
        ↓
FastAPI Backend
        ↓
SQLite + Local Storage (data/, reports/)
```

前端通过 HTTP 调用 FastAPI 接口；后端各模块共享数据库与本地文件目录，
用于报告文件管理和分析结果输出。

## 🌍 多框架 ESG

### EU Taxonomy 2020
围绕六大环境目标，并包含 Do No Significant Harm（DNSH）检查。
适用于需要欧盟合规口径和技术筛选标准的 ESG 评分场景。

### 中国证监会 CSRC 2023
对齐中国上市公司可持续发展报告指引的披露结构。
可用于评估 E/S/G 维度覆盖度与本地监管披露准备情况。

### 欧盟 CSRD/ESRS
扩展到 E1-E5、S1、G1 等 ESRS 主题维度。
可用于衡量企业在欧盟可持续披露义务下的报告完整度。

## 📊 前端页面

- `DashboardPage.tsx` — 组合层 KPI 卡片与快速跳转入口。
- `UploadPage.tsx` — 单文件/批量 ESG PDF 上传与处理状态追踪。
- `CompaniesPage.tsx` — 企业报告列表检索、排序与管理。
- `TaxonomyPage.tsx` — EU Taxonomy 雷达图、差距分析与 PDF 导出。
- `FrameworksPage.tsx` — EU Taxonomy、CSRC、CSRD 三框架横向对比。
- `ComparePage.tsx` — 多企业关键指标并排比较。
- `LcoePage.tsx` — LCOE 计算、基准对照与敏感性图表。

## 🔧 配置

| Variable | Default | Description |
| --- | --- | --- |
| `OPENAI_API_KEY` | `Required` | OpenAI API 密钥（用于 ESG 指标抽取） |
| `APP_ENV` | `development` | 应用环境（development/production） |
| `APP_HOST` | `0.0.0.0` | 后端监听地址 |
| `APP_PORT` | `8000` | 后端监听端口 |
| `DATABASE_URL` | `sqlite:///./data/esg_toolkit.db` | SQLAlchemy 数据库连接串 |
| `ARXIV_MAX_RESULTS` | `20` | 文献流程最大检索数量 |
| `ARXIV_DOWNLOAD_PDF` | `true` | 是否下载 arXiv PDF |
| `LOG_LEVEL` | `INFO` | 运行日志级别 |
| `BATCH_MAX_WORKERS` | `2` | 批量解析并发 worker 上限 |

## 🤝 贡献指南

1. Fork 仓库并创建功能分支。
2. 保持变更聚焦，并在提交中写明原因。
3. 提交 PR 前运行后端测试与前端 lint/build。
4. 在 PR 描述中附上验证命令与结果。
5. 发起 Pull Request 并及时响应评审反馈。

## 📄 许可证

MIT

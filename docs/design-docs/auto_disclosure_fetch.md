# Auto Disclosure Fetch (F2)

**Status**: draft (design) · **Owner**: backend + ops · **Depth**: 2026-04-18

## Goal

当用户在 CompanyProfile / Frameworks 页面发现某家公司某年份的披露**缺失**时，支持**后台**自动去开放数据源拉取合规可公开的披露数据，落入我们现有的 `CompanyReport` 表，补齐时间序列——无需用户手动下载 PDF。

## Why this is *not* the boring generic scraper

- 不做 Bloomberg-style 的"一键全球"面子工程。
- 只处理 **已在数据库里存在"锚点"但年份断档** 的公司（有 2024 没 2022）——这是 demo 中用户会真实触发的路径。
- 抓到的每一项指标都写进 `evidence_summary`（已有 schema），携带 `source_url` + `source_doc_id`，直接走我们现成的证据链审计管线（`extraction_qa_audit.py`）。**这才是项目差异点**：其他 ESG 工具抓完就完，我们把每个数字和来源绑死。

## Scope — 合规边界

| 数据源 | 是否纳入 | 备注 |
| --- | --- | --- |
| 公司官网 `/sustainability`、`/investor` 下的公开 PDF | ✅ | robots.txt 允许；标记 `source_type=pdf` |
| EU Transparency Register, SEC EDGAR, HKEX, SSE/SZSE filings | ✅ | 均为公开文件 API |
| CDP / SBTi 公开披露数据库（需 ToS 允许） | ⚠️ 二期 | 先 audit ToS |
| 付费数据商（Refinitiv, MSCI, ISS）| ❌ | 不纳入，明确排除 |
| 第三方二手整理站（爬虫汇总站） | ❌ | 合规风险 |

**硬约束**：
- 所有抓取都必须在调用之前检查该 host 的 robots.txt；
- HTTP header 带可识别 User-Agent `esg-research-toolkit/<ver> (+contact)`；
- 每个 host 单任务 RPS ≤ 0.5，全局并发 ≤ 4；
- **默认不自动写入主表**：抓取结果进 `pending_disclosures` 审核队列，人工或规则确认后才合并。

## Trigger Path

```
User 点 "未入库 2022" ──► /upload?company=BASF&year=2022
                            │
                            ├─ Upload PDF (手动)                ← 现有路径
                            └─ "自动尝试从官方源抓取" 按钮     ← 新增
                                  │
                                  ▼
                         POST /disclosures/fetch
                           {company, year, sources?:[...]}
                                  │
                                  ▼
                    async task → fetch → extract → 写 pending
                                  │
                                  ▼
                    用户回到 /upload，看到 review diff，"Approve"
                                  │
                                  ▼
                         写入 CompanyReport + evidence_summary
```

## Architecture

```
fetcher/
  sources/
    company_site.py     # 启发式寻找 /sustainability /esg /investor 下 PDF
    sec_edgar.py        # 10-K / 20-F climate sections
    hkex_filings.py     # 港股
    sse_szse.py         # 沪深 2023 CSRC 披露
  dispatcher.py         # 按 domicile 选 source 链
  pipeline.py           # fetch → extract (走现有 report_parser) → queue
  pending_store.py      # 新表 pending_disclosures (status: pending/approved/rejected)
api/
  disclosures.py        # POST /disclosures/fetch, GET /disclosures/pending
frontend/
  UploadPage:
    + autoFetchPanel (shows source guesses, lets user tick which to try)
    + pendingReviewDrawer (shows diff before approve)
```

## Data Model

```sql
CREATE TABLE pending_disclosures (
  id INTEGER PRIMARY KEY,
  company_name TEXT NOT NULL,
  report_year INTEGER NOT NULL,
  source_url TEXT NOT NULL,
  source_type TEXT NOT NULL,      -- 'pdf', 'html', 'filing'
  fetched_at TIMESTAMP NOT NULL,
  extracted_payload JSONB NOT NULL, -- CompanyESGData-shaped
  status TEXT NOT NULL DEFAULT 'pending',  -- pending | approved | rejected
  review_note TEXT,
  UNIQUE(company_name, report_year, source_url)
);
```

## Reuse

- 提取复用现有 `report_parser/extractor.py` + `extraction_qa_audit.py`，**不为 auto-fetch 另造一套 LLM 链**。
- 提取模型按 `~/.codex/memories` 里的 provider 策略：默认 `gpt-4.1-mini`，大文件降级 `gpt-4o-mini`。
- 费用守护：每个 fetch 任务默认额度 $0.10，超支抛错不重试。

## Decision Points (open)

| # | 决策 | 选项 | 推荐 |
| - | --- | --- | --- |
| Q1 | 触发方式 | (a) 用户按钮 / (b) 每晚 cron 扫所有缺口 | (a) 先上，(b) 作为 v0.3 feature-flagged |
| Q2 | 审核 UI | (a) 简单 approve/reject / (b) 字段级 diff + 勾选 | 先 (a)，v0.3 升 (b) |
| Q3 | 失败语义 | (a) 静默失败 / (b) 明确告诉用户"没找到公开报告" | (b) 并记 `fetch_attempts` 表 |

## Done Criteria

- [ ] `/disclosures/fetch` 可以在本地启动、成功抓一家德国公司官网的 sustainability PDF 并写入 `pending_disclosures`
- [ ] `extraction_qa_audit.py` 对 pending 记录跑通
- [ ] Upload 页新增 "Auto fetch" 面板和 pending review drawer
- [ ] Playwright e2e：mock source → trigger fetch → approve → 数据库出现 new CompanyReport
- [ ] README 里补一段合规声明：支持哪些源、排除哪些源、User-Agent、RPS 限制
- [ ] `docs/releases/CHANGELOG.md` 加条目

## 非目标

- 不实现付费 API 接入。
- 不做公司名模糊匹配/别名消解（依赖已有 `canonical_name`）。
- 不做全量历史回填——只在用户触发或 cron 白名单公司上跑。

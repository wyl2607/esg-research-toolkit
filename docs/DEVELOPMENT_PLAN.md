# ESG Research Toolkit — 重审后开发计划

## 第一性原理

**这个工具存在的唯一理由**：帮助分析一家真实企业的 ESG 合规状况，并对其可再生能源项目做技术经济评估。

所有功能必须回答这个问题：**"这对分析一家企业的 ESG 数据有直接帮助吗？"**

如果答案是否，不做。

---

## 已废弃的内容

- `literature_pipeline/`（arXiv 文献抓取）— 学术论文不是企业 ESG 数据，废弃
- 对应的 schemas：`PaperMetadata`、`PaperSummary` — 一并清除

---

## 三个核心模块（重新定义）

### 模块 1：企业报告解析器（`report_parser/`）

**解决什么问题**：企业的 ESG 数据藏在 PDF 年报、可持续发展报告里，需要提取成结构化数据才能评分。

**输入**：企业 PDF 文件（年报、CSR 报告、CSRD 披露文件）
**输出**：结构化 ESG 指标数据（能耗、排放、收入构成、资本支出等）

**核心功能**：
- 上传 PDF → 提取文本（pdfplumber）
- OpenAI 从文本中抽取 ESG 关键指标（Scope 1/2/3、能耗、收入分类等）
- 输出标准化的 `CompanyESGData` 结构，供后续模块使用

---

### 模块 2：EU Taxonomy 合规评分器（`taxonomy_scorer/`）

**解决什么问题**：判断一家企业的经济活动是否符合欧盟分类法，计算对齐度百分比。

**输入**：`CompanyESGData`（来自模块 1 或手动填写）
**输出**：6 个环保目标的对齐度评分 + DNSH 检查 + 差距分析

**核心规则**（硬编码，来自 EU Taxonomy Regulation 2020/852）：
- 6 个环保目标：气候变化减缓、气候变化适应、水资源保护、循环经济、污染防治、生物多样性
- DNSH 原则：每个目标不能对其他目标造成重大损害
- TSC（技术筛选标准）：重点覆盖太阳能 PV、风能、储能、建筑节能
- 三类指标：Revenue 对齐度、CapEx 对齐度、OpEx 对齐度

---

### 模块 3：技术经济分析（`techno_economics/`）

**解决什么问题**：评估一个可再生能源项目的财务可行性。

**输入**：项目参数（CAPEX、OPEX、容量因子、生命周期、折现率）
**输出**：LCOE（€/MWh）、NPV、IRR、回收期

**核心计算**：
- LCOE = (CAPEX + Σ OPEX_t/(1+r)^t) / Σ E_t/(1+r)^t
- NPV = Σ 现金流_t/(1+r)^t − 初始投资
- IRR = 使 NPV=0 的折现率
- 敏感性分析：±20% CAPEX/OPEX 对 LCOE 的影响

---

## 项目目录结构（重审后）

```
esg-research-toolkit/
├── README.md
├── LICENSE
├── requirements.txt
├── .env.example
├── .gitignore
├── main.py                      # FastAPI 入口，注册三个 router
│
├── core/
│   ├── config.py               # OpenAI 配置（已完成）
│   ├── ai_client.py            # OpenAI complete()（已完成）
│   ├── database.py             # SQLAlchemy（已完成）
│   └── schemas.py              # 共享数据模型（需重写，删除 Paper* 类）
│
├── report_parser/              # 模块 1（新建，替代 literature_pipeline）
│   ├── __init__.py
│   ├── extractor.py            # PDF 文本提取（pdfplumber）
│   ├── analyzer.py             # OpenAI 抽取 ESG 指标
│   ├── storage.py              # 企业报告记录存储
│   └── api.py                  # FastAPI router /report
│
├── taxonomy_scorer/            # 模块 2
│   ├── __init__.py
│   ├── framework.py            # EU Taxonomy 规则（6 目标 + DNSH + TSC）
│   ├── scorer.py               # 合规评分引擎
│   ├── gap_analyzer.py         # 差距分析
│   ├── reporter.py             # 报告生成（JSON + PDF）
│   └── api.py                  # FastAPI router /taxonomy
│
├── techno_economics/           # 模块 3
│   ├── __init__.py
│   ├── lcoe.py                 # LCOE 计算
│   ├── npv_irr.py              # NPV/IRR 计算
│   ├── sensitivity.py          # 敏感性分析
│   └── api.py                  # FastAPI router /techno
│
├── tests/
│   ├── test_report_parser.py
│   ├── test_taxonomy_scorer.py
│   └── test_techno_economics.py
│
└── docs/
    ├── DEVELOPMENT_PLAN.md     # 本文件副本
    └── eu_taxonomy_guide.md    # EU Taxonomy 规则参考
```

---

## 需要清理的已有文件

| 文件 | 操作 |
|------|------|
| `literature_pipeline/` 整个目录 | 删除 |
| `core/schemas.py` 中的 `PaperMetadata`、`PaperSummary` | 删除这两个类 |
| `main.py` 中的 `literature_router` 引用 | 删除 |

---

## 开发顺序

### 阶段 1：清理 + 重建 schemas（立即）
1. 删除 `literature_pipeline/`
2. 重写 `core/schemas.py`：保留 Taxonomy/LCOE 相关模型，新增 `CompanyESGData`
3. 更新 `main.py`

### 阶段 2：report_parser 模块
- `extractor.py`：PDF 上传 → pdfplumber 提取文本
- `analyzer.py`：OpenAI 从文本抽取 ESG 指标 → `CompanyESGData`
- `storage.py`：存储企业报告记录
- `api.py`：`POST /report/upload`、`GET /report/{company_id}`

### 阶段 3：taxonomy_scorer 模块
- `framework.py`：EU Taxonomy 6 目标 + DNSH + TSC 规则（硬编码）
- `scorer.py`：Revenue/CapEx/OpEx 对齐度计算
- `gap_analyzer.py`：差距分析
- `reporter.py`：JSON + PDF 报告
- `api.py`：`POST /taxonomy/score`、`GET /taxonomy/report/{company_id}`

### 阶段 4：techno_economics 模块
- `lcoe.py`：LCOE 计算
- `npv_irr.py`：NPV/IRR + 回收期
- `sensitivity.py`：敏感性分析
- `api.py`：`POST /techno/lcoe`、`POST /techno/sensitivity`

### 阶段 5：集成 + 测试 + 发布
- 端到端测试：上传企业 PDF → 提取数据 → EU Taxonomy 评分 → 输出报告
- pytest 覆盖率 ≥ 70%
- README 更新（含 demo）
- GitHub release v0.1.0
- 更新 cv.md 中的 GitHub 链接为 `github.com/wyl2607/esg-research-toolkit`

---

## 核心 Schema（重审后）

```python
# 企业 ESG 数据（模块 1 输出，模块 2 输入）
class CompanyESGData(BaseModel):
    company_name: str
    report_year: int
    # 环境
    scope1_co2e_tonnes: float | None = None
    scope2_co2e_tonnes: float | None = None
    scope3_co2e_tonnes: float | None = None
    energy_consumption_mwh: float | None = None
    renewable_energy_pct: float | None = None
    water_usage_m3: float | None = None
    waste_recycled_pct: float | None = None
    # 财务（用于 Taxonomy 对齐度）
    total_revenue_eur: float | None = None
    taxonomy_aligned_revenue_pct: float | None = None
    total_capex_eur: float | None = None
    taxonomy_aligned_capex_pct: float | None = None
    # 社会
    total_employees: int | None = None
    female_pct: float | None = None
    # 活动分类（企业主要经济活动）
    primary_activities: list[str] = []  # e.g. ["solar_pv", "wind_onshore"]

# EU Taxonomy 评分结果（模块 2 输出）
class TaxonomyScoreResult(BaseModel):
    company_name: str
    report_year: int
    revenue_aligned_pct: float
    capex_aligned_pct: float
    opex_aligned_pct: float
    objective_scores: dict[str, float]  # 6 个目标各自的得分
    dnsh_pass: bool
    gaps: list[str]
    recommendations: list[str]

# LCOE 输入/输出（模块 3）
class LCOEInput(BaseModel):
    technology: Literal["solar_pv", "wind_onshore", "wind_offshore", "battery_storage"]
    capex_eur_per_kw: float
    opex_eur_per_kw_year: float
    capacity_factor: float
    lifetime_years: int = 25
    discount_rate: float = 0.07

class LCOEResult(BaseModel):
    technology: str
    lcoe_eur_per_mwh: float
    npv_eur: float
    irr: float
    payback_years: float
```

---

## Done Criteria

- [ ] `POST /report/upload` 接受 PDF，返回 `CompanyESGData`
- [ ] `POST /taxonomy/score` 接受 `CompanyESGData`，返回 6 目标对齐度 + DNSH 结果
- [ ] `POST /techno/lcoe` 接受项目参数，返回 LCOE + NPV + IRR
- [ ] pytest 覆盖率 ≥ 70%
- [ ] 无 `literature_pipeline` 残留
- [ ] GitHub repo 公开，cv.md 链接更新

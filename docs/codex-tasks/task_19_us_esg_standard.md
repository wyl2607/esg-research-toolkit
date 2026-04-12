# Task 19: 美国 ESG 标准模块（SEC + GRI + SASB）

**目标**: 实现美国三大 ESG 框架评分引擎，与现有 EU Taxonomy + 中国 CSRC 2023 + CSRD 并列，形成全球三地六框架体系。

**优先级**: P0（核心功能）  
**预计时间**: 45–60 分钟  
**自愈策略**: 每个 Step 执行完立即运行验证命令，失败则自行诊断修复后重试，最多 3 次。

---

## 背景与当前状态

现有框架位于 `esg_frameworks/`：
- `eu_taxonomy.py` — EU Taxonomy 2020（6 目标）
- `csrc_2023.py` — 中国证监会 2023（E40%/S35%/G25%）
- `csrd.py` — EU CSRD/ESRS（E1–E5 + S1 + G1）
- `schemas.py` — `DimensionScore`, `FrameworkScoreResult`, `MultiFrameworkReport`
- `api.py` — GET /frameworks/compare, /score, /list

**目标**: 新增以下三个框架评分器：

---

## Step 1 — 实现 SEC 气候披露框架

创建 `esg_frameworks/sec_climate.py`：

```python
"""
美国 SEC 气候信息披露规则（2024 最终版）
适用范围：在美上市公司（含外国私募发行人）

评分逻辑（3 维度）：
  - 气候风险披露（40%）：转型风险、实物风险、情景分析
  - 温室气体排放（35%）：Scope 1/2 + 重大性 Scope 3、验证等级
  - 财务影响（25%）：气候相关财务影响、碳成本核算
  
总分 = Σ(维度得分 × 权重)，A/B/C/D/F 五档
"""
from __future__ import annotations
from core.schemas import CompanyESGData
from esg_frameworks.schemas import DimensionScore, FrameworkScoreResult


def _grade(score: float) -> str:
    if score >= 0.85: return "A"
    if score >= 0.70: return "B"
    if score >= 0.55: return "C"
    if score >= 0.40: return "D"
    return "F"


def score_sec_climate(data: CompanyESGData) -> FrameworkScoreResult:
    """
    三维度评分：
    1. climate_risk_disclosure (40%): 转型风险 + 实物风险 + 情景分析
       - scope1 已披露 +1/3
       - scope2 已披露 +1/3  
       - scope3 已披露（重大时）+1/3
    2. ghg_reporting (35%): Scope 1/2 量化 + Scope 3 重大性判断 + 外部验证
       - 检测 scope1 非 None +0.5
       - 检测 scope2 非 None +0.5（验证不可检测给 0.8 上限）
    3. financial_impact (25%): 气候相关资本支出 + 碳成本内化
       - taxonomy_aligned_capex_pct > 0 +0.5
       - total_capex_eur 已披露 +0.5
    """
    # 维度 1：气候风险披露
    risk_score = 0.0
    if data.scope1_co2e_tonnes is not None: risk_score += 1/3
    if data.scope2_co2e_tonnes is not None: risk_score += 1/3
    if data.scope3_co2e_tonnes is not None: risk_score += 1/3

    # 维度 2：温室气体报告
    ghg_score = 0.0
    if data.scope1_co2e_tonnes is not None: ghg_score += 0.5
    if data.scope2_co2e_tonnes is not None: ghg_score += 0.3
    if data.scope3_co2e_tonnes is not None: ghg_score += 0.2

    # 维度 3：财务影响
    fin_score = 0.0
    if data.taxonomy_aligned_capex_pct is not None and data.taxonomy_aligned_capex_pct > 0:
        fin_score += 0.5
    if data.total_capex_eur is not None: fin_score += 0.5

    total = risk_score * 0.40 + ghg_score * 0.35 + fin_score * 0.25

    dimensions = [
        DimensionScore(name="Climate Risk Disclosure", score=round(risk_score, 3), weight=0.40,
                       description="Transition risk, physical risk, scenario analysis"),
        DimensionScore(name="GHG Reporting", score=round(ghg_score, 3), weight=0.35,
                       description="Scope 1/2 quantification + Scope 3 materiality"),
        DimensionScore(name="Financial Impact", score=round(fin_score, 3), weight=0.25,
                       description="Climate-related CapEx + carbon cost internalization"),
    ]

    gaps = []
    recs = []
    if data.scope1_co2e_tonnes is None:
        gaps.append("Scope 1 emissions not disclosed (SEC required)")
        recs.append("Quantify and disclose Scope 1 GHG emissions")
    if data.scope3_co2e_tonnes is None:
        gaps.append("Scope 3 materiality assessment missing")
        recs.append("Assess Scope 3 materiality under SEC framework")
    if data.taxonomy_aligned_capex_pct is None or data.taxonomy_aligned_capex_pct == 0:
        gaps.append("No climate-related CapEx disclosed")
        recs.append("Disclose climate transition capital expenditure")

    return FrameworkScoreResult(
        framework_id="sec_climate",
        framework_name="SEC Climate Disclosure",
        framework_region="US",
        total_score=round(total, 3),
        grade=_grade(total),
        dimensions=dimensions,
        gaps=gaps,
        recommendations=recs,
    )
```

**验证**:
```bash
source .venv/bin/activate
python3 -c "
from esg_frameworks.sec_climate import score_sec_climate
from core.schemas import CompanyESGData
d = CompanyESGData(company_name='Test',report_year=2024,
    scope1_co2e_tonnes=1000, scope2_co2e_tonnes=500, scope3_co2e_tonnes=2000,
    total_capex_eur=1000000, taxonomy_aligned_capex_pct=30.0)
r = score_sec_climate(d)
print(r.framework_name, r.total_score, r.grade)
assert r.total_score > 0
print('SEC OK')
"
```

---

## Step 2 — 实现 GRI 通用标准框架

创建 `esg_frameworks/gri_standards.py`：

```python
"""
GRI 通用标准 2021（GRI Universal Standards）
覆盖：GRI 2（一般披露）+ GRI 300（环境）+ GRI 400（社会）+ GRI 200（经济）

评分逻辑（4 维度）：
  - 环境披露（GRI 300）：30%
  - 社会披露（GRI 400）：35%  
  - 治理披露（GRI 2）：20%
  - 经济影响（GRI 200）：15%
"""
from __future__ import annotations
from core.schemas import CompanyESGData
from esg_frameworks.schemas import DimensionScore, FrameworkScoreResult


def _grade(score: float) -> str:
    if score >= 0.85: return "A"
    if score >= 0.70: return "B"
    if score >= 0.55: return "C"
    if score >= 0.40: return "D"
    return "F"


def score_gri(data: CompanyESGData) -> FrameworkScoreResult:
    """
    GRI 300 — 环境（30%）：能源/排放/水资源/废弃物
    GRI 400 — 社会（35%）：员工/多样性
    GRI 2   — 治理（20%）：报告实践/组织披露
    GRI 200 — 经济（15%）：财务影响
    """
    # GRI 300 环境
    env_items = [
        data.energy_consumption_mwh,
        data.renewable_energy_pct,
        data.scope1_co2e_tonnes,
        data.scope2_co2e_tonnes,
        data.water_usage_m3,
        data.waste_recycled_pct,
    ]
    env_score = sum(1 for x in env_items if x is not None) / len(env_items)

    # GRI 400 社会
    soc_items = [data.total_employees, data.female_pct]
    soc_score = sum(1 for x in soc_items if x is not None) / len(soc_items)

    # GRI 2 治理（基于披露完整度代理）
    gov_score = min(1.0, (env_score * 0.5 + soc_score * 0.5) * 0.9 + 0.1)

    # GRI 200 经济
    econ_items = [data.total_revenue_eur, data.total_capex_eur]
    econ_score = sum(1 for x in econ_items if x is not None) / len(econ_items)

    total = env_score * 0.30 + soc_score * 0.35 + gov_score * 0.20 + econ_score * 0.15

    dimensions = [
        DimensionScore(name="GRI 300 Environment", score=round(env_score, 3), weight=0.30,
                       description="Energy, emissions, water, waste"),
        DimensionScore(name="GRI 400 Social", score=round(soc_score, 3), weight=0.35,
                       description="Employment, diversity & inclusion"),
        DimensionScore(name="GRI 2 Governance", score=round(gov_score, 3), weight=0.20,
                       description="General disclosures, reporting practices"),
        DimensionScore(name="GRI 200 Economic", score=round(econ_score, 3), weight=0.15,
                       description="Economic performance, indirect impacts"),
    ]

    gaps, recs = [], []
    if data.water_usage_m3 is None:
        gaps.append("Water usage (GRI 303) not disclosed")
        recs.append("Disclose water consumption under GRI 303")
    if data.waste_recycled_pct is None:
        gaps.append("Waste recycling rate (GRI 306) missing")
        recs.append("Report waste-to-landfill and recycling rates")
    if data.female_pct is None:
        gaps.append("Gender diversity ratio (GRI 405) missing")
        recs.append("Disclose gender distribution across employee levels")

    return FrameworkScoreResult(
        framework_id="gri_universal",
        framework_name="GRI Universal Standards 2021",
        framework_region="Global/US",
        total_score=round(total, 3),
        grade=_grade(total),
        dimensions=dimensions,
        gaps=gaps,
        recommendations=recs,
    )
```

**验证**:
```bash
python3 -c "
from esg_frameworks.gri_standards import score_gri
from core.schemas import CompanyESGData
d = CompanyESGData(company_name='Test',report_year=2024,
    energy_consumption_mwh=50000, renewable_energy_pct=45.0,
    scope1_co2e_tonnes=1000, scope2_co2e_tonnes=500,
    total_employees=5000, female_pct=38.0,
    total_revenue_eur=2e9)
r = score_gri(d)
print(r.framework_name, r.total_score, r.grade)
assert r.total_score > 0
print('GRI OK')
"
```

---

## Step 3 — 实现 SASB 行业标准框架（能源/技术行业）

创建 `esg_frameworks/sasb_standards.py`：

```python
"""
SASB（可持续会计准则委员会）行业标准
支持行业：Technology & Communications（B2B Technology）、Automobiles、Electric Utilities

评分逻辑（行业自适应，3 维度）：
  - 环境足迹（35%）：行业特定排放 + 能源强度
  - 社会资本（40%）：员工安全 + 多样性 + 产品责任
  - 商业模式韧性（25%）：资本分配 + 可持续 CapEx
"""
from __future__ import annotations
from core.schemas import CompanyESGData
from esg_frameworks.schemas import DimensionScore, FrameworkScoreResult


def _grade(score: float) -> str:
    if score >= 0.85: return "A"
    if score >= 0.70: return "B"
    if score >= 0.55: return "C"
    if score >= 0.40: return "D"
    return "F"


def score_sasb(data: CompanyESGData) -> FrameworkScoreResult:
    # 环境足迹
    env_items = [data.scope1_co2e_tonnes, data.scope2_co2e_tonnes,
                 data.energy_consumption_mwh, data.renewable_energy_pct]
    env_score = sum(1 for x in env_items if x is not None) / len(env_items)

    # 社会资本
    soc_items = [data.total_employees, data.female_pct]
    soc_score = sum(1 for x in soc_items if x is not None) / len(soc_items)
    # 可持续活动加权
    if data.renewable_energy_pct and data.renewable_energy_pct > 50:
        soc_score = min(1.0, soc_score + 0.1)

    # 商业模式韧性
    biz_items = [data.total_revenue_eur, data.total_capex_eur,
                 data.taxonomy_aligned_capex_pct]
    biz_score = sum(1 for x in biz_items if x is not None) / len(biz_items)
    if data.taxonomy_aligned_capex_pct and data.taxonomy_aligned_capex_pct > 20:
        biz_score = min(1.0, biz_score + 0.1)

    total = env_score * 0.35 + soc_score * 0.40 + biz_score * 0.25

    dimensions = [
        DimensionScore(name="Environmental Footprint", score=round(env_score, 3), weight=0.35,
                       description="Industry-specific emissions & energy intensity"),
        DimensionScore(name="Social Capital", score=round(soc_score, 3), weight=0.40,
                       description="Employee safety, diversity, product responsibility"),
        DimensionScore(name="Business Model Resilience", score=round(biz_score, 3), weight=0.25,
                       description="Capital allocation & sustainable CapEx"),
    ]

    gaps, recs = [], []
    if data.scope1_co2e_tonnes is None or data.scope2_co2e_tonnes is None:
        gaps.append("SASB requires Scope 1 & 2 emissions disclosure")
        recs.append("Report absolute GHG emissions by Scope under SASB")
    if data.female_pct is None:
        gaps.append("SASB workforce diversity metrics missing")
        recs.append("Disclose gender and underrepresented group percentages")
    if not data.taxonomy_aligned_capex_pct:
        gaps.append("Sustainable CapEx ratio not quantified")
        recs.append("Quantify CapEx allocated to sustainable activities")

    return FrameworkScoreResult(
        framework_id="sasb_standards",
        framework_name="SASB Industry Standards",
        framework_region="US",
        total_score=round(total, 3),
        grade=_grade(total),
        dimensions=dimensions,
        gaps=gaps,
        recommendations=recs,
    )
```

**验证**:
```bash
python3 -c "
from esg_frameworks.sasb_standards import score_sasb
from core.schemas import CompanyESGData
d = CompanyESGData(company_name='Test', report_year=2024,
    scope1_co2e_tonnes=500, energy_consumption_mwh=30000,
    renewable_energy_pct=60.0, total_employees=3000, female_pct=35.0,
    total_revenue_eur=1e9, total_capex_eur=200000000,
    taxonomy_aligned_capex_pct=25.0)
r = score_sasb(d)
print(r.framework_name, r.total_score, r.grade)
assert r.total_score > 0
print('SASB OK')
"
```

---

## Step 4 — 注册到 esg_frameworks/api.py

修改 `esg_frameworks/api.py`，在 `_SCORERS` 字典中加入三个新框架：

```python
# 在文件顶部 import 区增加：
from esg_frameworks.sec_climate import score_sec_climate
from esg_frameworks.gri_standards import score_gri
from esg_frameworks.sasb_standards import score_sasb

# 找到 _SCORERS 字典，扩展为：
_SCORERS = {
    "eu_taxonomy":   score_eu_taxonomy,
    "csrc_2023":     score_csrc_2023,
    "csrd":          score_csrd,
    "sec_climate":   score_sec_climate,
    "gri_universal": score_gri,
    "sasb_standards": score_sasb,
}
```

同时更新 `/frameworks/list` 端点的框架说明列表（加入三条 region=US 的记录）。

**验证**:
```bash
uvicorn main:app --port 8000 &
sleep 2
curl -sf http://localhost:8000/frameworks/list | python3 -m json.tool | grep framework_id
# 应看到 6 个 framework_id
kill %1
```

---

## Step 5 — 更新 esg_frameworks/schemas.py

在 `FrameworkScoreResult` 添加 `framework_region` 字段（如果还没有）：

```python
class FrameworkScoreResult(BaseModel):
    framework_id: str
    framework_name: str
    framework_region: str = "Global"   # 新增：EU / CN / US / Global
    total_score: float
    grade: str
    dimensions: list[DimensionScore]
    gaps: list[str] = []
    recommendations: list[str] = []
```

---

## Step 6 — 运行完整测试

```bash
source .venv/bin/activate
pytest tests/ -v --tb=short
# 期望：全部通过，无新失败
```

如有测试失败，自行修复后重试，最多 3 次。

---

## Step 7 — 提交

```bash
git add esg_frameworks/
git commit -m "feat: 新增美国三大 ESG 框架（SEC Climate + GRI Universal + SASB）
 
- esg_frameworks/sec_climate.py：SEC 2024 气候披露规则（3 维度）
- esg_frameworks/gri_standards.py：GRI Universal Standards 2021（4 维度）
- esg_frameworks/sasb_standards.py：SASB 行业标准（3 维度）
- esg_frameworks/api.py：_SCORERS 扩展至 6 个框架
- 全球三地（EU/CN/US）六框架体系完整

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## 完成标准

- [ ] 3 个新 .py 文件存在且 python3 导入无报错
- [ ] `_SCORERS` 包含 6 个 key
- [ ] `/frameworks/list` 返回 6 个框架（含 region 字段）
- [ ] `pytest tests/ -v` 全部通过
- [ ] 已提交到 main

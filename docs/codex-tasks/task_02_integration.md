# Task 2: 模块联动集成（端到端工作流）

**优先级**: 高  
**预计时间**: 3-4 小时  
**依赖**: Task 1（用户手册）

---

## 目标

创建完整的端到端工作流，展示三个模块如何协同工作，并提供示例数据。

## 模块联动逻辑

```
PDF 上传
   ↓
report_parser.extractor → 提取文本
   ↓
report_parser.analyzer → OpenAI 抽取 ESG 指标 → CompanyESGData
   ↓
taxonomy_scorer.scorer → EU Taxonomy 评分 → TaxonomyScoreResult
   ↓
taxonomy_scorer.reporter → 生成报告
   ↓
techno_economics.lcoe → LCOE 计算（如果有可再生能源项目）
   ↓
综合报告输出
```

## 输出文件

### 1. `examples/mock_esg_data.json`
示例 ESG 数据（用于测试，不需要真实 PDF）

```json
{
  "company_name": "GreenTech Solutions GmbH",
  "report_year": 2024,
  "scope1_co2e_tonnes": 1200,
  "scope2_co2e_tonnes": 800,
  "scope3_co2e_tonnes": 5000,
  "energy_consumption_mwh": 15000,
  "renewable_energy_pct": 85,
  "water_usage_m3": 50000,
  "waste_recycled_pct": 70,
  "total_revenue_eur": 50000000,
  "taxonomy_aligned_revenue_pct": 75,
  "total_capex_eur": 10000000,
  "taxonomy_aligned_capex_pct": 80,
  "total_employees": 250,
  "female_pct": 45,
  "primary_activities": ["solar_pv", "wind_onshore"]
}
```

### 2. `workflows/end_to_end.py`
完整端到端工作流脚本

功能：
- 从 JSON 文件加载 ESG 数据（或上传 PDF）
- 调用 Taxonomy Scorer 评分
- 如果有可再生能源活动，调用 LCOE 计算
- 生成综合报告并保存到 `reports/` 目录

```python
"""端到端工作流：从 ESG 数据到综合报告"""
import json
import requests
from pathlib import Path

BASE_URL = "http://localhost:8000"

def run_full_analysis(esg_data_path: str = "examples/mock_esg_data.json"):
    # 1. 加载 ESG 数据
    with open(esg_data_path) as f:
        esg_data = json.load(f)
    print(f"✓ 加载 ESG 数据: {esg_data['company_name']} ({esg_data['report_year']})")

    # 2. EU Taxonomy 评分
    resp = requests.post(f"{BASE_URL}/taxonomy/score", json=esg_data)
    resp.raise_for_status()
    taxonomy_result = resp.json()
    print(f"✓ Taxonomy 评分完成")
    print(f"  Revenue aligned: {taxonomy_result['revenue_aligned_pct']:.1f}%")
    print(f"  DNSH pass: {taxonomy_result['dnsh_pass']}")

    # 3. 生成文本报告
    resp = requests.post(f"{BASE_URL}/taxonomy/report/text", json=taxonomy_result)
    resp.raise_for_status()
    taxonomy_report = resp.text

    # 4. LCOE 分析（如果有可再生能源活动）
    lcoe_results = []
    renewable_activities = {
        "solar_pv": {"capex": 800, "opex": 15, "cf": 0.18},
        "wind_onshore": {"capex": 1200, "opex": 30, "cf": 0.35},
        "wind_offshore": {"capex": 2500, "opex": 80, "cf": 0.45},
        "battery_storage": {"capex": 500, "opex": 10, "cf": 0.9},
    }

    for activity in esg_data.get("primary_activities", []):
        if activity in renewable_activities:
            params = renewable_activities[activity]
            lcoe_input = {
                "technology": activity,
                "capex_eur_per_kw": params["capex"],
                "opex_eur_per_kw_year": params["opex"],
                "capacity_factor": params["cf"],
                "lifetime_years": 25,
                "discount_rate": 0.07
            }
            resp = requests.post(f"{BASE_URL}/techno/lcoe", json=lcoe_input)
            resp.raise_for_status()
            lcoe_result = resp.json()
            lcoe_results.append(lcoe_result)
            print(f"✓ LCOE ({activity}): {lcoe_result['lcoe_eur_per_mwh']:.1f} €/MWh, IRR: {lcoe_result['irr']*100:.1f}%")

    # 5. 保存综合报告
    company = esg_data["company_name"].replace(" ", "_")
    year = esg_data["report_year"]
    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)

    report_path = output_dir / f"{company}_{year}_full_report.txt"
    with open(report_path, "w") as f:
        f.write(taxonomy_report)
        if lcoe_results:
            f.write("\n\n=== TECHNO-ECONOMIC ANALYSIS ===\n")
            for r in lcoe_results:
                f.write(f"\n{r['technology'].upper()}\n")
                f.write(f"  LCOE: {r['lcoe_eur_per_mwh']:.1f} €/MWh\n")
                f.write(f"  NPV: {r['npv_eur']:,.0f} EUR\n")
                f.write(f"  IRR: {r['irr']*100:.1f}%\n")
                f.write(f"  Payback: {r['payback_years']:.1f} years\n")

    print(f"✓ 报告已保存: {report_path}")
    return str(report_path)

if __name__ == "__main__":
    run_full_analysis()
```

### 3. `workflows/batch_analysis.py`
批量分析多家企业

功能：
- 读取 `examples/companies/` 目录下所有 JSON 文件
- 对每家企业运行 Taxonomy 评分
- 生成汇总对比表（CSV 格式）
- 保存到 `reports/batch_summary.csv`

### 4. `examples/companies/` 目录
创建 3 个示例企业数据文件：
- `greentech_solutions.json` — 高对齐度（solar_pv + wind_onshore）
- `traditional_energy.json` — 低对齐度（无可再生能源活动）
- `mixed_portfolio.json` — 中等对齐度（部分可再生能源）

## 验证标准

- [ ] `examples/mock_esg_data.json` 可被 API 正确解析
- [ ] `workflows/end_to_end.py` 可运行（需要服务器启动）
- [ ] `workflows/batch_analysis.py` 可处理多个企业
- [ ] 生成的报告包含 Taxonomy 评分 + LCOE 结果
- [ ] `reports/` 目录自动创建

## 自愈规则

1. 如果服务器未启动，脚本应给出清晰错误提示（不是 ConnectionError）
2. 如果 API 返回 422，检查请求体格式是否符合 Pydantic 模型
3. 如果 LCOE 计算失败，跳过该活动并记录警告
4. 如果 `reports/` 目录不存在，自动创建

## 参考文件

- `core/schemas.py` — CompanyESGData, TaxonomyScoreResult, LCOEInput, LCOEResult
- `taxonomy_scorer/api.py` — POST /taxonomy/score, /taxonomy/report/text
- `techno_economics/api.py` — POST /techno/lcoe
- `tests/test_taxonomy_scorer.py` — 参考测试数据格式

## Codex 执行命令

```bash
codex --model gpt-5.4 --approval-policy on-failure \
  --prompt "读取 docs/codex-tasks/task_02_integration.md，创建模块联动工作流：1) examples/mock_esg_data.json，2) workflows/end_to_end.py，3) workflows/batch_analysis.py，4) examples/companies/ 下 3 个示例企业数据。先读取 core/schemas.py 了解数据结构，确保脚本可运行。"
```

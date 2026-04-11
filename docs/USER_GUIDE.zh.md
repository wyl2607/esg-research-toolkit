# ESG Research Toolkit 用户手册

## 1. 安装指南

- Python 3.11 或更高版本
- 已克隆本仓库
- `requirements.txt` 中的依赖
- 配置了 `OPENAI_API_KEY` 的 `.env` 文件

```bash
git clone https://github.com/wyl2607/esg-research-toolkit.git
cd esg-research-toolkit

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
```

至少设置以下内容：

```env
OPENAI_API_KEY=your_openai_api_key_here
DATABASE_URL=sqlite:///./data/esg_toolkit.db
```

## 2. 快速开始

启动 API 服务：

```bash
uvicorn main:app --reload
```

打开交互式文档：

- `http://localhost:8000/docs`

健康检查：

```bash
curl http://localhost:8000/health
```

根路径元数据：

```bash
curl http://localhost:8000/
```

## 3. 模块使用指南

### 3.1 Report Parser（企业报告解析）

Report Parser 会上传企业 PDF，提取文本，调用 OpenAI 驱动的抽取器，并将 ESG 数据写入数据库。

#### `POST /report/upload`

上传 PDF 报告并返回 `CompanyESGData`。

```bash
curl -X POST http://localhost:8000/report/upload \
  -F "file=@/path/to/company_report.pdf"
```

```python
import requests

with open("/path/to/company_report.pdf", "rb") as handle:
    response = requests.post(
        "http://localhost:8000/report/upload",
        files={"file": handle},
    )

response.raise_for_status()
data = response.json()
print(data["company_name"], data["report_year"])
```

`CompanyESGData` 字段：

- `company_name`
- `report_year`
- `scope1_co2e_tonnes`
- `scope2_co2e_tonnes`
- `scope3_co2e_tonnes`
- `energy_consumption_mwh`
- `renewable_energy_pct`
- `water_usage_m3`
- `waste_recycled_pct`
- `total_revenue_eur`
- `taxonomy_aligned_revenue_pct`
- `total_capex_eur`
- `taxonomy_aligned_capex_pct`
- `total_employees`
- `female_pct`
- `primary_activities`

注意：文件上传需要 `python-multipart`，并且 PDF 必须包含可提取文本。

#### `GET /report/companies`

列出已存储的报告。

```bash
curl http://localhost:8000/report/companies
```

#### `GET /report/companies/{company_name}/{report_year}`

获取指定公司和年份的报告。公司名包含空格时要进行 URL 编码。

```bash
curl "http://localhost:8000/report/companies/GreenTech%20Solutions%20GmbH/2024"
```

```python
import requests

response = requests.get(
    "http://localhost:8000/report/companies/GreenTech%20Solutions%20GmbH/2024"
)
response.raise_for_status()
print(response.json())
```

### 3.2 Taxonomy Scorer（EU Taxonomy 评分）

Taxonomy Scorer 会对 `CompanyESGData` 进行 EU Taxonomy 评估，覆盖 6 个环境目标和 DNSH 逻辑。

#### `POST /taxonomy/score`

对公司打分并返回 `TaxonomyScoreResult`。

```bash
curl -X POST http://localhost:8000/taxonomy/score \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "GreenTech Solutions GmbH",
    "report_year": 2024,
    "scope1_co2e_tonnes": 1200,
    "scope2_co2e_tonnes": 340,
    "scope3_co2e_tonnes": 5600,
    "energy_consumption_mwh": 8200,
    "renewable_energy_pct": 85,
    "water_usage_m3": 12500,
    "waste_recycled_pct": 72,
    "total_revenue_eur": 25000000,
    "taxonomy_aligned_revenue_pct": 18,
    "total_capex_eur": 4200000,
    "taxonomy_aligned_capex_pct": 25,
    "total_employees": 180,
    "female_pct": 41,
    "primary_activities": ["solar_pv", "wind_onshore"]
  }'
```

```python
import requests

esg_data = {
    "company_name": "GreenTech Solutions GmbH",
    "report_year": 2024,
    "scope1_co2e_tonnes": 1200,
    "scope2_co2e_tonnes": 340,
    "scope3_co2e_tonnes": 5600,
    "energy_consumption_mwh": 8200,
    "renewable_energy_pct": 85,
    "water_usage_m3": 12500,
    "waste_recycled_pct": 72,
    "total_revenue_eur": 25000000,
    "taxonomy_aligned_revenue_pct": 18,
    "total_capex_eur": 4200000,
    "taxonomy_aligned_capex_pct": 25,
    "total_employees": 180,
    "female_pct": 41,
    "primary_activities": ["solar_pv", "wind_onshore"],
}

response = requests.post("http://localhost:8000/taxonomy/score", json=esg_data)
response.raise_for_status()
result = response.json()
print(f"Revenue aligned: {result['revenue_aligned_pct']:.1f}%")
print(f"DNSH pass: {result['dnsh_pass']}")
```

`TaxonomyScoreResult` 字段：

- `company_name`
- `report_year`
- `revenue_aligned_pct`
- `capex_aligned_pct`
- `opex_aligned_pct`
- `objective_scores`
- `dnsh_pass`
- `gaps`
- `recommendations`

#### `POST /taxonomy/report`

生成结构化 JSON 报告。

```bash
curl -X POST http://localhost:8000/taxonomy/report \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "GreenTech Solutions GmbH",
    "report_year": 2024,
    "scope1_co2e_tonnes": 1200,
    "scope2_co2e_tonnes": 340,
    "scope3_co2e_tonnes": 5600,
    "energy_consumption_mwh": 8200,
    "renewable_energy_pct": 85,
    "water_usage_m3": 12500,
    "waste_recycled_pct": 72,
    "total_revenue_eur": 25000000,
    "taxonomy_aligned_revenue_pct": 18,
    "total_capex_eur": 4200000,
    "taxonomy_aligned_capex_pct": 25,
    "total_employees": 180,
    "female_pct": 41,
    "primary_activities": ["solar_pv", "wind_onshore"]
  }'
```

响应包含：

- `company`
- `report_year`
- `taxonomy_alignment`
- `objective_scores`
- `dnsh_pass`
- `gaps`
- `recommendations`

#### `POST /taxonomy/report/text`

生成纯文本摘要报告。

```bash
curl -X POST http://localhost:8000/taxonomy/report/text \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "GreenTech Solutions GmbH",
    "report_year": 2024,
    "scope1_co2e_tonnes": 1200,
    "scope2_co2e_tonnes": 340,
    "scope3_co2e_tonnes": 5600,
    "energy_consumption_mwh": 8200,
    "renewable_energy_pct": 85,
    "water_usage_m3": 12500,
    "waste_recycled_pct": 72,
    "total_revenue_eur": 25000000,
    "taxonomy_aligned_revenue_pct": 18,
    "total_capex_eur": 4200000,
    "taxonomy_aligned_capex_pct": 25,
    "total_employees": 180,
    "female_pct": 41,
    "primary_activities": ["solar_pv", "wind_onshore"]
  }'
```

响应是一个只有单个键的 JSON 对象：

- `report`

#### `GET /taxonomy/activities`

列出所有支持的 EU Taxonomy 活动。

```bash
curl http://localhost:8000/taxonomy/activities
```

### 3.3 Techno Economics（技术经济分析）

Techno Economics 模块用于计算可再生能源项目的 LCOE、NPV、IRR 以及敏感性分析。

#### `POST /techno/lcoe`

计算指定技术的 LCOE。

```bash
curl -X POST http://localhost:8000/techno/lcoe \
  -H "Content-Type: application/json" \
  -d '{
    "technology": "solar_pv",
    "capex_eur_per_kw": 800,
    "opex_eur_per_kw_year": 15,
    "capacity_factor": 0.18,
    "lifetime_years": 25,
    "discount_rate": 0.07
  }'
```

```python
import requests

lcoe_input = {
    "technology": "solar_pv",
    "capex_eur_per_kw": 800,
    "opex_eur_per_kw_year": 15,
    "capacity_factor": 0.18,
    "lifetime_years": 25,
    "discount_rate": 0.07,
}

response = requests.post("http://localhost:8000/techno/lcoe", json=lcoe_input)
response.raise_for_status()
result = response.json()
print(f"LCOE: {result['lcoe_eur_per_mwh']} EUR/MWh")
print(f"NPV: {result['npv_eur']}")
```

`LCOEResult` 字段：

- `technology`
- `lcoe_eur_per_mwh`
- `npv_eur`
- `irr`
- `payback_years`
- `lifetime_years`

#### `POST /techno/sensitivity`

对 CAPEX 和 OPEX 进行敏感性分析。

```bash
curl -X POST "http://localhost:8000/techno/sensitivity?variation_range=0.2&steps=5" \
  -H "Content-Type: application/json" \
  -d '{
    "technology": "solar_pv",
    "capex_eur_per_kw": 800,
    "opex_eur_per_kw_year": 15,
    "capacity_factor": 0.18,
    "lifetime_years": 25,
    "discount_rate": 0.07
  }'
```

响应是一个对象列表，包含：

- `parameter`
- `base_value`
- `variations`
- `lcoe_values`
- `lcoe_change_pct`

#### `GET /techno/benchmarks`

返回行业基准 LCOE 区间。

```bash
curl http://localhost:8000/techno/benchmarks
```

## 4. 端到端工作流

GreenTech Solutions GmbH 的完整流程示例：

1. 使用 `POST /report/upload` 上传真实 PDF，或者先准备一份手工构造的 `CompanyESGData`。
2. 将抽取出的 ESG 数据发送到 `POST /taxonomy/score`。
3. 用 `POST /techno/lcoe` 评估某个可再生能源技术。
4. 结合 `POST /taxonomy/report` 和 `GET /techno/benchmarks` 生成综合决策材料。

## 5. 故障排查

- 服务无法启动：检查端口 `8000` 是否被占用。
- OpenAI API 错误：确认 `.env` 中已设置 `OPENAI_API_KEY`。
- PDF 上传失败：确认文件是真正的、带可提取文本层的 PDF，而不是纯扫描图片。
- 数据库错误：删除 `data/esg_toolkit.db` 后重新启动，让 SQLite 重新初始化表结构。

## 6. 常见问题（FAQ）

- 支持哪些 PDF 格式？支持包含可提取文本的普通 PDF。
- 如何处理中文 PDF？建议使用带文本层的 PDF，并在上传前验证提取结果。
- EU Taxonomy 评分准确吗？这是一个简化的规则引擎，适合分析和原型验证，不适合做法律合规结论。
- LCOE 使用什么公式？使用折现后的 CAPEX 和 OPEX 除以折现后的发电量，并换算为 EUR/MWh。

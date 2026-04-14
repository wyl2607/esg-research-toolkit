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

如果你要直接运行本手册中的 Python 示例，请额外安装 `requests`：

```bash
pip install requests
```

## 2. 快速开始

启动 API 服务：

```bash
uvicorn main:app --reload
```

打开 API 文档：

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

Report Parser 会上传企业 PDF，提取文本，分析内容，并将结果 ESG 数据存入数据库。

#### `POST /report/upload`

上传 PDF 并返回 `CompanyESGData` 对象。该接口需要 `python-multipart`，并且 PDF 必须包含可提取文本。

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

#### `GET /report/companies`

列出已保存的报告。

```bash
curl http://localhost:8000/report/companies
```

#### `GET /report/companies/{company_name}/{report_year}`

获取指定报告。公司名包含空格时，请进行 URL 编码。

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

Taxonomy Scorer 会对 `CompanyESGData` 进行 EU Taxonomy 评估，覆盖 6 个环境目标和 DNSH 简化逻辑。

#### `POST /taxonomy/score`

对公司评分并返回 `TaxonomyScoreResult`。

```bash
curl -X POST http://localhost:8000/taxonomy/score \
  -H "Content-Type: application/json" \
  --data-binary @examples/mock_esg_data.json
```

```python
import json
from pathlib import Path

import requests

esg_data = json.loads(Path("examples/mock_esg_data.json").read_text())

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
  --data-binary @examples/mock_esg_data.json
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
  --data-binary @examples/mock_esg_data.json
```

```python
import json
from pathlib import Path

import requests

esg_data = json.loads(Path("examples/mock_esg_data.json").read_text())

response = requests.post("http://localhost:8000/taxonomy/report/text", json=esg_data)
response.raise_for_status()
print(response.json()["report"])
```

#### `GET /taxonomy/activities`

列出所有受支持的 EU Taxonomy 活动。

```bash
curl http://localhost:8000/taxonomy/activities
```

### 3.3 Techno Economics（技术经济分析）

Techno Economics 模块用于计算可再生能源项目的 LCOE、NPV、IRR、回收期和敏感性分析。

#### `POST /techno/lcoe`

计算 LCOE / NPV / IRR。

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

inp = {
    "technology": "solar_pv",
    "capex_eur_per_kw": 800,
    "opex_eur_per_kw_year": 15,
    "capacity_factor": 0.18,
    "lifetime_years": 25,
    "discount_rate": 0.07,
}

response = requests.post("http://localhost:8000/techno/lcoe", json=inp)
response.raise_for_status()
result = response.json()
print(f"LCOE: {result['lcoe_eur_per_mwh']:.2f} EUR/MWh")
print(f"NPV: {result['npv_eur']:.2f} EUR")
```

`LCOEResult` 字段：

- `technology`
- `lcoe_eur_per_mwh`
- `npv_eur`
- `irr`
- `payback_years`
- `lifetime_years`

#### `POST /techno/sensitivity`

对 CAPEX 和 OPEX 做敏感性分析。

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

#### `GET /techno/benchmarks`

获取常见技术的 LCOE 基准范围。

```bash
curl http://localhost:8000/techno/benchmarks
```

## 4. 端到端工作流

示例公司：GreenTech Solutions GmbH。

1. 使用 `POST /report/upload` 上传 PDF 报告；如果只是测试评分流程，也可以直接使用 `examples/mock_esg_data.json`。
2. 将提取出的 ESG 数据发送到 `POST /taxonomy/score`。
3. 针对相关技术调用 `POST /techno/lcoe`，例如 `solar_pv` 或 `wind_onshore`。
4. 使用 `POST /taxonomy/report` 和 `POST /taxonomy/report/text` 生成最终报告。

最小 mock 数据流程：

```bash
curl -X POST http://localhost:8000/taxonomy/score \
  -H "Content-Type: application/json" \
  --data-binary @examples/mock_esg_data.json

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

## 5. 故障排查

- 服务无法启动：检查 8000 端口是否被占用。
- OpenAI API 错误：确认 `.env` 中的 `OPENAI_API_KEY` 是否正确。
- PDF 解析失败：确认 PDF 不是纯扫描图像，必须包含可提取文本。
- 上传接口报 multipart 错误：安装 `python-multipart`。
- 数据库异常：删除 `data/esg_toolkit.db`，让应用重新初始化。

## 6. 常见问题

- Q: 支持哪些 PDF 格式？
  A: 支持包含可提取文本的 PDF。纯扫描 PDF 通常需要先做 OCR。
- Q: 如何处理中文 PDF？
  A: 需要 PDF 中存在真实文本层；如果只是图片，需先 OCR。
- Q: EU Taxonomy 评分准确吗？
  A: 这里的实现是简化版，适合分析和原型验证，不是法律意见。
- Q: LCOE 计算使用什么公式？
  A: 使用折现后的 CAPEX 和 OPEX 除以折现后的发电量，单位为 EUR/MWh。


## 相关文件

[[USER_GUIDE.de]]
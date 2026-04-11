# ESG Research Toolkit

Open-source toolkit for corporate ESG analysis: report parsing, EU Taxonomy compliance scoring, and renewable energy techno-economic analysis.

## 第一性原理

**这个工具存在的唯一理由**：帮助分析一家真实企业的 ESG 合规状况，并对其可再生能源项目做技术经济评估。

所有功能必须回答：**"这对分析一家企业的 ESG 数据有直接帮助吗？"**

## Modules

| Module | Description | Status |
|--------|-------------|--------|
| `report_parser` | Extract ESG metrics from corporate PDF reports (annual reports, CSR reports, CSRD disclosures) | 🚧 In Progress |
| `taxonomy_scorer` | EU Taxonomy (2020/852) compliance scoring — 6 objectives + DNSH principle | 📋 Planned |
| `techno_economics` | LCOE / NPV / IRR calculator for renewable energy projects | 📋 Planned |

## Quick Start

```bash
git clone https://github.com/wyl2607/esg-research-toolkit.git
cd esg-research-toolkit

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

uvicorn main:app --reload
```

API docs available at `http://localhost:8000/docs`

## Requirements

- Python 3.11+
- OpenAI API key (for ESG data extraction)

## License

MIT

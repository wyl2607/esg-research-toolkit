# ESG Research Toolkit User Guide

## 1. Installation

- Python 3.11 or newer
- A clone of this repository
- Dependencies from `requirements.txt`
- An `.env` file with `OPENAI_API_KEY`

```bash
git clone https://github.com/wyl2607/esg-research-toolkit.git
cd esg-research-toolkit

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
```

Set at least:

```env
OPENAI_API_KEY=your_openai_api_key_here
DATABASE_URL=sqlite:///./data/esg_toolkit.db
```

If you want to run the Python snippets in this guide, install `requests` as well:

```bash
pip install requests
```

## 2. Quick Start

Start the API server:

```bash
uvicorn main:app --reload
```

Open the API docs:

- `http://localhost:8000/docs`

Check health:

```bash
curl http://localhost:8000/health
```

Check root metadata:

```bash
curl http://localhost:8000/
```

## 3. Module Guide

### 3.1 Report Parser

The Report Parser uploads a corporate PDF, extracts text, analyzes it, and stores the resulting ESG data in the database.

#### `POST /report/upload`

Upload a PDF and receive a `CompanyESGData` object. This route requires `python-multipart`, and the PDF must contain extractable text.

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

`CompanyESGData` fields:

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

List stored reports.

```bash
curl http://localhost:8000/report/companies
```

#### `GET /report/companies/{company_name}/{report_year}`

Retrieve one stored report. URL-encode company names that contain spaces.

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

### 3.2 Taxonomy Scorer

The Taxonomy Scorer evaluates a `CompanyESGData` payload against the EU Taxonomy framework. It covers the six environmental objectives and a simplified DNSH check.

#### `POST /taxonomy/score`

Score a company and receive a `TaxonomyScoreResult`.

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

`TaxonomyScoreResult` fields:

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

Generate a structured JSON report.

```bash
curl -X POST http://localhost:8000/taxonomy/report \
  -H "Content-Type: application/json" \
  --data-binary @examples/mock_esg_data.json
```

The response includes:

- `company`
- `report_year`
- `taxonomy_alignment`
- `objective_scores`
- `dnsh_pass`
- `gaps`
- `recommendations`

#### `POST /taxonomy/report/text`

Generate a plain-text summary report.

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

List all supported EU Taxonomy activities.

```bash
curl http://localhost:8000/taxonomy/activities
```

### 3.3 Techno Economics

The Techno Economics module calculates LCOE, NPV, IRR, payback period, and simple sensitivity outputs for renewable energy projects.

#### `POST /techno/lcoe`

Calculate LCOE / NPV / IRR.

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

`LCOEResult` fields:

- `technology`
- `lcoe_eur_per_mwh`
- `npv_eur`
- `irr`
- `payback_years`
- `lifetime_years`

#### `POST /techno/sensitivity`

Run sensitivity analysis for CAPEX and OPEX over a variation range.

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

Get benchmark LCOE ranges for common technologies.

```bash
curl http://localhost:8000/techno/benchmarks
```

## 4. End-to-End Workflow

Example: GreenTech Solutions GmbH.

1. Upload a PDF report with `POST /report/upload`, or load `examples/mock_esg_data.json` if you only want to test the scoring flow.
2. Send the extracted ESG data to `POST /taxonomy/score`.
3. Run `POST /techno/lcoe` for the relevant technology, such as `solar_pv` or `wind_onshore`.
4. Generate the final outputs with `POST /taxonomy/report` and `POST /taxonomy/report/text`.

Minimal mock-data workflow:

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

## 5. Troubleshooting

- Server will not start: check whether port 8000 is already in use.
- OpenAI API errors: verify `OPENAI_API_KEY` in `.env`.
- PDF parsing fails: confirm the PDF is text-based, not a scanned image.
- Upload endpoint returns a multipart error: install `python-multipart`.
- Database issues: remove `data/esg_toolkit.db` and let the app initialize it again.

## 6. FAQ

- Q: Which PDF formats are supported?
  A: PDF files with extractable text. Scanned PDFs usually need OCR first.
- Q: How do I handle Chinese PDFs?
  A: Use a PDF that contains a real text layer. If the file is image-only, OCR is required before upload.
- Q: How accurate is EU Taxonomy scoring?
  A: The scoring here is a simplified implementation for analysis and prototyping, not a legal opinion.
- Q: What formula does LCOE use?
  A: Discounted CAPEX and OPEX divided by discounted energy output, expressed in EUR/MWh.

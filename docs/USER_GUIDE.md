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

## 2. Quick Start

Run the API server:

```bash
uvicorn main:app --reload
```

Open the interactive docs:

- `http://localhost:8000/docs`

Check service health:

```bash
curl http://localhost:8000/health
```

Root metadata is available at:

```bash
curl http://localhost:8000/
```

## 3. Module Guide

### 3.1 Report Parser

The Report Parser uploads a corporate PDF, extracts text, sends it to the OpenAI-backed extractor, and stores the resulting ESG data in the database.

#### `POST /report/upload`

Upload a PDF report and receive a `CompanyESGData` object.

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

Note: file upload requires the `python-multipart` package, and the PDF must contain extractable text.

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

The Taxonomy Scorer evaluates a `CompanyESGData` payload against the EU Taxonomy framework, including the 6 environmental objectives and DNSH logic.

#### `POST /taxonomy/score`

Score a company and receive a `TaxonomyScoreResult`.

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

The response is a JSON object with a single key:

- `report`

#### `GET /taxonomy/activities`

List all supported EU Taxonomy activities.

```bash
curl http://localhost:8000/taxonomy/activities
```

### 3.3 Techno Economics

The Techno Economics module calculates LCOE, NPV, IRR, and scenario sensitivity for renewable energy projects.

#### `POST /techno/lcoe`

Calculate LCOE for a supported technology.

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

`LCOEResult` fields:

- `technology`
- `lcoe_eur_per_mwh`
- `npv_eur`
- `irr`
- `payback_years`
- `lifetime_years`

#### `POST /techno/sensitivity`

Run CAPEX and OPEX sensitivity analysis.

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

The response is a list of objects with:

- `parameter`
- `base_value`
- `variations`
- `lcoe_values`
- `lcoe_change_pct`

#### `GET /techno/benchmarks`

Return benchmark LCOE ranges.

```bash
curl http://localhost:8000/techno/benchmarks
```

## 4. End-to-End Workflow

Example workflow for GreenTech Solutions GmbH:

1. Upload a real PDF report with `POST /report/upload`, or start with a hand-crafted `CompanyESGData` payload.
2. Send the extracted ESG data to `POST /taxonomy/score`.
3. Run `POST /techno/lcoe` for the renewable technology you want to evaluate.
4. Use `POST /taxonomy/report` and `GET /techno/benchmarks` to assemble a combined decision brief.

## 5. Troubleshooting

- Server will not start: check whether port `8000` is already in use.
- OpenAI API errors: confirm `OPENAI_API_KEY` is set in `.env`.
- PDF upload fails: make sure the file is a real PDF with extractable text, not a scanned image-only document.
- Database errors: delete `data/esg_toolkit.db` and start the app again so SQLite can reinitialize the schema.

## 6. FAQ

- What PDF formats are supported? Regular text-based PDF files.
- How do I handle Chinese PDFs? Use PDFs with embedded text and verify that text extraction works before upload.
- How accurate is EU Taxonomy scoring? It is a simplified rules-based scorer, suitable for analysis and prototyping, not legal assurance.
- What formula does LCOE use? Discounted CAPEX and OPEX divided by discounted energy output, converted to EUR/MWh.

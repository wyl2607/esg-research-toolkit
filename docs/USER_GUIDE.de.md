# ESG Research Toolkit Benutzerhandbuch

## 1. Installationsanleitung

- Python 3.11 oder neuer
- Ein Klon dieses Repositories
- Abhängigkeiten aus `requirements.txt`
- Eine `.env`-Datei mit `OPENAI_API_KEY`

```bash
git clone https://github.com/wyl2607/esg-research-toolkit.git
cd esg-research-toolkit

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
```

Mindestens diese Werte setzen:

```env
OPENAI_API_KEY=your_openai_api_key_here
DATABASE_URL=sqlite:///./data/esg_toolkit.db
```

## 2. Schnellstart

API-Server starten:

```bash
uvicorn main:app --reload
```

Interaktive Dokumentation öffnen:

- `http://localhost:8000/docs`

Health Check:

```bash
curl http://localhost:8000/health
```

Metadaten am Root-Pfad:

```bash
curl http://localhost:8000/
```

## 3. Modullenutzung

### 3.1 Report Parser

Der Report Parser lädt ein Unternehmens-PDF hoch, extrahiert Text, sendet ihn an den OpenAI-gestützten Extraktor und speichert die ESG-Daten in der Datenbank.

#### `POST /report/upload`

PDF-Bericht hochladen und ein `CompanyESGData`-Objekt erhalten.

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

`CompanyESGData`-Felder:

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

Hinweis: Für Datei-Uploads wird `python-multipart` benötigt, und das PDF muss extrahierbaren Text enthalten.

#### `GET /report/companies`

Gespeicherte Berichte auflisten.

```bash
curl http://localhost:8000/report/companies
```

#### `GET /report/companies/{company_name}/{report_year}`

Einen bestimmten Bericht abrufen. Firmennamen mit Leerzeichen müssen URL-kodiert werden.

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

Der Taxonomy Scorer bewertet ein `CompanyESGData`-Payload gegen den EU-Taxonomie-Rahmen, einschließlich der 6 Umweltziele und DNSH-Logik.

#### `POST /taxonomy/score`

Ein Unternehmen bewerten und ein `TaxonomyScoreResult` erhalten.

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

`TaxonomyScoreResult`-Felder:

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

Einen strukturierten JSON-Bericht generieren.

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

Die Antwort enthält:

- `company`
- `report_year`
- `taxonomy_alignment`
- `objective_scores`
- `dnsh_pass`
- `gaps`
- `recommendations`

#### `POST /taxonomy/report/text`

Eine reine Textzusammenfassung erzeugen.

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

Die Antwort ist ein JSON-Objekt mit genau einem Schlüssel:

- `report`

#### `GET /taxonomy/activities`

Alle unterstützten EU-Taxonomie-Aktivitäten auflisten.

```bash
curl http://localhost:8000/taxonomy/activities
```

### 3.3 Techno Economics

Das Techno-Economics-Modul berechnet LCOE, NPV, IRR und Sensitivitätsanalysen für erneuerbare Energieprojekte.

#### `POST /techno/lcoe`

LCOE für eine unterstützte Technologie berechnen.

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

`LCOEResult`-Felder:

- `technology`
- `lcoe_eur_per_mwh`
- `npv_eur`
- `irr`
- `payback_years`
- `lifetime_years`

#### `POST /techno/sensitivity`

CAPEX- und OPEX-Sensitivitätsanalyse ausführen.

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

Die Antwort ist eine Liste von Objekten mit:

- `parameter`
- `base_value`
- `variations`
- `lcoe_values`
- `lcoe_change_pct`

#### `GET /techno/benchmarks`

Benchmark-LCOE-Bereiche zurückgeben.

```bash
curl http://localhost:8000/techno/benchmarks
```

## 4. End-to-End-Workflow

Beispiel für GreenTech Solutions GmbH:

1. Ein echtes PDF mit `POST /report/upload` hochladen oder zunächst ein manuell erstelltes `CompanyESGData`-Payload verwenden.
2. Die extrahierten ESG-Daten an `POST /taxonomy/score` senden.
3. Mit `POST /techno/lcoe` die gewünschte erneuerbare Technologie bewerten.
4. `POST /taxonomy/report` und `GET /techno/benchmarks` kombinieren, um eine Entscheidungsgrundlage zu erstellen.

## 5. Fehlerbehebung

- Server startet nicht: Prüfen, ob Port `8000` bereits belegt ist.
- OpenAI-API-Fehler: Sicherstellen, dass `OPENAI_API_KEY` in `.env` gesetzt ist.
- PDF-Upload schlägt fehl: Sicherstellen, dass die Datei ein echtes PDF mit extrahierbarem Text ist und kein reiner Scan.
- Datenbankfehler: `data/esg_toolkit.db` löschen und die Anwendung neu starten, damit SQLite das Schema neu anlegt.

## 6. FAQ

- Welche PDF-Formate werden unterstützt? Normale PDFs mit extrahierbarem Text.
- Wie gehe ich mit chinesischen PDFs um? PDFs mit eingebettetem Text verwenden und die Textextraktion vor dem Upload prüfen.
- Wie genau ist das EU-Taxonomie-Scoring? Es ist eine vereinfachte regelbasierte Bewertung und eignet sich für Analyse und Prototyping, nicht für rechtliche Verbindlichkeit.
- Welche Formel nutzt LCOE? Abgezinste CAPEX und OPEX geteilt durch abgezinste Energieerzeugung, umgerechnet in EUR/MWh.

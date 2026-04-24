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

Wenn du die Python-Beispiele in diesem Handbuch ausführen willst, installiere zusätzlich `requests`:

```bash
pip install requests
```

## 2. Schnellstart

API-Server starten:

```bash
uvicorn main:app --reload
```

Interaktive API-Dokumentation öffnen:

- `http://localhost:8000/docs`

Health Check:

```bash
curl http://localhost:8000/health
```

Root-Metadaten:

```bash
curl http://localhost:8000/
```

## 3. Modullogik

### 3.1 Report Parser

Der Report Parser lädt ein Unternehmens-PDF hoch, extrahiert Text, analysiert ihn und speichert die resultierenden ESG-Daten in der Datenbank.

#### `POST /report/upload`

PDF hochladen und ein `CompanyESGData`-Objekt erhalten. Dieser Endpunkt benötigt `python-multipart`, und das PDF muss extrahierbaren Text enthalten.

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

#### `GET /report/companies`

Gespeicherte Berichte auflisten.

```bash
curl http://localhost:8000/report/companies
```

#### `GET /report/companies/{company_name}/{report_year}`

Einen gespeicherten Bericht abrufen. Firmennamen mit Leerzeichen müssen URL-kodiert werden.

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

Der Taxonomy Scorer bewertet ein `CompanyESGData`-Payload gegen das EU-Taxonomie-Rahmenwerk. Er deckt die sechs Umweltziele und eine vereinfachte DNSH-Prüfung ab.

#### `POST /taxonomy/score`

Ein Unternehmen bewerten und ein `TaxonomyScoreResult` erhalten.

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

Einen strukturierten JSON-Bericht erzeugen.

```bash
curl -X POST http://localhost:8000/taxonomy/report \
  -H "Content-Type: application/json" \
  --data-binary @examples/mock_esg_data.json
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

Alle unterstützten EU-Taxonomie-Aktivitäten auflisten.

```bash
curl http://localhost:8000/taxonomy/activities
```

### 3.3 Techno Economics

Das Techno-Economics-Modul berechnet LCOE, NPV, IRR, Amortisationszeit und einfache Sensitivitätsanalysen für erneuerbare Energieprojekte.

#### `POST /techno/lcoe`

LCOE / NPV / IRR berechnen.

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

`LCOEResult`-Felder:

- `technology`
- `lcoe_eur_per_mwh`
- `npv_eur`
- `irr`
- `payback_years`
- `lifetime_years`

#### `POST /techno/sensitivity`

Sensitivitätsanalyse für CAPEX und OPEX durchführen.

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

Referenzbereiche für LCOE typischer Technologien abrufen.

```bash
curl http://localhost:8000/techno/benchmarks
```

## 4. End-to-End-Workflow

Beispiel: GreenTech Solutions GmbH.

1. Lade einen PDF-Bericht mit `POST /report/upload` hoch, oder nutze `examples/mock_esg_data.json`, wenn du nur den Scoring-Workflow testen willst.
2. Sende die extrahierten ESG-Daten an `POST /taxonomy/score`.
3. Führe für die passende Technologie `POST /techno/lcoe` aus, zum Beispiel `solar_pv` oder `wind_onshore`.
4. Erzeuge die Endberichte mit `POST /taxonomy/report` und `POST /taxonomy/report/text`.

Minimaler Mock-Workflow:

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

## 5. Fehlerbehebung

- Server startet nicht: Prüfe, ob Port 8000 bereits belegt ist.
- OpenAI-API-Fehler: Prüfe `OPENAI_API_KEY` in `.env`.
- PDF-Analyse schlägt fehl: Stelle sicher, dass das PDF Text enthält und nicht nur gescannt ist.
- Upload-Fehler wegen Multipart: Installiere `python-multipart`.
- Datenbankfehler: Lösche `data/esg_toolkit.db` und initialisiere die App neu.

## 6. FAQ

- F: Welche PDF-Formate werden unterstützt?
  A: PDFs mit extrahierbarem Text. Nur gescannte PDFs benötigen vorher OCR.
- F: Wie gehe ich mit chinesischen PDFs um?
  A: Das PDF muss eine echte Textebene enthalten. Bei Bild-PDFs ist OCR erforderlich.
- F: Wie genau ist die EU-Taxonomie-Bewertung?
  A: Die Implementierung ist bewusst vereinfacht und eignet sich für Analyse und Prototyping, nicht als Rechtsberatung.
- F: Welche Formel verwendet LCOE?
  A: Diskontierte CAPEX und OPEX geteilt durch die diskontierte Stromerzeugung, angegeben in EUR/MWh.

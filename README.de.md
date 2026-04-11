[![Tests](https://github.com/wyl2607/esg-research-toolkit/actions/workflows/test.yml/badge.svg)](https://github.com/wyl2607/esg-research-toolkit/actions/workflows/test.yml)
[![Lint](https://github.com/wyl2607/esg-research-toolkit/actions/workflows/lint.yml/badge.svg)](https://github.com/wyl2607/esg-research-toolkit/actions/workflows/lint.yml)

# ESG Research Toolkit

Das ESG Research Toolkit ist ein Open-Source-Werkzeugkasten fuer die ESG-Analyse von Unternehmen. Er vereint PDF-Berichtsparsing, EU-Taxonomie-Scoring und techno-oekonomische Modellierung fuer Projekte im Bereich erneuerbarer Energien in einem gemeinsamen FastAPI-Service.

## Projektueberblick

Das Projekt verfolgt ein klares Ziel: reale ESG-Offenlegungen von Unternehmen reproduzierbar auszuwerten und gleichzeitig die Wirtschaftlichkeit ihrer Projekte im Bereich erneuerbarer Energien ueber einen API-first-Workflow zu bewerten.

Aktueller Release-Status:

- Version: `v0.1.0`
- Repository: `https://github.com/wyl2607/esg-research-toolkit`
- Snapshot-Datum: `2026-04-12`

## Kernmodule

### 1. `report_parser`

Analysiert PDF-Berichte von Unternehmen und ueberfuehrt unstrukturierte Offenlegungen in strukturierte ESG-Daten.

- Extrahiert Text aus hochgeladenen PDF-Berichten mit `pdfplumber`
- Nutzt die OpenAI API zur Identifikation und Extraktion von ESG-Kennzahlen
- Persistiert strukturierte Ergebnisse ueber SQLAlchemy ORM
- Liefert normalisierte `CompanyESGData`-Objekte fuer nachgelagerte Bewertungsprozesse

### 2. `taxonomy_scorer`

Bewertet Unternehmensdaten entlang des EU-Taxonomie-Rahmenwerks.

- Bewertet die Ausrichtung auf alle 6 Umweltziele
- Beruecksichtigt das Do No Significant Harm (`DNSH`)-Prinzip
- Verwendet Schwellenwerte aus den Technical Screening Criteria (`TSC`) fuer unterstuetzte Aktivitaeten
- Erzeugt maschinenlesbare Reports und Textzusammenfassungen
- Enthaelt eine Gap-Analyse mit den Schweregraden `critical`, `high`, `medium`, `low`

### 3. `techno_economics`

Fuehrt wirtschaftliche Berechnungen und Szenarioanalysen fuer Projekte im Bereich erneuerbarer Energien durch.

- Berechnet die Stromgestehungskosten (`LCOE`, Levelized Cost of Energy)
- Berechnet Kapitalwert (`NPV`), interne Verzinsung (`IRR`) und Amortisationskennzahlen
- Fuehrt Sensitivitaetsanalysen fuer CAPEX und OPEX durch
- Stellt Referenzbereiche fuer LCOE ausgewahlter Technologien bereit

## Schnellstart

### Voraussetzungen

- Python `3.11+`
- Ein gueltiger OpenAI API Key

### Installation

```bash
git clone https://github.com/wyl2607/esg-research-toolkit.git
cd esg-research-toolkit

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Konfiguration

```bash
cp .env.example .env
```

Mindestens die folgenden Variablen setzen:

```env
OPENAI_API_KEY=your_openai_api_key_here
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
DATABASE_URL=sqlite:///./data/esg_toolkit.db
```

### Service starten

```bash
uvicorn main:app --reload
```

Interaktive API-Dokumentation:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Tests ausfuehren

```bash
pytest tests/ -v
```

## Docker-Bereitstellung

### Schnellstart

```bash
cp .env.example .env
docker compose up -d
docker compose ps
docker compose logs -f
docker compose down
```

### Umgebungsvariablen

Lege in `.env` mindestens Folgendes fest:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

Der Container verwendet standardmaessig `DATABASE_URL=sqlite:///./data/esg_toolkit.db` und bindet `./data` sowie `./reports` als persistente Volumes ein.

## API-Endpunkte

### System

| Methode | Endpunkt | Beschreibung |
| --- | --- | --- |
| `GET` | `/` | Service-Metadaten und Modulliste |
| `GET` | `/health` | Health-Check |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc |
| `GET` | `/openapi.json` | OpenAPI-Schema |

### Report Parser

| Methode | Endpunkt | Beschreibung |
| --- | --- | --- |
| `POST` | `/report/upload` | PDF-Bericht hochladen und strukturierte `CompanyESGData` zurueckgeben |
| `GET` | `/report/companies` | Gespeicherte Unternehmensberichte auflisten |
| `GET` | `/report/companies/{company_name}/{report_year}` | Einen bestimmten Unternehmensbericht abrufen |

### Taxonomy Scorer

| Methode | Endpunkt | Beschreibung |
| --- | --- | --- |
| `POST` | `/taxonomy/score` | Ein `CompanyESGData`-Payload gegen die EU-Taxonomie bewerten |
| `POST` | `/taxonomy/report` | Einen strukturierten Taxonomie-Report mit Gap-Analyse erzeugen |
| `POST` | `/taxonomy/report/text` | Eine textuelle Taxonomie-Zusammenfassung erzeugen |
| `GET` | `/taxonomy/activities` | Alle aktuell unterstuetzten EU-Taxonomie-Aktivitaeten auflisten |

### Techno Economics

| Methode | Endpunkt | Beschreibung |
| --- | --- | --- |
| `POST` | `/techno/lcoe` | `LCOE`, `NPV` und `IRR` berechnen |
| `POST` | `/techno/sensitivity` | Sensitivitaetsanalyse fuer CAPEX und OPEX ausfuehren |
| `GET` | `/techno/benchmarks` | Referenzbereiche fuer LCOE ausgewaehlter Technologien zurueckgeben |

## Technologiestack

- Backend: FastAPI, Uvicorn
- Datenvalidierung: Pydantic v2
- Datenbank: SQLAlchemy 2.0, SQLite
- KI-gestuetzte Extraktion: OpenAI API
- PDF-Verarbeitung: pdfplumber
- Wissenschaftliches Rechnen: NumPy, SciPy
- Datenwerkzeuge: pandas, openpyxl
- Reporting: ReportLab, python-docx
- Tests: pytest, pytest-asyncio

## Projektkennzahlen

Projekt-Snapshot fuer `v0.1.0`:

| Kennzahl | Wert |
| --- | --- |
| Versionierte Dateien | 37 |
| Kernmodule | 3 |
| API-Endpunkte | 15 |
| Automatisierte Tests | 19 |
| Dokumentierte Erfolgsquote der Tests | 100% |
| Python-Version | 3.11+ |

## Architektur- und Designprinzipien

- First-Principles-Umfang: nur Funktionen, die ESG-Compliance-Analysen und die Bewertung erneuerbarer Energieprojekte direkt unterstuetzen
- API-first: jede Kernfaehigkeit ist ueber dokumentierte HTTP-Endpunkte verfuegbar
- Typsicherheit: Pydantic-Schemas und explizite Python-Typisierung
- Modularitaet: Berichtsparsing, Taxonomie-Scoring und techno-oekonomische Analyse sind getrennt entwickelt, aber interoperabel
- Testgestuetzte Entwicklung: die zentrale Fachlogik ist durch automatisierte Tests abgesichert

## Mitwirken

Beitraege sind willkommen.

1. Repository forken.
2. Einen Feature-Branch erstellen.
3. Aenderungen klein, testbar und im Einklang mit dem fachlichen Kernumfang halten.
4. Vor dem Pull Request Linting und Tests ausfuehren.
5. Im Pull Request die fachliche Motivation und die Verifikation klar dokumentieren.

Bevorzugt werden Beitraege, die ESG-Analyseablaeufe, die Genauigkeit des EU-Taxonomie-Scorings oder die Qualitaet der techno-oekonomischen Modellierung verbessern, ohne den Projektumfang unnoetig zu erweitern.

## Lizenz

Das Projekt wird unter der MIT License veroeffentlicht.

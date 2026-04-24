# ESG Research Toolkit

🌐 [English](README.md) · [中文](README.zh.md) · [Deutsch](README.de.md)

> Open-Source-Plattform zur Analyse von Unternehmens-ESG-Berichten, für EU-Taxonomie-Compliance-Scoring,
> Multi-Framework-Vergleiche (EU-Taxonomie 2020 · China CSRC 2023 · EU CSRD/ESRS)
> sowie techno-ökonomische Analysen erneuerbarer Energien (LCOE/NPV/IRR).

![Python](https://img.shields.io/badge/Python-3.12%2B-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688) ![React](https://img.shields.io/badge/React-19%2B-61DAFB) ![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Funktionen

- 📄 ESG-Berichte werden aus Uploads geparst und als strukturierte Nachhaltigkeitsdaten extrahiert.
- 🧮 Die EU-Taxonomie-Ausrichtung für Umsatz, CapEx und OpEx wird regelbasiert berechnet.
- 🧠 Multi-Framework-Scoring über EU-Taxonomie 2020, China CSRC 2023 und EU CSRD/ESRS.
- ⚡ Compliance-Lückenanalyse mit konkreten, priorisierbaren Handlungsempfehlungen.
- 📊 Export von Unternehmensdatensätzen als CSV/XLSX sowie PDF-Report-Erstellung.
- 🔬 Berechnung von LCOE und Sensitivitätsanalysen für Energieprojekte.
- 🖥️ React-Frontend für Upload, Dashboard, Vergleich und Historie.
- 🎯 **Lücken-bewusster Unternehmen+Jahr-Picker**: zeigt bereits importierte vs. fehlende Berichtsjahre und springt per Deep-Link direkt in den Upload- bzw. Auto-Fetch-Workflow.
- 📥 **Pending-Disclosures-Workbench**: Analyst:innen-Review für automatisch geholte Berichte aus offiziellen Quellen (Unternehmensseite, SEC EDGAR, HKEX, CSRC/CNINFO) mit feldweiser Freigabe und Lane-Zuverlässigkeits-Ranking.
- 💱 Regionsabhängige LCOE-Defaults (EUR / USD) inkl. EIA-Referenzpreisen für die englische Oberfläche.
- 🐳 Docker-basierter Start mit persistenter Speicherung in `data/` und `reports/`.

## 🚀 Schnellstart

### Voraussetzungen

- Python 3.12+
- Node.js 18+
- Docker (optional)

### Lokale Entwicklung

1. Repository klonen und in das Projekt wechseln:

```bash
git clone https://github.com/wyl2607/esg-research-toolkit.git
cd esg-research-toolkit
```

2. Backend-Abhängigkeiten installieren und FastAPI starten:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
```

3. Frontend in einem zweiten Terminal starten:

```bash
cd frontend
npm install
npm run dev
```

### Frontend-Health-Check an Werktagen

Vollständigen Frontend-Health-Pass ausführen (lint, build, Playwright smoke, axe, Lighthouse):

```bash
cd frontend
npm run health:check
```

Wenn Fehler, Bundle-Regressionen, offensichtliche Layoutprobleme oder neue Console-/Network-Fehler erkannt werden, wird eine Zusammenfassung erzeugt unter:

```text
frontend/health-reports/latest/summary.md
```

### Docker

Den Backend-Stack mit Docker Compose starten:

```bash
cp .env.example .env
docker-compose up -d --build
```

Die Backend-API ist anschließend unter `http://localhost:8000` erreichbar.

## 📡 API-Referenz

Die folgende Tabelle basiert auf den aktuell registrierten FastAPI-Routen in `main.py`.

| Method | Endpoint | Beschreibung |
|---|---|---|
| GET | `/` | Root-Endpunkt mit Basisantwort zur Erreichbarkeit. |
| GET | `/docs` | Swagger UI für interaktive API-Dokumentation. |
| GET | `/docs/oauth2-redirect` | OAuth-Redirect-Helfer für Swagger UI. |
| GET | `/frameworks/compare` | Vergleich von Ergebnissen über mehrere ESG-Frameworks. |
| GET | `/frameworks/list` | Liste unterstützter ESG-Frameworks mit Metadaten. |
| GET | `/frameworks/score` | Framework-Scoring per Query-Parameter. |
| POST | `/frameworks/score/upload` | Report hochladen und Multi-Framework-Scoring ausführen. |
| GET | `/health` | Health-Check-Endpunkt des Services. |
| GET | `/openapi.json` | OpenAPI-Schema als JSON. |
| GET | `/redoc` | ReDoc-Dokumentationsseite. |
| GET | `/report/companies` | Gespeicherte Unternehmensdatensätze auflisten. |
| GET | `/report/companies/v2` | Unternehmen mit importierten + vorgeschlagenen Jahren (liefert den Gap-Picker). |
| POST | `/disclosures/fetch` | Auto-Fetch-Versuch aus offiziellen Quellen für `(Unternehmen, Jahr)` einreihen. |
| GET | `/disclosures/pending` | Ausstehende auto-geholte Disclosures zur Analystenprüfung auflisten. |
| POST | `/disclosures/{id}/approve` | Ausgewählte Kennzahlen einer Pending-Disclosure in die Unternehmenshistorie übernehmen. |
| POST | `/disclosures/{id}/reject` | Pending-Disclosure mit Analystennotiz ablehnen. |
| GET | `/disclosures/lane-stats` | Zuverlässigkeitstelemetrie je Quelle-Lane + empfohlene Reihenfolge. |
| GET | `/report/companies/export/csv` | Unternehmensdatensätze als CSV exportieren. |
| GET | `/report/companies/export/xlsx` | Unternehmensdatensätze als Excel exportieren. |
| GET | `/report/companies/{company_name}/{report_year:int}` | Einzelnen Datensatz nach Schlüssel abrufen. |
| DELETE | `/report/companies/{company_name}/{report_year:int}` | Datensatz endgültig löschen. |
| POST | `/report/companies/{company_name}/{report_year:int}/request-deletion` | Löschanfrage für einen Datensatz anlegen. |
| GET | `/report/jobs/{batch_id}` | Status eines Batch-Upload-Jobs abrufen. |
| POST | `/report/upload` | Einzelnen ESG-Report hochladen und parsen. |
| POST | `/report/upload/batch` | Mehrere ESG-Reports im Batch hochladen. |
| GET | `/taxonomy/activities` | Katalog der Taxonomie-Aktivitäten abrufen. |
| POST | `/taxonomy/report` | Taxonomie-Report aus strukturierten Eingaben erzeugen. |
| GET | `/taxonomy/report` | Vorhandenen Taxonomie-Report nach Firma/Jahr lesen. |
| GET | `/taxonomy/report/pdf` | Taxonomie-PDF-Report generieren und herunterladen. |
| POST | `/taxonomy/report/text` | Narrativen Text-Report zur Taxonomie erzeugen. |
| POST | `/taxonomy/score` | EU-Taxonomie-Scoring für übergebene Kennzahlen. |
| GET | `/techno/benchmarks` | Benchmark-Annahmen für techno-ökonomische Analysen. |
| POST | `/techno/lcoe` | LCOE-Berechnung für Projektparameter. |
| POST | `/techno/sensitivity` | Sensitivitätsanalyse für techno-ökonomische Annahmen. |

## 🛡 Auto-Fetch Compliance-Leitplanken (F2)

Der Disclosure-Backfill-Flow (`POST /disclosures/fetch` + Pending-Review in der Upload-Seite) ist absichtlich eingeschränkt:

- **Unterstützte offizielle Quellenpfade:** Unternehmens-Webseiten, SEC EDGAR, HKEX und CSRC/CNINFO.
- **Explizit ausgeschlossen:** kostenpflichtige/proprietäre ESG-Datenanbieter und Drittseiten mit Scraper-Aggregaten.
- **Identifikation:** Requests tragen einen projektbezogenen User-Agent (`esg-research-toolkit/<ver> (+contact)`).
- **Rate- und Merge-Policy:** host-bezogene Abrufrate und globale Parallelität sind begrenzt; Ergebnisse landen zuerst in `pending_disclosures` und werden erst nach explizitem Approve/Reject übernommen.

## 🏗 Architektur

```text
React Frontend (Vite)
        |
        v
      Nginx
        |
        v
 FastAPI Backend (main.py)
        |
        v
 SQLite (data/esg_toolkit.db) + File Reports (reports/)
```

Das Frontend steuert Upload-, Bewertungs- und Auswertungsabläufe. FastAPI stellt die Rechen- und Reporting-Endpunkte bereit. Persistenz erfolgt über SQLite, Artefakte liegen im Verzeichnis `reports/`.

## 🌍 Multi-Framework ESG

### EU-Taxonomie 2020

Die EU-Taxonomie bewertet Umweltkonformität über aktivitätsspezifische Kriterien sowie Umsatz-/CapEx-/OpEx-Ausrichtung. Das Toolkit enthält DNSH-Prüfungen und konkrete Gap-Empfehlungen.

### China CSRC 2023

CSRC 2023 fokussiert verpflichtende ESG-Offenlegung für börsennotierte Unternehmen entlang E/S/G-Dimensionen. Extrahierte Berichtsdaten werden in CSRC-kompatible Bewertungsstrukturen überführt.

### EU CSRD / ESRS

CSRD/ESRS erweitert die Berichtsanforderungen über Umwelt-, Sozial- und Governance-Themen hinweg. Die Plattform ermöglicht den direkten Framework-Vergleich zur Identifikation von Überschneidungen und Lücken.

## 📊 Frontend-Seiten

- `DashboardPage.tsx`: KPI-Überblick und zusammenfassende Ergebnisdarstellung.
- `UploadPage.tsx`: Upload-Prozess für Einzel- und Batch-Dateien (erkennt `?company=&year=` Deep-Links aus dem Gap-Picker).
- `PendingDisclosuresPage.tsx`: Analystenfreigabe für automatisch geholte offizielle Disclosures (`/disclosures`).
- `TaxonomyPage.tsx`: Arbeitsfläche für EU-Taxonomie-Scoring und Berichte.
- `FrameworksPage.tsx`: Framework-orientierte Bewertung und Standardsicht.
- `ComparePage.tsx`: Nebeneinandervergleich unterschiedlicher Framework-Ergebnisse.
- `LcoePage.tsx`: Berechnung von LCOE und Sensitivitätsvarianten.
- `CompaniesPage.tsx`: Historie, Suche und Export gespeicherter Unternehmensdaten.

## 🔧 Konfiguration

Umgebungsvariablen werden aus `.env` geladen.

| Variable | Beispiel | Beschreibung |
|---|---|---|
| `OPENAI_API_KEY` | `sk-...` | API-Schlüssel für modellgestützte Parsing-/Enrichment-Funktionen. |
| `APP_ENV` | `development` | Laufzeitmodus, beeinflusst Logging und Feature-Toggles. |
| `APP_HOST` | `0.0.0.0` | Bind-Host des Backends. |
| `APP_PORT` | `8000` | Bind-Port des Backends. |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173,http://localhost:4173` | Kommagetrennte erlaubte Browser-Origins. In Produktion explizit auf Deployment-Domains setzen. |
| `ADMIN_API_TOKEN` | leer | Optionales Token für destruktive Admin-Routen über `X-Admin-Token`; bei `APP_ENV=production` erforderlich. |
| `DATABASE_URL` | `sqlite:///./data/esg_toolkit.db` | SQLAlchemy-Verbindungszeichenfolge zur Datenbank. |
| `ARXIV_MAX_RESULTS` | `20` | Maximale Trefferzahl für Literaturabfragen. |
| `ARXIV_DOWNLOAD_PDF` | `true` | Steuert PDF-Download im Literatur-Workflow. |
| `LOG_LEVEL` | `INFO` | Detailgrad der Protokollausgabe. |
| `BATCH_MAX_WORKERS` | `2` | Anzahl paralleler Worker im Batch-Processing. |

## 🗄️ Datenbankinitialisierung (Alembic zuerst)

Datenbankschema-Änderungen mit Alembic anwenden:

```bash
./scripts/db_init.sh
# or
alembic upgrade head
```

Für bestehende Produktionsdatenbanken mit vorhandenen Schemas oder Daten zuerst diesen Runbook befolgen:

- `docs/runbooks/alembic_cutover.md` (enthält `alembic stamp 0001_baseline` + `alembic upgrade head`)

Kompatibilitätshinweis:

- `scripts/migrate_db.py` bleibt nur als Kompatibilitäts-Shim für alte Abläufe erhalten und gibt Alembic-Hinweise aus; es schreibt kein Schema mehr.

## 🤝 Beitrag leisten

1. Forken Sie das Repository und erstellen Sie einen Feature-Branch.
2. Ergänzen oder aktualisieren Sie Tests für Ihre Änderungen.
3. Führen Sie lokale Prüfungen vor dem Pull Request aus.
4. Beschreiben Sie im PR klar Umfang, Validierung und ggf. Migration.

## 📄 Lizenz

MIT

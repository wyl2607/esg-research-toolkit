# ESG Research Toolkit

🌐 [English](README.md) · [中文](README.zh.md) · [Deutsch](README.de.md)

> Open-Source-Plattform für die Analyse von ESG-Berichten, mit EU-Taxonomie-Scoring,
> Multi-Framework-Vergleich (EU-Taxonomie 2020 · China CSRC 2023 · EU CSRD/ESRS)
> sowie techno-ökonomischer Analyse für erneuerbare Energien (LCOE/NPV/IRR).

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](#) [![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?logo=fastapi&logoColor=white)](#) [![React 19](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](#) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](#) [![Live Demo](https://img.shields.io/badge/Live%20Demo-Coming%20Soon-lightgrey)](#)

## ✨ Funktionen
- 🔍 Einzel- und Batch-Upload von ESG-PDFs über FastAPI-Endpunkte.
- 🧠 Strukturierte ESG-Kennzahlen durch OpenAI-gestützte Textanalyse.
- 🗂 Persistenz von Unternehmensberichten in SQLite über SQLAlchemy.
- 📏 EU-Taxonomie-Scoring inklusive DNSH- und TSC-Prüfungen.
- 🌍 Vergleich von drei Frameworks: EU-Taxonomie 2020, CSRC 2023 und CSRD/ESRS.
- 📉 Techno-ökonomische Berechnungen für Projekte (LCOE, NPV, IRR, Payback).
- 📊 Benchmark- und Sensitivitätsdiagramme im React-Frontend.
- 📄 Ausgabe als JSON-Report und herunterladbare PDF-Zusammenfassung.

## 🚀 Schnellstart

### Voraussetzungen
- Python 3.12+, Node 18+, Docker (optional)

### Lokale Entwicklung
1. Repository klonen und wechseln:
   ```bash
   git clone https://github.com/wyl2607/esg-research-toolkit.git
   cd esg-research-toolkit
   ```
2. Backend-API starten:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```
3. Frontend-Dashboard starten:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

### Docker
```bash
cp .env.example .env
docker compose up --build
```

## 📡 API-Referenz

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/` | Service-Metadaten und Modulüberblick |
| `GET` | `/docs` | Swagger-UI-Dokumentation |
| `GET` | `/docs/oauth2-redirect` | OAuth2-Redirect-Helfer für Swagger |
| `GET` | `/frameworks/compare` | Unternehmen über alle Frameworks vergleichen |
| `GET` | `/frameworks/list` | Unterstützte ESG-Frameworks und Metadaten auflisten |
| `GET` | `/frameworks/score` | Unternehmen gegen ein einzelnes Framework bewerten |
| `POST` | `/frameworks/score/upload` | Hochgeladene CompanyESGData über alle Frameworks bewerten |
| `GET` | `/health` | Gesundheitsprüfung des Services |
| `GET` | `/openapi.json` | OpenAPI-Schema |
| `GET` | `/redoc` | ReDoc-Dokumentation |
| `GET` | `/report/companies` | Gespeicherte ESG-Berichte auflisten |
| `GET` | `/report/companies/{company_name}/{report_year}` | Einen gespeicherten Unternehmensbericht abrufen |
| `GET` | `/report/jobs/{batch_id}` | Status eines Batch-Uploads prüfen |
| `POST` | `/report/upload` | Eine PDF hochladen und ESG-Daten extrahieren |
| `POST` | `/report/upload/batch` | Bis zu 20 PDFs asynchron hochladen |
| `GET` | `/taxonomy/activities` | Unterstützte EU-Taxonomie-Aktivitäten auflisten |
| `POST` | `/taxonomy/report` | Strukturierten Taxonomie-Report (JSON) erzeugen |
| `GET` | `/taxonomy/report` | Strukturierten Taxonomie-Report (JSON) erzeugen |
| `GET` | `/taxonomy/report/pdf` | Taxonomie-Report als PDF herunterladen |
| `POST` | `/taxonomy/report/text` | Textzusammenfassung zur Taxonomie erzeugen |
| `POST` | `/taxonomy/score` | EU-Taxonomie-Scoring zurückgeben |
| `GET` | `/techno/benchmarks` | Benchmark-LCOE-Bereiche zurückgeben |
| `POST` | `/techno/lcoe` | LCOE, NPV, IRR und Payback berechnen |
| `POST` | `/techno/sensitivity` | CAPEX/OPEX-Sensitivitätsanalyse ausführen |

## 🏗 Architektur

```text
React Frontend (Vite)
        ↓
Nginx (production reverse proxy)
        ↓
FastAPI Backend
        ↓
SQLite + Local Storage (data/, reports/)
```

Das Frontend ruft die FastAPI-Endpunkte per HTTP auf; die Backend-Module teilen sich
eine Datenbank sowie ein gemeinsames Dateisystem für Reports und Ausgaben.

## 🌍 Multi-Framework-ESG

### EU-Taxonomie 2020
Abdeckung der sechs Umweltziele inklusive Do-No-Significant-Harm-Prüfungen.
Nutzen Sie dieses Framework für EU-konformes Scoring mit technischen Schwellenwerten.

### China CSRC 2023
Abbildung der chinesischen Leitlinien für Nachhaltigkeitsberichte börsennotierter Unternehmen.
Nutzen Sie es für E/S/G-Abdeckungsanalysen und lokale Offenlegungsbereitschaft.

### EU CSRD/ESRS
Erweitert die Bewertung auf ESRS-Themen wie E1-E5, S1 und G1.
Nutzen Sie dieses Framework für Vollständigkeits-Benchmarks im EU-Offenlegungskontext.

## 📊 Frontend-Seiten

- `DashboardPage.tsx` — Portfolio-KPIs und schnelle Drill-down-Aktionen.
- `UploadPage.tsx` — Einzel- und Batch-Upload von ESG-PDFs mit Statusanzeige.
- `CompaniesPage.tsx` — Suche, Sortierung und Verwaltung gespeicherter Berichte.
- `TaxonomyPage.tsx` — EU-Taxonomie-Radar, Gap-Analyse und PDF-Export.
- `FrameworksPage.tsx` — Vergleich von EU-Taxonomie, CSRC und CSRD.
- `ComparePage.tsx` — Tabellarischer Kennzahlenvergleich mehrerer Unternehmen.
- `LcoePage.tsx` — LCOE-Rechner mit Benchmark- und Sensitivitätsdiagrammen.

## 🔧 Konfiguration

| Variable | Default | Description |
| --- | --- | --- |
| `OPENAI_API_KEY` | `Required` | OpenAI-API-Schlüssel für die ESG-Extraktion |
| `APP_ENV` | `development` | Anwendungsumgebung (development/production) |
| `APP_HOST` | `0.0.0.0` | Bind-Adresse des Backends |
| `APP_PORT` | `8000` | Port des Backends |
| `DATABASE_URL` | `sqlite:///./data/esg_toolkit.db` | SQLAlchemy-Verbindungszeichenfolge |
| `ARXIV_MAX_RESULTS` | `20` | Maximale Trefferzahl für die Literatur-Pipeline |
| `ARXIV_DOWNLOAD_PDF` | `true` | Legt fest, ob arXiv-PDFs heruntergeladen werden |
| `LOG_LEVEL` | `INFO` | Log-Level zur Laufzeit |
| `BATCH_MAX_WORKERS` | `2` | Maximale Parallelität für Batch-Verarbeitung |

## 🤝 Mitwirken

1. Forken Sie das Repository und erstellen Sie einen Feature-Branch.
2. Halten Sie Änderungen fokussiert und begründen Sie Ihre Commits klar.
3. Führen Sie vor dem PR Backend-Tests sowie Frontend-Lint/Build aus.
4. Ergänzen Sie im PR die verwendeten Prüfkommandos und Ergebnisse.
5. Öffnen Sie einen Pull Request und reagieren Sie zügig auf Feedback.

## 📄 Lizenz

MIT

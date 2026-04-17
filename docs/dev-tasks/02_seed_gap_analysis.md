# Seed Pipeline Gap Analysis

**Manifest**: `scripts/seed_data/german_demo_manifest.json` (36 entries)
**DB**: `sqlite:///./data/esg_toolkit.db` (36 (company, year) pairs)

## 1. Manifest Coverage Matrix

| Company | 2022 | 2023 | 2024 |
|---|:-:|:-:|:-:|
| `BASF SE` | ✅ | ✅ | ✅ |
| `BMW AG` | ✅ | ✅ | ✅ |
| `DHL Group` | ✅ | ✅ | ✅ |
| `Deutsche Telekom AG` | ✅ | ✅ | ✅ |
| `E.ON SE` | — | — | ✅ |
| `EnBW Energie Baden-Württemberg AG` | — | — | ✅ |
| `Fresenius SE & Co. KGaA` | — | — | ✅ |
| `Heidelberg Materials AG` | — | — | ✅ |
| `Henkel AG & Co. KGaA` | — | ✅ | ✅ |
| `Linde plc` | — | — | ✅ |
| `Merck KGaA, Darmstadt, Germany` | — | — | ✅ |
| `Munich Re` | — | — | ✅ |
| `PUMA SE` | — | — | ✅ |
| `Porsche AG` | — | — | ✅ |
| `RWE AG` | ✅ | ✅ | ✅ |
| `SAP SE` | ✅ | ✅ | ✅ |
| `Salzgitter AG` | — | — | ✅ |
| `Siemens AG` | — | ✅ | — |
| `Uniper SE` | — | — | ✅ |
| `Volkswagen AG` | ✅ | ✅ | ✅ |
| `thyssenkrupp AG` | — | — | ✅ |

## 2. In Manifest but NOT in DB

_All manifest entries are loaded._ 🎉

## 3. In DB but NOT in Manifest (possible drift)

_All DB rows have a matching manifest entry._ 🎉

## 4. Companies Missing 2022/2023 (high-impact gaps)

These companies have 2024 data but are missing historical years. Filling these would immediately unlock more multi-year trend charts.

### `E.ON SE`

- Missing: [2022, 2023]
- 2024 URL: `https://annualreport.eon.com/content/dam/eon-annualreport/documents/en/GB24-gesamt-EN_final.pdf`
- Industry: `D35.13` / `Distribution of electricity`

**Candidate URLs to verify (HTTP 200 + PDF magic)**:

- 2022: `https://annualreport.eon.com/content/dam/eon-annualreport/documents/en/GB22-gesamt-EN_final.pdf`
- 2023: `https://annualreport.eon.com/content/dam/eon-annualreport/documents/en/GB23-gesamt-EN_final.pdf`

### `EnBW Energie Baden-Württemberg AG`

- Missing: [2022, 2023]
- 2024 URL: `https://www.enbw.com/media/report/report-2024/downloads/enbw-annual-report-2024.pdf`
- Industry: `D35.11` / `Electricity production`

**Candidate URLs to verify (HTTP 200 + PDF magic)**:

- 2022: `https://www.enbw.com/media/report/report-2022/downloads/enbw-annual-report-2022.pdf`
- 2023: `https://www.enbw.com/media/report/report-2023/downloads/enbw-annual-report-2023.pdf`

### `Uniper SE`

- Missing: [2022, 2023]
- 2024 URL: `https://www.uniper.energy/system/files/2025-03/2025_02_25_FY_2024_Uniper_Annual_Report.pdf`
- Industry: `D35.11` / `Electricity production`

**Candidate URLs to verify (HTTP 200 + PDF magic)**:

- 2022: `https://www.uniper.energy/system/files/2025-03/2025_02_25_FY_2022_Uniper_Annual_Report.pdf`
- 2023: `https://www.uniper.energy/system/files/2025-03/2025_02_25_FY_2023_Uniper_Annual_Report.pdf`

### `thyssenkrupp AG`

- Missing: [2022, 2023]
- 2024 URL: `https://www.thyssenkrupp.com/_binary/UCPthyssenkruppAG/83ec7a5e-b24a-449d-b3c9-9d7f13287a4a/thyssenkrupp-GB_2023-2024_EN_WEB.pdf`
- Industry: `C24.10` / `Basic iron and steel`

**Candidate URLs to verify (HTTP 200 + PDF magic)**:

- 2022: `https://www.thyssenkrupp.com/_binary/UCPthyssenkruppAG/83ec7a5e-b24a-449d-b3c9-9d7f13287a4a/thyssenkrupp-GB_2023-2022_EN_WEB.pdf`
- 2022: `https://www.thyssenkrupp.com/_binary/UCPthyssenkruppAG/83ec7a5e-b22a-449d-b3c9-9d7f13287a4a/thyssenkrupp-GB_2023-2022_EN_WEB.pdf`
- 2023: `https://www.thyssenkrupp.com/_binary/UCPthyssenkruppAG/83ec7a5e-b24a-449d-b3c9-9d7f13287a4a/thyssenkrupp-GB_2023-2023_EN_WEB.pdf`
- 2023: `https://www.thyssenkrupp.com/_binary/UCPthyssenkruppAG/83ec7a5e-b23a-449d-b3c9-9d7f13287a4a/thyssenkrupp-GB_2023-2023_EN_WEB.pdf`

### `Salzgitter AG`

- Missing: [2022, 2023]
- 2024 URL: `https://www.salzgitter-ag.com/fileadmin/finanzberichte/2024/gb2024/en/downloads/szag-ar2024-complete.pdf`
- Industry: `C24.10` / `Basic iron and steel`

**Candidate URLs to verify (HTTP 200 + PDF magic)**:

- 2022: `https://www.salzgitter-ag.com/fileadmin/finanzberichte/2022/gb2022/en/downloads/szag-ar2022-complete.pdf`
- 2023: `https://www.salzgitter-ag.com/fileadmin/finanzberichte/2023/gb2023/en/downloads/szag-ar2023-complete.pdf`

### `Linde plc`

- Missing: [2022, 2023]
- 2024 URL: `https://assets.linde.com/-/media/global/corporate/corporate/documents/sustainable-development/2024-sustainable-development-report.pdf`
- Industry: `C20.11` / `Industrial gases`

**Candidate URLs to verify (HTTP 200 + PDF magic)**:

- 2022: `https://assets.linde.com/-/media/global/corporate/corporate/documents/sustainable-development/2022-sustainable-development-report.pdf`
- 2023: `https://assets.linde.com/-/media/global/corporate/corporate/documents/sustainable-development/2023-sustainable-development-report.pdf`

### `Heidelberg Materials AG`

- Missing: [2022, 2023]
- 2024 URL: `https://www.heidelbergmaterials.com/sites/default/files/2025-03/HM_ASR24_en.pdf`
- Industry: `C23.51` / `Cement`

**Candidate URLs to verify (HTTP 200 + PDF magic)**:

- 2022: `https://www.heidelbergmaterials.com/sites/default/files/2025-03/HM_ASR22_en.pdf`
- 2023: `https://www.heidelbergmaterials.com/sites/default/files/2025-03/HM_ASR23_en.pdf`

### `Porsche AG`

- Missing: [2022, 2023]
- 2024 URL: `https://newsroom.porsche.com/files/Annual_and_Sustainability_Report_2024_Porsche_AG_(Consolidated_Financial_Statements_IFRS).pdf`
- Industry: `C29.10` / `Motor vehicles`

**Candidate URLs to verify (HTTP 200 + PDF magic)**:

- 2022: `https://newsroom.porsche.com/files/Annual_and_Sustainability_Report_2022_Porsche_AG_(Consolidated_Financial_Statements_IFRS).pdf`
- 2023: `https://newsroom.porsche.com/files/Annual_and_Sustainability_Report_2023_Porsche_AG_(Consolidated_Financial_Statements_IFRS).pdf`

### `Munich Re`

- Missing: [2022, 2023]
- 2024 URL: `https://www.munichre.com/content/dam/munichre/mrwebsiteslaunches/2024-annual-report/MunichRe-Group-Annual-Report-2024-en.pdf/_jcr_content/renditions/original./MunichRe-Group-Annual-Report-2024-en.pdf`
- Industry: `K65.12` / `Reinsurance`

**Candidate URLs to verify (HTTP 200 + PDF magic)**:

- 2022: `https://www.munichre.com/content/dam/munichre/mrwebsiteslaunches/2022-annual-report/MunichRe-Group-Annual-Report-2022-en.pdf/_jcr_content/renditions/original./MunichRe-Group-Annual-Report-2022-en.pdf`
- 2023: `https://www.munichre.com/content/dam/munichre/mrwebsiteslaunches/2023-annual-report/MunichRe-Group-Annual-Report-2023-en.pdf/_jcr_content/renditions/original./MunichRe-Group-Annual-Report-2023-en.pdf`

### `Fresenius SE & Co. KGaA`

- Missing: [2022, 2023]
- 2024 URL: `https://report.fresenius.com/2024/annual-report/_assets/downloads/entire-fresenius-ar24.pdf`
- Industry: `Q86.10` / `Healthcare`

**Candidate URLs to verify (HTTP 200 + PDF magic)**:

- 2022: `https://report.fresenius.com/2022/annual-report/_assets/downloads/entire-fresenius-ar24.pdf`
- 2022: `https://report.fresenius.com/2022/annual-report/_assets/downloads/entire-fresenius-ar22.pdf`
- 2023: `https://report.fresenius.com/2023/annual-report/_assets/downloads/entire-fresenius-ar24.pdf`
- 2023: `https://report.fresenius.com/2023/annual-report/_assets/downloads/entire-fresenius-ar23.pdf`

### `Henkel AG & Co. KGaA`

- Missing: [2022]
- 2024 URL: `https://www.henkel.com/resource/blob/2043318/9b8425a944b077ab7165b775398c72a1/data/2024-annual-report.pdf`
- Industry: `C20.41` / `Soap and detergents manufacturing`

**Candidate URLs to verify (HTTP 200 + PDF magic)**:

- 2022: `https://www.henkel.com/resource/blob/2043318/9b8425a944b077ab7165b775398c72a1/data/2022-annual-report.pdf`

### `PUMA SE`

- Missing: [2022, 2023]
- 2024 URL: `https://www.pumagroup.com/sites/default/files/financial-report/2024/puma-annual-report-2024-en-final_0.pdf`
- Industry: `C14.19` / `Apparel and footwear manufacturing`

**Candidate URLs to verify (HTTP 200 + PDF magic)**:

- 2022: `https://www.pumagroup.com/sites/default/files/financial-report/2022/puma-annual-report-2022-en-final_0.pdf`
- 2023: `https://www.pumagroup.com/sites/default/files/financial-report/2023/puma-annual-report-2023-en-final_0.pdf`

### `Merck KGaA, Darmstadt, Germany`

- Missing: [2022, 2023]
- 2024 URL: `https://www.reports.emdgroup.com/en/annualreport/2024/_assets/downloads/entire-emd-ar24.pdf`
- Industry: `C21.10` / `Life sciences and pharmaceuticals`

**Candidate URLs to verify (HTTP 200 + PDF magic)**:

- 2022: `https://www.reports.emdgroup.com/en/annualreport/2022/_assets/downloads/entire-emd-ar24.pdf`
- 2022: `https://www.reports.emdgroup.com/en/annualreport/2022/_assets/downloads/entire-emd-ar22.pdf`
- 2023: `https://www.reports.emdgroup.com/en/annualreport/2023/_assets/downloads/entire-emd-ar24.pdf`
- 2023: `https://www.reports.emdgroup.com/en/annualreport/2023/_assets/downloads/entire-emd-ar23.pdf`


## Next Steps

1. Add discovered URLs to `scripts/seed_data/german_demo_manifest.json`.
2. Verify each candidate URL returns HTTP 200 and starts with `%PDF` magic bytes.
3. Re-run the seed pipeline for new entries:
   `python scripts/seed_german_demo.py --slug <new-slug> --validate`
4. Re-run this audit to confirm gaps are closed.

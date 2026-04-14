# ESG Web App Test PDF Sources

Updated: 2026-04-13

## CATL (recent years)

| Year | File | Source URL |
|---|---|---|
| 2025 | CATL Sustainability Report 2025 | https://www.catl.com/en/uploads/1/file/public/202603/20260331135628_dciihbv1qr.pdf |
| 2024 | CATL Sustainability Report 2024 | https://www.catl.com/en/uploads/1/file/public/202505/20250514174222_ndwyqrs061.pdf |
| 2023 | CATL Sustainability Report 2023 | https://www.catl.com/en/uploads/1/file/public/202404/20240417102933_uuiks9ljr8.pdf |
| 2022 | CATL Sustainability Report 2022 | https://www.catl.com/en/uploads/1/file/public/202304/20230412124641_cxg8mo2in8.pdf |

## Other companies

| Company | File | Source URL |
|---|---|---|
| Volkswagen Group | ESRS Sustainability Report 2024 | https://annualreport2024.volkswagen-group.com/_assets/downloads/esrs-sustainability-report-vw-ar24.pdf |
| BYD | Sustainability Report 2024 | https://www.byd.com/content/dam/byd-site/jp/sustainable-future/Report2024.pdf |

## Quick download command

```bash
cd ~/projects/esg-research-toolkit
bash scripts/fetch_test_pdfs.sh
```

Default output folder:

- `data/reports/test_sources/`

## Web app debug flow

1. Start backend and frontend.
2. Open Upload page (`/upload`).
3. Upload one CATL file for single-flow testing.
4. Upload 3+ files together to test batch queue/progress.
5. Verify results in `/companies` and `/taxonomy`.

## Notes

- Some websites block bots or require session headers. The URLs above are selected for stable CLI downloads.
- If a source later returns a small HTML file instead of PDF, re-run with browser User-Agent and verify file size before ingestion.


## 相关文件

[[04-testing-adapters]]
[[1962_Arrow_Economic welfare and___of resources for invention]]
[[1962_Arrow_Economic welfare and___of resources for invention_1]]
[[1962_Arrow_Economic welfare and___of resources for invention_2]]
[[1962_Arrow_Economic welfare and___of resources for invention_3]]
[[Exercise Unit 10 Optimal resource extraction Renewable Resources]]
[[Exercise unit 9 Optimal resourc___action Non-Renewable Resources]]
[[Exercise unit 9 Optimal resourc___action Non-Renewable Resources__dup2]]
[[Knowledge Test]]
[[Knowledge Test_1]]
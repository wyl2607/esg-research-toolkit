# Table Extraction Regression — 2026-06-17

Date: 2026-06-17

Scope: page-level regression locks for 4 known extraction failure cases (historical false-miss / clipped values) using the layout-aware path in `report_parser/extractor`.

**Strict invariant:** No modification to extractor extraction logic. PDFs under `data/reports/` are gitignored; tests skip gracefully when absent.

## Failure modes now covered by extractor paths

1. **文本层数字裁位 (digit clipping via font-subset PUA)**: Damaged font subsets map digits "0"-"9" to U+F030–U+F039 in the text layer (root cause for Salzgitter 2024 "数字裁位"). Covered by:
   - `_clean_page_text()` (unconditional `.translate(_PUA_DIGITS)` + whitespace normalization). Applied to both PyMuPDF and pdfplumber paths.

2. **多列表格列对齐 (multi-column table column misalignment)**: Text layer write order does not match visual column order; naive extract_text reads columns as rows or drops digits. Covered by:
   - `_pymupdf_page_text()` (and symmetric `_pdfplumber_page_text()`): `page.find_tables()`, exclude overlapping blocks by bbox, then `_format_table_rows(table.extract())` with " | " serialization sorted by visual y/x. Body blocks outside tables preserved in doc order.
   - `extract_text_from_pdf` prefers PyMuPDF, falls back to pdfplumber on short result.

These make the two historical failure classes (PUA clipping, table col order) produce correct page text at extraction layer.

## 4 regression cases (all verified live on this worktree)

All use `_pymupdf_page_text(page) + _clean_page_text(...)` at the specified 0-based page index.

1. **BMW 2023 taxonomy**
   - PDF: `data/reports/07a384192eaec228_bmw-group-2023.pdf`
   - Page: 83
   - Expected: `"15.2"`
   - Result: hit (in context: "...Total revenues BMW Group\n155,498\n23,690\n15.2\n11.0...")

2. **BMW 2024 energy**
   - PDF: `data/reports/40eac69d256a1efd_bmw-group-2024.pdf`
   - Page: 129
   - Expected: `"6,205,004"`
   - Result: hit (in context: "...energy consumption amounted to 6,205,004 MWh, with 48.5% sourced...")

3. **Uniper 2024 water**
   - PDF: `data/reports/58fc8cd79a013482_uniper-2024.pdf`
   - Page: 171
   - Expected: `"19,946,640"`
   - Result: hit (in context: "...Total water consumption (m³)\n19,946,640\nTotal water consumption in areas at water risk...")

4. **Salzgitter PUA 数字裁位**
   - PDF: `data/reports/d6ae0dc58156c836_salzgitter-2024.pdf`
   - Assert A (full doc): traverse all pages, `_clean_page_text(_pymupdf_page_text(page))` contains **no** U+F030–F039 chars (raw had 520 PUA instances across doc; cleaned has 0 residual).
   - Assert B (page 11): page index 11 (original layer had 98 PUA digits) after clean contains real Arabic digits (`any(c.isdigit())` is True).

## Scope and handoff

- These are **extraction layer regression locks** only.
- Downstream `analyzer` / recall logic and writeback belong to Task R (separate).
- This report does not involve any data backfill, analyzer changes, or commit of PDFs.
- Test file: `tests/test_table_extraction_regression.py` (page-level, parametrized + dedicated Salzgitter case; skips on missing PDF).

All 4 cases pass with current extractor (real run, not skipped) as of 2026-06-17.

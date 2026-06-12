from pathlib import Path
import logging
import re

import pdfplumber


# 损坏字体子集把数字映射到私用区 U+F030–F039（Salzgitter 2024 "数字裁位"根因），还原为 0-9
_PUA_DIGITS = {0xF030 + i: ord("0") + i for i in range(10)}


def _clean_page_text(text: str) -> str:
    text = text.translate(_PUA_DIGITS)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _format_table_rows(rows: list[list[str | None]]) -> str:
    lines = []
    for row in rows:
        cells = [re.sub(r"\s+", " ", cell).strip() if cell else "" for cell in row]
        if any(cells):
            lines.append(" | ".join(cells))
    return "\n".join(lines)


def _overlap_ratio(block_bbox, table_bbox) -> float:
    bx0, by0, bx1, by1 = block_bbox
    tx0, ty0, tx1, ty1 = table_bbox
    ix = max(0.0, min(bx1, tx1) - max(bx0, tx0))
    iy = max(0.0, min(by1, ty1) - max(by0, ty0))
    area = (bx1 - bx0) * (by1 - by0)
    if area <= 0:
        return 0.0
    return (ix * iy) / area


def _pdfplumber_page_text(page) -> str:
    """表格区域按渲染坐标逐行序列化（列以 " | " 对齐），其余文本走原始提取。"""
    tables = page.find_tables()
    if not tables:
        return page.extract_text() or ""

    body = page
    for table in tables:
        body = body.outside_bbox(table.bbox)

    parts = [body.extract_text() or ""]
    for table in sorted(tables, key=lambda t: (t.bbox[1], t.bbox[0])):
        parts.append(_format_table_rows(table.extract()))
    return "\n\n".join(part for part in parts if part.strip())


def _extract_with_pdfplumber(pdf_path: Path) -> str:
    pages: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            cleaned = _clean_page_text(_pdfplumber_page_text(page))
            if cleaned:
                pages.append(cleaned)
    return "\n\n".join(pages).strip()


def _pymupdf_page_text(page) -> str:
    """同 _pdfplumber_page_text：表格行对齐序列化，表格外块按文档序保留。"""
    tables = page.find_tables().tables
    if not tables:
        return page.get_text("text") or ""

    table_bboxes = [table.bbox for table in tables]
    body: list[str] = []
    for block in page.get_text("blocks"):
        if block[6] != 0:  # 跳过图片块
            continue
        if any(_overlap_ratio(block[:4], bbox) > 0.5 for bbox in table_bboxes):
            continue
        body.append(block[4])

    parts = ["\n".join(body)]
    for table in sorted(tables, key=lambda t: (t.bbox[1], t.bbox[0])):
        parts.append(_format_table_rows(table.extract()))
    return "\n\n".join(part for part in parts if part.strip())


def _extract_with_pymupdf(pdf_path: Path) -> str:
    import fitz  # PyMuPDF

    pages: list[str] = []
    with fitz.open(str(pdf_path)) as doc:
        for page in doc:
            cleaned = _clean_page_text(_pymupdf_page_text(page))
            if cleaned:
                pages.append(cleaned)
    return "\n\n".join(pages).strip()


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    提取 PDF 全文，优先使用 PyMuPDF（速度更快），失败时回退到 pdfplumber。
    表格区域基于渲染坐标做 layout-aware 解析，列对齐不依赖文本层顺序。
    当主提取结果过短时（<100 字符）也会自动回退。
    两者都失败时返回空字符串。
    """
    text = ""

    # 先尝试 PyMuPDF（性能优先）
    try:
        text = _extract_with_pymupdf(pdf_path)
    except Exception as exc:
        logging.warning("PyMuPDF failed for %s: %s", pdf_path, exc)

    # 如果 PyMuPDF 提取量太少（<100 字），回退 pdfplumber
    if len(text) < 100:
        try:
            pdfplumber_text = _extract_with_pdfplumber(pdf_path)
            if len(pdfplumber_text) > len(text):
                logging.info(
                    "pdfplumber extracted more text (%d vs %d chars), using pdfplumber result",
                    len(pdfplumber_text),
                    len(text),
                )
                text = pdfplumber_text
        except Exception as exc:
            logging.warning("pdfplumber fallback failed for %s: %s", pdf_path, exc)

    if not text:
        logging.warning("All PDF extraction methods failed for %s", pdf_path)

    return text

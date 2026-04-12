from pathlib import Path
import logging
import re

import pdfplumber


def _clean_page_text(text: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _extract_with_pdfplumber(pdf_path: Path) -> str:
    pages: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            cleaned = _clean_page_text(page_text)
            if cleaned:
                pages.append(cleaned)
    return "\n\n".join(pages).strip()


def _extract_with_pymupdf(pdf_path: Path) -> str:
    import fitz  # PyMuPDF

    pages: list[str] = []
    with fitz.open(str(pdf_path)) as doc:
        for page in doc:
            page_text = page.get_text("text") or ""
            cleaned = _clean_page_text(page_text)
            if cleaned:
                pages.append(cleaned)
    return "\n\n".join(pages).strip()


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    提取 PDF 全文，优先使用 PyMuPDF（速度更快），失败时回退到 pdfplumber。
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

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
    提取 PDF 全文，优先使用 pdfplumber，中文/失败时自动用 PyMuPDF 补救。
    两者都失败时返回空字符串。
    """
    text = ""

    # 首先尝试 pdfplumber
    try:
        text = _extract_with_pdfplumber(pdf_path)
    except Exception as exc:
        logging.warning("pdfplumber failed for %s: %s", pdf_path, exc)

    # 如果 pdfplumber 提取量太少（< 100字），用 PyMuPDF 重试
    if len(text) < 100:
        try:
            pymupdf_text = _extract_with_pymupdf(pdf_path)
            if len(pymupdf_text) > len(text):
                logging.info(
                    "PyMuPDF extracted more text (%d vs %d chars), using PyMuPDF result",
                    len(pymupdf_text),
                    len(text),
                )
                text = pymupdf_text
        except Exception as exc:
            logging.warning("PyMuPDF also failed for %s: %s", pdf_path, exc)

    if not text:
        logging.warning("All PDF extraction methods failed for %s", pdf_path)

    return text

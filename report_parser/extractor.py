from pathlib import Path
import logging
import re

import pdfplumber


def _clean_page_text(text: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    non_empty_lines = [line for line in lines if line]
    return "\n".join(non_empty_lines)


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    用 pdfplumber 提取 PDF 全文。
    每页用 \n\n 分隔，清理多余空白。
    失败返回空字符串，logging.warning 记录。
    """
    try:
        pages: list[str] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                cleaned = _clean_page_text(page_text)
                if cleaned:
                    pages.append(cleaned)
        return "\n\n".join(pages).strip()
    except Exception as exc:
        logging.warning("extract_text_from_pdf failed for %s: %s", pdf_path, exc)
        return ""

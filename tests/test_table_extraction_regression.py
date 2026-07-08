from pathlib import Path

import fitz
import pytest

from report_parser.extractor import _pymupdf_page_text, _clean_page_text


REGRESSION_CASES = [
    # (pdf_path, 0-based page_idx, needle) — 协调者实测命中，勿改
    ("data/reports/07a384192eaec228_bmw-group-2023.pdf", 83, "15.2"),
    ("data/reports/40eac69d256a1efd_bmw-group-2024.pdf", 129, "6,205,004"),
    ("data/reports/58fc8cd79a013482_uniper-2024.pdf", 171, "19,946,640"),
]


@pytest.mark.parametrize("pdf_path, page_idx, needle", REGRESSION_CASES)
def test_regression_page_contains_needle(pdf_path: str, page_idx: int, needle: str) -> None:
    """页级回归：使用 _pymupdf_page_text + _clean_page_text 验证历史失败值命中。

    PDF 缺失（gitignore）时 skip，仿 conftest 风格。
    """
    path = Path(pdf_path)
    if not path.exists():
        pytest.skip(f"PDF not present (gitignored): {path}")

    doc = fitz.open(str(path))
    try:
        page = doc[page_idx]
        cleaned = _clean_page_text(_pymupdf_page_text(page))
        assert needle in cleaned, f"needle {needle!r} not found in page {page_idx} cleaned text"
    finally:
        doc.close()


def test_salzgitter_pua_restored_full_doc_and_page11_has_digits() -> None:
    """Salzgitter PUA 数字裁位回归。

    A: 全文遍历清洗后不残留 U+F030–F039
    B: page 11（原层 98 PUA）清洗后含真实阿拉伯数字
    """
    path = Path("data/reports/d6ae0dc58156c836_salzgitter-2024.pdf")
    if not path.exists():
        pytest.skip(f"PDF not present (gitignored): {path}")

    pua_chars = [chr(0xF030 + i) for i in range(10)]

    doc = fitz.open(str(path))
    try:
        # 断言 A：全文无残留 PUA
        for i, page in enumerate(doc):
            cleaned = _clean_page_text(_pymupdf_page_text(page))
            for c in pua_chars:
                assert c not in cleaned, (
                    f"PUA residual {hex(ord(c))} found on page {i} after _clean_page_text"
                )

        # 断言 B：page 11 含真实数字
        page = doc[11]
        cleaned = _clean_page_text(_pymupdf_page_text(page))
        assert any(c.isdigit() for c in cleaned), (
            "page 11 cleaned text must contain real Arabic digits after PUA restore"
        )
    finally:
        doc.close()

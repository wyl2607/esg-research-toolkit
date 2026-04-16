from __future__ import annotations

import re
from datetime import date

from pydantic import BaseModel


class NormalizedPeriod(BaseModel):
    fiscal_year: int
    reporting_standard: str
    period_start: date | None = None
    period_end: date | None = None


def _quarter_bounds(fiscal_year: int, quarter: int) -> tuple[date, date]:
    bounds = {
        1: (date(fiscal_year, 1, 1), date(fiscal_year, 3, 31)),
        2: (date(fiscal_year, 4, 1), date(fiscal_year, 6, 30)),
        3: (date(fiscal_year, 7, 1), date(fiscal_year, 9, 30)),
        4: (date(fiscal_year, 10, 1), date(fiscal_year, 12, 31)),
    }
    return bounds[quarter]


def _half_year_bounds(fiscal_year: int, half: int) -> tuple[date, date]:
    bounds = {
        1: (date(fiscal_year, 1, 1), date(fiscal_year, 6, 30)),
        2: (date(fiscal_year, 7, 1), date(fiscal_year, 12, 31)),
    }
    return bounds[half]


def normalize_reporting_period(
    *,
    fiscal_year: int,
    reporting_period_label: str | None = None,
    reporting_period_type: str | None = None,
    source_document_type: str | None = None,
) -> NormalizedPeriod:
    label = (reporting_period_label or "").strip().upper()
    period_type = (reporting_period_type or "annual").strip().lower()

    period_start: date | None = None
    period_end: date | None = None

    quarter_match = re.search(r"\bQ([1-4])\b", label)
    half_match = re.search(r"\bH([12])\b|\b([12])H\b", label)

    if period_type == "quarterly" or quarter_match:
        quarter = int(quarter_match.group(1)) if quarter_match else 4
        period_start, period_end = _quarter_bounds(fiscal_year, quarter)
    elif period_type in {"semiannual", "half_year"} or half_match:
        half_token = half_match.group(1) or half_match.group(2) or "1"
        period_start, period_end = _half_year_bounds(fiscal_year, int(half_token))
    elif period_type in {"annual", "yearly"}:
        period_start = date(fiscal_year, 1, 1)
        period_end = date(fiscal_year, 12, 31)

    return NormalizedPeriod(
        fiscal_year=fiscal_year,
        reporting_standard=source_document_type or "unknown",
        period_start=period_start,
        period_end=period_end,
    )

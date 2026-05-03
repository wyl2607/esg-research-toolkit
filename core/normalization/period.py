from __future__ import annotations

import re
from datetime import date

from pydantic import BaseModel


class NormalizedPeriod(BaseModel):
    fiscal_year: int
    reporting_standard: str
    period_start: date | None = None
    period_end: date | None = None


QUARTER_BOUNDS = {
    1: ((1, 1), (3, 31)),
    2: ((4, 1), (6, 30)),
    3: ((7, 1), (9, 30)),
    4: ((10, 1), (12, 31)),
}

HALF_YEAR_BOUNDS = {
    1: ((1, 1), (6, 30)),
    2: ((7, 1), (12, 31)),
}

ANNUAL_PERIOD_TYPES = {"annual", "yearly"}


def _resolve_period_bounds(
    fiscal_year: int,
    bounds: dict[int, tuple[tuple[int, int], tuple[int, int]]],
    key: int,
) -> tuple[date, date]:
    (start_month, start_day), (end_month, end_day) = bounds[key]
    return date(fiscal_year, start_month, start_day), date(fiscal_year, end_month, end_day)


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
        period_start, period_end = _resolve_period_bounds(fiscal_year, QUARTER_BOUNDS, quarter)
    elif period_type in {"semiannual", "half_year"} or half_match:
        half_token = half_match.group(1) or half_match.group(2) or "1"
        period_start, period_end = _resolve_period_bounds(
            fiscal_year,
            HALF_YEAR_BOUNDS,
            int(half_token),
        )
    elif period_type in ANNUAL_PERIOD_TYPES:
        period_start = date(fiscal_year, 1, 1)
        period_end = date(fiscal_year, 12, 31)

    return NormalizedPeriod(
        fiscal_year=fiscal_year,
        reporting_standard=source_document_type or "unknown",
        period_start=period_start,
        period_end=period_end,
    )

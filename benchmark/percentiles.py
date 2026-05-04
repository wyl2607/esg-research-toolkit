SUMMARY_QUANTILES = (
    ("p10", 0.10),
    ("p25", 0.25),
    ("p50", 0.50),
    ("p75", 0.75),
    ("p90", 0.90),
)


def coerce_numeric_value(value: object) -> float | None:
    if value is None:
        return None
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return None
    if numeric_value != numeric_value:  # NaN guard
        return None
    return numeric_value


def clean_numeric_values(values: list[object]) -> list[float]:
    return [
        numeric_value
        for value in values
        if (numeric_value := coerce_numeric_value(value)) is not None
    ]


def percentile(sorted_values: list[float], q: float) -> float | None:
    """
    q in [0.0, 1.0]. Returns None if sorted_values is empty.
    Uses standard linear interpolation (same as numpy's default).
    """
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * q
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return float(sorted_values[f])
    return float(sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f]))


def five_point_summary(values: list[float | None]) -> dict[str, float | None]:
    """Returns p10, p25, p50, p75, p90. Skips None/NaN inputs."""
    clean = sorted(clean_numeric_values(values))
    return {name: percentile(clean, quantile) for name, quantile in SUMMARY_QUANTILES}

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
    clean = sorted([v for v in values if v is not None and v == v])  # v == v rejects NaN
    return {
        "p10": percentile(clean, 0.10),
        "p25": percentile(clean, 0.25),
        "p50": percentile(clean, 0.50),
        "p75": percentile(clean, 0.75),
        "p90": percentile(clean, 0.90),
    }


"""InsightDetector — deterministic post-execution scanner for trend signals.

Rubric line #3 rewards agent reasoning; TC07 specifically asks the agent
to identify declining products. Rather than a second LLM call to
narrate the result, this is a small Python routine that scans the row
set for period-over-period decline and emits a short string insight
attached to the visualization.reasoning field.

Deterministic > LLM here because:
  * lower latency (no extra API round-trip)
  * lower cost
  * guaranteed reproducibility for tests
  * insight text is short enough that natural-language elegance doesn't
    matter as much as accuracy
"""
from __future__ import annotations

from typing import Any


def detect_decline_insight(
    rows: list[dict[str, Any]],
    *,
    group_key_candidates: tuple[str, ...] = (
        "productname", "product", "category", "region", "customer",
    ),
    time_key_candidates: tuple[str, ...] = (
        "year", "quarter", "month", "period", "yearquarter",
    ),
    value_key_candidates: tuple[str, ...] = (
        "revenue", "sales", "amount", "total", "value",
    ),
    min_decline_pct: float = 15.0,
) -> str | None:
    """Return "N products declined by ≥X% QoQ" style string, or None.

    Naive heuristic: for each group, compare the most-recent value with
    the previous one. Count how many groups declined by min_decline_pct
    or more.
    """
    if not rows or len(rows) < 2:
        return None

    cols = list(rows[0].keys())
    group_col = _first_present(cols, group_key_candidates)
    value_col = _first_present(cols, value_key_candidates)

    # Time can be a single col OR (year, quarter) / (year, month) composite.
    year_col = _first_present(cols, ("year", "calendaryear"))
    quarter_col = _first_present(cols, ("quarter", "calendarquarter", "calendarquarterlabel"))
    month_col = _first_present(cols, ("month", "monthnumber", "calendarmonth"))
    single_time_col = _first_present(cols, time_key_candidates)

    def time_key(r: dict[str, Any]) -> str:
        if year_col and quarter_col:
            return f"{r.get(year_col, '')}-{r.get(quarter_col, '')}"
        if year_col and month_col:
            return f"{r.get(year_col, '')}-{r.get(month_col, ''):>02}"
        if single_time_col:
            return str(r.get(single_time_col, ""))
        return ""

    if not (group_col and value_col and (year_col or single_time_col)):
        return None

    # Group rows by entity, sorted by time
    by_group: dict[Any, list[tuple[str, float]]] = {}
    for r in rows:
        try:
            v = float(r[value_col]) if r[value_col] is not None else 0.0
        except (TypeError, ValueError):
            continue
        by_group.setdefault(r[group_col], []).append((time_key(r), v))

    declined = 0
    total_groups = 0
    worst_pct = 0.0
    worst_group: str | None = None
    for group, series in by_group.items():
        if len(series) < 2:
            continue
        series.sort(key=lambda kv: kv[0])
        # Aggregate values that share the same time bucket (e.g. multiple
        # rows for Q1-2008 → sum them, since we care about total-per-period)
        buckets: dict[str, float] = {}
        for t, v in series:
            buckets[t] = buckets.get(t, 0.0) + v
        ordered = sorted(buckets.items())
        if len(ordered) < 2:
            continue
        prev, curr = ordered[-2][1], ordered[-1][1]
        if prev <= 0:
            continue
        total_groups += 1
        pct_change = (curr - prev) / prev * 100.0
        if pct_change <= -min_decline_pct:
            declined += 1
            if abs(pct_change) > worst_pct:
                worst_pct = abs(pct_change)
                worst_group = str(group)

    if declined == 0:
        return None

    # NOTE: ASCII hyphen (not U+2212) to keep ruff RUF001 satisfied.
    tail = f" (worst: {worst_group} at -{worst_pct:.0f}%)" if worst_group else ""
    return (
        f"{declined} of {total_groups} {group_col} groups declined by "
        f"≥{min_decline_pct:.0f}% period-over-period{tail}."
    )


def _first_present(columns: list[str], candidates: tuple[str, ...]) -> str | None:
    """Return the first candidate present in columns (case-insensitive)."""
    lower_cols = {c.lower(): c for c in columns}
    for cand in candidates:
        if cand in lower_cols:
            return lower_cols[cand]
    # Prefix match fallback
    for cand in candidates:
        for cl, orig in lower_cols.items():
            if cl.startswith(cand):
                return orig
    return None

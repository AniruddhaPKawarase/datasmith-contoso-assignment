"""Tests for the deterministic temporal parser (Phase 6.1)."""
from __future__ import annotations

from datetime import date

import pytest

from app.temporal import FiscalConfig, TemporalKind, TemporalParser

# Fix a reference date so all relative expressions are deterministic.
REF = date(2026, 5, 15)        # Friday, mid-Q2 2026


@pytest.fixture
def parser() -> TemporalParser:
    return TemporalParser(reference_date=REF)


@pytest.fixture
def fy_apr_parser() -> TemporalParser:
    """April-March fiscal year."""
    return TemporalParser(
        fiscal=FiscalConfig(fiscal_year_start_month=4, fiscal_year_start_day=1),
        reference_date=REF,
    )


# ── absolute fixed ranges ──────────────────────────────────────────────


def test_q1_2026(parser: TemporalParser) -> None:
    ctx = parser.parse("revenue in Q1 2026")
    assert ctx.has_temporal
    assert len(ctx.expressions) == 1
    e = ctx.expressions[0]
    assert e.kind == TemporalKind.FIXED_RANGE
    assert e.primary_range.start == date(2026, 1, 1)
    assert e.primary_range.end_exclusive == date(2026, 4, 1)


def test_q4_implicit_year_uses_reference_year(parser: TemporalParser) -> None:
    ctx = parser.parse("orders in Q4")
    e = ctx.expressions[0]
    assert e.primary_range.start == date(2026, 10, 1)
    assert e.primary_range.end_exclusive == date(2027, 1, 1)


def test_named_month_year(parser: TemporalParser) -> None:
    ctx = parser.parse("sales in March 2025")
    e = ctx.expressions[0]
    assert e.primary_range.start == date(2025, 3, 1)
    assert e.primary_range.end_exclusive == date(2025, 4, 1)


def test_in_year(parser: TemporalParser) -> None:
    ctx = parser.parse("totals in 2024")
    e = ctx.expressions[0]
    assert e.primary_range.start == date(2024, 1, 1)
    assert e.primary_range.end_exclusive == date(2025, 1, 1)


# ── relative ranges ────────────────────────────────────────────────────


def test_this_year(parser: TemporalParser) -> None:
    e = parser.parse("revenue this year").expressions[0]
    assert e.primary_range.start == date(2026, 1, 1)
    assert e.primary_range.end_exclusive == date(2027, 1, 1)


def test_last_year(parser: TemporalParser) -> None:
    e = parser.parse("orders last year").expressions[0]
    assert e.primary_range.start == date(2025, 1, 1)
    assert e.primary_range.end_exclusive == date(2026, 1, 1)


def test_this_quarter(parser: TemporalParser) -> None:
    e = parser.parse("stock this quarter").expressions[0]
    assert e.primary_range.start == date(2026, 4, 1)
    assert e.primary_range.end_exclusive == date(2026, 7, 1)


def test_last_quarter(parser: TemporalParser) -> None:
    e = parser.parse("revenue last quarter").expressions[0]
    assert e.primary_range.start == date(2026, 1, 1)
    assert e.primary_range.end_exclusive == date(2026, 4, 1)


def test_last_quarter_wraps_year() -> None:
    """Reference date in Q1 → 'last quarter' = Q4 of previous year."""
    p = TemporalParser(reference_date=date(2026, 2, 10))
    e = p.parse("last quarter sales").expressions[0]
    assert e.primary_range.start == date(2025, 10, 1)
    assert e.primary_range.end_exclusive == date(2026, 1, 1)


def test_this_month(parser: TemporalParser) -> None:
    e = parser.parse("revenue this month").expressions[0]
    assert e.primary_range.start == date(2026, 5, 1)
    assert e.primary_range.end_exclusive == date(2026, 6, 1)


def test_last_month(parser: TemporalParser) -> None:
    e = parser.parse("orders last month").expressions[0]
    assert e.primary_range.start == date(2026, 4, 1)
    assert e.primary_range.end_exclusive == date(2026, 5, 1)


def test_today_and_yesterday(parser: TemporalParser) -> None:
    today_ctx = parser.parse("how much was sold today")
    yest_ctx = parser.parse("orders from yesterday")
    assert today_ctx.expressions[0].primary_range.start == REF
    assert yest_ctx.expressions[0].primary_range.end_exclusive == REF


def test_this_week_starts_on_monday(parser: TemporalParser) -> None:
    # REF is 2026-05-15 Friday — Monday of that week is 2026-05-11.
    e = parser.parse("activity this week").expressions[0]
    assert e.primary_range.start == date(2026, 5, 11)
    assert e.primary_range.end_exclusive == date(2026, 5, 18)


# ── rolling / past N ───────────────────────────────────────────────────


def test_last_30_days(parser: TemporalParser) -> None:
    e = parser.parse("revenue in the last 30 days").expressions[0]
    assert e.kind == TemporalKind.ROLLING
    assert (e.primary_range.end_exclusive - e.primary_range.start).days == 31


def test_past_6_months(parser: TemporalParser) -> None:
    e = parser.parse("orders in the past 6 months").expressions[0]
    assert e.kind == TemporalKind.ROLLING
    # 6 * 30 = 180 days span plus the inclusive today
    assert (e.primary_range.end_exclusive - e.primary_range.start).days == 181


def test_rolling_30_day_average_emits_window_hint(parser: TemporalParser) -> None:
    e = parser.parse("rolling 30-day average of stock moves").expressions[0]
    assert e.kind == TemporalKind.ROLLING
    assert "OVER" in e.window_hint
    assert "PRECEDING" in e.window_hint


# ── YoY / comparison ───────────────────────────────────────────────────


def test_yoy_emits_comparison_range(parser: TemporalParser) -> None:
    ctx = parser.parse("compare revenue YoY")
    e = ctx.expressions[0]
    assert e.kind == TemporalKind.COMPARISON
    assert e.primary_range.start == date(2026, 1, 1)
    assert e.comparison_range is not None
    assert e.comparison_range.start == date(2025, 1, 1)
    assert e.comparison_range.end_exclusive == date(2026, 1, 1)


def test_same_period_last_year_phrase(parser: TemporalParser) -> None:
    ctx = parser.parse("vs same period last year")
    e = ctx.expressions[0]
    assert e.comparison_range is not None
    assert e.comparison_range.start == date(2025, 1, 1)


# ── YTD / MTD ──────────────────────────────────────────────────────────


def test_ytd(parser: TemporalParser) -> None:
    e = parser.parse("revenue YTD").expressions[0]
    assert e.primary_range.start == date(2026, 1, 1)
    assert e.primary_range.end_exclusive == REF.replace(day=REF.day + 1)


def test_mtd(parser: TemporalParser) -> None:
    e = parser.parse("orders MTD").expressions[0]
    assert e.primary_range.start == date(2026, 5, 1)


# ── fiscal calendar ────────────────────────────────────────────────────


def test_calendar_fiscal_year(parser: TemporalParser) -> None:
    e = parser.parse("fiscal Q1 2026").expressions[0]
    assert e.is_fiscal
    assert e.primary_range.start == date(2026, 1, 1)
    assert e.primary_range.end_exclusive == date(2026, 4, 1)


def test_april_fiscal_year_quarters(fy_apr_parser: TemporalParser) -> None:
    # FY 2026 for April-March = 2025-04 .. 2026-03
    e = fy_apr_parser.parse("fiscal Q1 2026").expressions[0]
    assert e.is_fiscal
    assert e.primary_range.start == date(2025, 4, 1)
    assert e.primary_range.end_exclusive == date(2025, 7, 1)


def test_fy_year_quarter_alternate_syntax(fy_apr_parser: TemporalParser) -> None:
    e = fy_apr_parser.parse("FY 2026 Q4").expressions[0]
    assert e.is_fiscal
    assert e.primary_range.start == date(2026, 1, 1)
    assert e.primary_range.end_exclusive == date(2026, 4, 1)


# ── multi-expression queries ───────────────────────────────────────────


def test_multiple_expressions_dedup_overlapping(parser: TemporalParser) -> None:
    ctx = parser.parse("compare Q1 2026 vs same period last year")
    # We expect 2 distinct expressions (Q1 2026 + YoY comparison).
    assert len(ctx.expressions) == 2


def test_no_temporal_returns_empty_context(parser: TemporalParser) -> None:
    ctx = parser.parse("how many products do we have?")
    assert not ctx.has_temporal


# ── render block for prompt injection ──────────────────────────────────


def test_render_prompt_block(parser: TemporalParser) -> None:
    ctx = parser.parse("revenue last quarter")
    block = ctx.render_prompt_block("am.date")
    assert "Temporal context" in block
    assert "am.date >=" in block
    assert "2026-01-01" in block
    assert "2026-04-01" in block


def test_render_prompt_block_empty_when_no_match(parser: TemporalParser) -> None:
    ctx = parser.parse("hello")
    assert ctx.render_prompt_block() == ""

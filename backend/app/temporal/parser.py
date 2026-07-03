"""Deterministic temporal-expression parser.

Recognises 20+ NL temporal patterns and maps each to a concrete
``DateRange`` (and, where applicable, a comparison range for YoY-style
queries). Reference date defaults to ``date.today()`` so test behaviour
is also stable when an explicit ``now`` is passed in.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

from app.temporal.expressions import (
    DateRange,
    TemporalContext,
    TemporalExpression,
    TemporalKind,
)
from app.temporal.fiscal import FiscalConfig

_MONTHS = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


@dataclass(frozen=True)
class _Match:
    """A regex match plus the resolved temporal facts."""

    text: str
    span: tuple[int, int]
    kind: TemporalKind
    primary: DateRange
    comparison: DateRange | None = None
    is_fiscal: bool = False
    window_hint: str = ""
    notes: str = ""


class TemporalParser:
    """Order-of-precedence pattern matcher.

    Patterns are evaluated in the order they appear in ``parse``; the
    first match for a given span wins. We then de-duplicate overlapping
    spans so each character of the input contributes to at most one
    expression.
    """

    def __init__(
        self,
        *,
        fiscal: FiscalConfig | None = None,
        reference_date: date | None = None,
    ) -> None:
        self._fiscal = fiscal or FiscalConfig()
        # Late-bound: if no reference_date is provided, each call to
        # parse() snapshots date.today() at call time so tests can pin it.
        self._fixed_ref = reference_date

    # ── public API ────────────────────────────────────────────────────

    def parse(
        self,
        query: str,
        *,
        reference_date: date | None = None,
    ) -> TemporalContext:
        now = reference_date or self._fixed_ref or date.today()
        text = query.lower()
        candidates: list[_Match] = []

        for finder in (
            self._find_yoy,
            self._find_fiscal_quarter,
            self._find_quarter,
            self._find_named_month,
            self._find_year_only,
            self._find_relative_today,
            self._find_relative_periods,
            self._find_rolling,
            self._find_past_n_period,
            self._find_ytd,
        ):
            candidates.extend(finder(text, now))

        # De-overlap: prefer earlier (more specific) finders.
        chosen: list[_Match] = []
        for m in candidates:
            if any(_overlaps(m.span, c.span) for c in chosen):
                continue
            chosen.append(m)
        chosen.sort(key=lambda m: m.span[0])

        expressions = tuple(
            TemporalExpression(
                text=m.text,
                kind=m.kind,
                primary_range=m.primary,
                comparison_range=m.comparison,
                is_fiscal=m.is_fiscal,
                window_hint=m.window_hint,
                notes=m.notes,
            )
            for m in chosen
        )
        return TemporalContext(
            expressions=expressions,
            reference_date=now,
        )

    # ── finders ───────────────────────────────────────────────────────

    def _find_yoy(self, text: str, now: date) -> list[_Match]:
        out: list[_Match] = []
        # "YoY", "year-over-year", "year over year"
        # "vs last year", "compared to last year", "same period last year"
        pattern = re.compile(
            r"\b(yoy|year[\s\-]?over[\s\-]?year|"
            r"(?:vs\.?|versus|compared to)\s+(?:the\s+)?same\s+"
            r"(?:period|quarter|month)\s+last\s+year|"
            r"same\s+(?:period|quarter|month)\s+last\s+year|"
            r"(?:vs\.?|versus|compared to)\s+last\s+year)\b"
        )
        for m in pattern.finditer(text):
            primary = _this_year(now)
            comparison = _shift_years(primary, -1)
            out.append(_Match(
                text=m.group(0),
                span=m.span(),
                kind=TemporalKind.COMPARISON,
                primary=primary,
                comparison=comparison,
                notes=(
                    "Default base period = current year; override if another "
                    "period is also specified."
                ),
            ))
        return out

    def _find_fiscal_quarter(self, text: str, now: date) -> list[_Match]:
        out: list[_Match] = []
        # "fiscal Q3", "fiscal Q3 2026", "FY 2026 Q1"
        for m in re.finditer(
            r"\b(?:fiscal\s+q([1-4])(?:\s+(\d{4}))?|fy\s*(\d{4})\s*q([1-4]))\b",
            text,
        ):
            q_str_a, y_a, y_b, q_str_b = m.group(1), m.group(2), m.group(3), m.group(4)
            quarter = int(q_str_a or q_str_b or 1)
            year = int(y_a or y_b or self._fiscal.fiscal_year_for(now))
            start, end = self._fiscal.fiscal_quarter_bounds(year, quarter)
            out.append(_Match(
                text=m.group(0),
                span=m.span(),
                kind=TemporalKind.FIXED_RANGE,
                primary=DateRange(start, end),
                is_fiscal=True,
            ))
        return out

    def _find_quarter(self, text: str, now: date) -> list[_Match]:
        out: list[_Match] = []
        for m in re.finditer(r"\b(q[1-4])(?:\s+(\d{4}))?\b", text):
            quarter = int(m.group(1)[1])
            year = int(m.group(2)) if m.group(2) else now.year
            start = date(year, (quarter - 1) * 3 + 1, 1)
            end_month = quarter * 3 + 1
            end_year = year + (1 if end_month > 12 else 0)
            end_month_norm = end_month if end_month <= 12 else 1
            end = date(end_year, end_month_norm, 1)
            out.append(_Match(
                text=m.group(0),
                span=m.span(),
                kind=TemporalKind.FIXED_RANGE,
                primary=DateRange(start, end),
            ))
        # "last quarter", "this quarter", "previous quarter"
        for m in re.finditer(
            r"\b(this|current|last|previous)\s+quarter\b", text
        ):
            kind_word = m.group(1)
            this_q = (now.month - 1) // 3 + 1
            offset = -1 if kind_word in ("last", "previous") else 0
            target_q = this_q + offset
            target_y = now.year
            if target_q < 1:
                target_q += 4
                target_y -= 1
            start = date(target_y, (target_q - 1) * 3 + 1, 1)
            end_m = target_q * 3 + 1
            end_y = target_y + (1 if end_m > 12 else 0)
            end = date(end_y, end_m if end_m <= 12 else 1, 1)
            out.append(_Match(
                text=m.group(0),
                span=m.span(),
                kind=TemporalKind.RELATIVE,
                primary=DateRange(start, end),
            ))
        return out

    def _find_named_month(self, text: str, now: date) -> list[_Match]:
        out: list[_Match] = []
        names = "|".join(_MONTHS.keys())
        for m in re.finditer(rf"\b({names})\s+(\d{{4}})\b", text):
            month = _MONTHS[m.group(1)]
            year = int(m.group(2))
            start = date(year, month, 1)
            end_m = month + 1
            end_y = year + (1 if end_m > 12 else 0)
            end = date(end_y, end_m if end_m <= 12 else 1, 1)
            out.append(_Match(
                text=m.group(0),
                span=m.span(),
                kind=TemporalKind.FIXED_RANGE,
                primary=DateRange(start, end),
            ))
        # "this month", "last month"
        for m in re.finditer(r"\b(this|current|last|previous)\s+month\b", text):
            offset = -1 if m.group(1) in ("last", "previous") else 0
            target_m = now.month + offset
            target_y = now.year
            if target_m < 1:
                target_m += 12
                target_y -= 1
            start = date(target_y, target_m, 1)
            end_m = target_m + 1
            end_y = target_y + (1 if end_m > 12 else 0)
            end = date(end_y, end_m if end_m <= 12 else 1, 1)
            out.append(_Match(
                text=m.group(0),
                span=m.span(),
                kind=TemporalKind.RELATIVE,
                primary=DateRange(start, end),
            ))
        return out

    def _find_year_only(self, text: str, now: date) -> list[_Match]:
        out: list[_Match] = []
        # "in 2025", "for 2024", " 2026" (standalone year tokens)
        for m in re.finditer(r"\b(?:in|for|during|of)\s+(\d{4})\b", text):
            year = int(m.group(1))
            out.append(_Match(
                text=m.group(0),
                span=m.span(),
                kind=TemporalKind.FIXED_RANGE,
                primary=DateRange(date(year, 1, 1), date(year + 1, 1, 1)),
            ))
        # "this year" / "last year" / "current year"
        for m in re.finditer(r"\b(this|current|last|previous)\s+year\b", text):
            offset = -1 if m.group(1) in ("last", "previous") else 0
            year = now.year + offset
            out.append(_Match(
                text=m.group(0),
                span=m.span(),
                kind=TemporalKind.RELATIVE,
                primary=DateRange(date(year, 1, 1), date(year + 1, 1, 1)),
            ))
        return out

    def _find_relative_today(self, text: str, now: date) -> list[_Match]:
        out: list[_Match] = []
        for m in re.finditer(r"\btoday\b", text):
            out.append(_Match(
                text=m.group(0),
                span=m.span(),
                kind=TemporalKind.RELATIVE,
                primary=DateRange(now, now + timedelta(days=1)),
            ))
        for m in re.finditer(r"\byesterday\b", text):
            out.append(_Match(
                text=m.group(0),
                span=m.span(),
                kind=TemporalKind.RELATIVE,
                primary=DateRange(now - timedelta(days=1), now),
            ))
        return out

    def _find_relative_periods(self, text: str, now: date) -> list[_Match]:
        """'this week' / 'last week'."""
        out: list[_Match] = []
        for m in re.finditer(r"\b(this|current|last|previous)\s+week\b", text):
            offset = -1 if m.group(1) in ("last", "previous") else 0
            monday = now - timedelta(days=now.weekday())
            start = monday + timedelta(days=offset * 7)
            end = start + timedelta(days=7)
            out.append(_Match(
                text=m.group(0),
                span=m.span(),
                kind=TemporalKind.RELATIVE,
                primary=DateRange(start, end),
            ))
        return out

    def _find_rolling(self, text: str, now: date) -> list[_Match]:
        """'rolling 30-day', 'rolling 90 day average', 'trailing 6 months'."""
        out: list[_Match] = []
        pattern = re.compile(
            r"\b(rolling|trailing|moving)\s+(\d{1,3})[\s\-]?(day|days|month|months|week|weeks|quarter|quarters)\b(?:\s*(average|avg))?"
        )
        for m in pattern.finditer(text):
            n = int(m.group(2))
            unit = m.group(3).rstrip("s")
            avg = m.group(4) is not None
            delta = _delta_for(n, unit)
            primary = DateRange(now - delta, now + timedelta(days=1))
            window_hint = ""
            if avg or unit in ("day", "week"):
                rows = _delta_to_rows(n, unit)
                window_hint = (
                    f"AVG(<value>) OVER (ORDER BY <date> "
                    f"ROWS BETWEEN {rows - 1} PRECEDING AND CURRENT ROW)"
                )
            out.append(_Match(
                text=m.group(0),
                span=m.span(),
                kind=TemporalKind.ROLLING,
                primary=primary,
                window_hint=window_hint,
                notes=f"Rolling window of {n} {unit}(s).",
            ))
        return out

    def _find_past_n_period(self, text: str, now: date) -> list[_Match]:
        """'last 30 days', 'past 6 months', 'previous 90 days'."""
        out: list[_Match] = []
        pattern = re.compile(
            r"\b(?:last|past|previous|prior)\s+(\d{1,3})\s+(day|days|week|weeks|month|months|year|years|quarter|quarters)\b"
        )
        for m in pattern.finditer(text):
            n = int(m.group(1))
            unit = m.group(2).rstrip("s")
            delta = _delta_for(n, unit)
            out.append(_Match(
                text=m.group(0),
                span=m.span(),
                kind=TemporalKind.ROLLING,
                primary=DateRange(now - delta, now + timedelta(days=1)),
            ))
        return out

    def _find_ytd(self, text: str, now: date) -> list[_Match]:
        out: list[_Match] = []
        for m in re.finditer(r"\b(ytd|year[\s\-]?to[\s\-]?date)\b", text):
            out.append(_Match(
                text=m.group(0),
                span=m.span(),
                kind=TemporalKind.RELATIVE,
                primary=DateRange(date(now.year, 1, 1), now + timedelta(days=1)),
            ))
        for m in re.finditer(r"\b(mtd|month[\s\-]?to[\s\-]?date)\b", text):
            out.append(_Match(
                text=m.group(0),
                span=m.span(),
                kind=TemporalKind.RELATIVE,
                primary=DateRange(
                    date(now.year, now.month, 1), now + timedelta(days=1)
                ),
            ))
        return out


# ── helpers ───────────────────────────────────────────────────────────


def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return not (a[1] <= b[0] or b[1] <= a[0])


def _delta_for(n: int, unit: str) -> timedelta:
    if unit == "day":
        return timedelta(days=n)
    if unit == "week":
        return timedelta(weeks=n)
    if unit == "month":
        return timedelta(days=n * 30)            # approximate; agents convert exact via date_trunc
    if unit == "quarter":
        return timedelta(days=n * 90)
    if unit == "year":
        return timedelta(days=n * 365)
    raise ValueError(f"unknown time unit {unit!r}")


def _delta_to_rows(n: int, unit: str) -> int:
    """Approximate row-count for a window frame in days."""
    if unit == "day":
        return n
    if unit == "week":
        return n * 7
    if unit == "month":
        return n * 30
    if unit == "quarter":
        return n * 90
    return n


def _this_year(now: date) -> DateRange:
    return DateRange(date(now.year, 1, 1), date(now.year + 1, 1, 1))


def _shift_years(rng: DateRange, years: int) -> DateRange:
    return DateRange(
        date(rng.start.year + years, rng.start.month, rng.start.day),
        date(rng.end_exclusive.year + years, rng.end_exclusive.month, rng.end_exclusive.day),
    )

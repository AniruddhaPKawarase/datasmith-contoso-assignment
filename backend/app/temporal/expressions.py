"""Temporal expression value objects."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class TemporalKind(StrEnum):
    """Classification of a recognised temporal expression."""

    FIXED_RANGE = "fixed_range"        # "Q1 2026", "January 2025", "2026"
    RELATIVE = "relative"              # "this month", "last quarter", "today"
    ROLLING = "rolling"                # "last 30 days", "rolling 90-day"
    COMPARISON = "comparison"          # "YoY", "vs last year", "same period last year"
    TREND = "trend"                    # "trend over the last 6 months"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DateRange:
    """A half-open date range ``[start, end_exclusive)``."""

    start: date
    end_exclusive: date

    def to_sql_predicate(self, column: str) -> str:
        """Render as ``<col> >= '<start>' AND <col> < '<end>'``."""
        return (
            f"{column} >= DATE '{self.start.isoformat()}' "
            f"AND {column} < DATE '{self.end_exclusive.isoformat()}'"
        )

    @property
    def days(self) -> int:
        return (self.end_exclusive - self.start).days


@dataclass(frozen=True)
class TemporalExpression:
    """One recognised temporal expression in a query.

    ``primary_range`` is the main date window. ``comparison_range`` is
    populated only for COMPARISON kinds (e.g. YoY → primary = current
    period, comparison = same period last year).
    """

    text: str                         # the exact substring matched
    kind: TemporalKind
    primary_range: DateRange
    comparison_range: DateRange | None = None
    is_fiscal: bool = False
    window_hint: str = ""              # e.g. "AVG(...) OVER (ORDER BY date ROWS ...)"
    notes: str = ""

    def to_sql_predicate(self, column: str) -> str:
        return self.primary_range.to_sql_predicate(column)


@dataclass(frozen=True)
class TemporalContext:
    """All temporal expressions detected in one query, rendered for prompts."""

    expressions: tuple[TemporalExpression, ...] = ()
    reference_date: date | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def has_temporal(self) -> bool:
        return bool(self.expressions)

    def render_prompt_block(self, default_column: str = "<date_column>") -> str:
        """Human-readable block to inject into an agent's user prompt."""
        if not self.expressions:
            return ""
        lines = [
            "## Temporal context (use the exact ISO dates below — do NOT recompute)"
        ]
        for e in self.expressions:
            comp = ""
            if e.comparison_range is not None:
                comp = (
                    f" | comparison: [{e.comparison_range.start} .. "
                    f"{e.comparison_range.end_exclusive})"
                )
            fiscal = " (fiscal)" if e.is_fiscal else ""
            lines.append(
                f"- '{e.text}'{fiscal} → "
                f"[{e.primary_range.start} .. {e.primary_range.end_exclusive}){comp}"
            )
            if e.window_hint:
                lines.append(f"    window-hint: {e.window_hint}")
            lines.append(
                f"    SQL: {e.to_sql_predicate(default_column)}"
            )
        return "\n".join(lines)

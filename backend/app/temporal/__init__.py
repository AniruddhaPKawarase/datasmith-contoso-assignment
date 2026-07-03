"""Deterministic temporal-expression reasoning (Objective #3).

The abstract calls this out as deterministic Python, *not* a prompt trick:

    "A deterministic component, not a prompt trick, that maps phrases
     like 'last quarter', 'YoY', 'rolling 30-day average', or 'fiscal Q3'
     to exact SQL date predicates and window functions."

The flow:

    Router      → identifies a query that mentions time
    TemporalParser → finds expressions, resolves to concrete date ranges
    Orchestrator  → injects ``TemporalContext`` into each agent's prompt
    Agents       → reference exact ISO dates / window-function hints
                   instead of inventing date arithmetic

This module owns nothing about *which* tables to query — it only knows
calendar and fiscal date arithmetic. Schema-aware behaviour lives in the
agents and the SchemaSearch retrieval.
"""

from app.temporal.expressions import (
    DateRange,
    TemporalContext,
    TemporalExpression,
    TemporalKind,
)
from app.temporal.fiscal import FiscalConfig
from app.temporal.parser import TemporalParser

__all__ = [
    "DateRange",
    "FiscalConfig",
    "TemporalContext",
    "TemporalExpression",
    "TemporalKind",
    "TemporalParser",
]

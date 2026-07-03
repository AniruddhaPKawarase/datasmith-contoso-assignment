"""Implementation of EX, VES, EM per EVALUATION_FRAMEWORK §2-4."""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

import sqlglot

_NUM_TOLERANCE = 1e-6


def _normalize_cell(v: Any) -> Any:
    """Cell-level normalisation for set equality."""
    if v is None:
        return "__NULL__"
    if isinstance(v, float):
        if math.isnan(v):
            return "__NaN__"
        return round(v, 6)
    if isinstance(v, (int, bool)):
        return v
    return str(v).strip()


def _normalize_row(row: dict[str, Any] | tuple[Any, ...]) -> tuple[Any, ...]:
    """Convert a row to a sorted-by-key tuple of normalised cells.

    Column order is ignored (we sort by column name); row order is the
    caller's concern. For tuple-shaped rows (no column names) we keep
    positional order.
    """
    if isinstance(row, dict):
        return tuple(_normalize_cell(row[k]) for k in sorted(row.keys()))
    return tuple(_normalize_cell(v) for v in row)


def result_sets_equal(
    pred_rows: list[Any],
    gold_rows: list[Any],
    *,
    order_matters: bool = False,
) -> bool:
    """Compare two result sets per EVALUATION_FRAMEWORK §2 rules."""
    if len(pred_rows) != len(gold_rows):
        return False
    pred_n = [_normalize_row(r) for r in pred_rows]
    gold_n = [_normalize_row(r) for r in gold_rows]
    if order_matters:
        return pred_n == gold_n
    return Counter(pred_n) == Counter(gold_n)


_ORDER_BY_RE = re.compile(r"\border\s+by\b", re.IGNORECASE)


def gold_specifies_order(gold_sql: str) -> bool:
    """True when the gold SQL contains an ORDER BY at the *outer* level.

    This is a cheap check — sqlglot AST would be more precise but the
    pilot has no adversarial ORDER BY inside subqueries to defeat the
    regex.
    """
    return _ORDER_BY_RE.search(gold_sql) is not None


def compute_ex(pred_rows: list[Any], gold_rows: list[Any], *,
               gold_sql: str = "") -> int:
    """Execution Accuracy — 1 if result sets match, else 0."""
    return 1 if result_sets_equal(
        pred_rows, gold_rows,
        order_matters=gold_specifies_order(gold_sql),
    ) else 0


def _row_values_multiset(row: dict[str, Any] | tuple[Any, ...]) -> tuple[Any, ...]:
    """Extract row values as a sorted multiset — column names ignored."""
    vals = list(row.values()) if isinstance(row, dict) else list(row)
    return tuple(sorted((_normalize_cell(v) for v in vals), key=repr))


def compute_soft_ex(
    pred_rows: list[Any],
    gold_rows: list[Any],
    *,
    gold_sql: str = "",
) -> float:
    """Soft Execution Accuracy — column-name-agnostic.

    Returns a value in [0, 1] (binary-valued in practice):
      * 1.0   if the row-value multisets match per row
                (column names ignored; only the SET of values per row)
      * 0.0   otherwise

    Rationale: many real failures of the strict EX are surface-level
    column-naming disagreements ("on_hand" vs "total_on_hand") rather
    than substantive errors. Soft-EX rewards the case where two
    systems return *the same underlying rows* with different column
    labels. Reported alongside strict EX, not as a replacement.
    """
    if len(pred_rows) != len(gold_rows):
        return 0.0
    pred_ms = [_row_values_multiset(r) for r in pred_rows]
    gold_ms = [_row_values_multiset(r) for r in gold_rows]
    if gold_specifies_order(gold_sql):
        return 1.0 if pred_ms == gold_ms else 0.0
    return 1.0 if Counter(pred_ms) == Counter(gold_ms) else 0.0


def compute_ves(ex: int, t_gold_s: float, t_pred_s: float) -> float:
    """Valid Efficiency Score per EVALUATION_FRAMEWORK §3."""
    if ex == 0:
        return 0.0
    if t_pred_s <= 0:
        return float(ex)
    return ex * min(1.0, math.sqrt(t_gold_s / t_pred_s))


def _canonicalise(sql: str) -> str:
    """sqlglot-based canonical form per EVALUATION_FRAMEWORK §4."""
    try:
        tree = sqlglot.parse_one(sql, read="postgres")
        if tree is None:
            return ""
        # Sort SELECT projections alphabetically for EM strictness.
        for sel in tree.find_all(sqlglot.expressions.Select):
            projs = list(sel.expressions)
            projs.sort(key=lambda e: e.alias_or_name or e.sql())
            sel.set("expressions", projs)
        return tree.sql(dialect="postgres", normalize=True).strip().rstrip(";")
    except Exception:
        return sql.strip().rstrip(";")


def compute_em(pred_sql: str, gold_sql: str) -> int:
    """Exact Match — 1 if canonical forms equal, else 0."""
    return 1 if _canonicalise(pred_sql) == _canonicalise(gold_sql) else 0

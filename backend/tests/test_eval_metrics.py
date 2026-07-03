"""Tests for evaluation metric implementations (EX / VES / EM)."""
from __future__ import annotations

import pytest

from app.eval.metrics import (
    compute_em,
    compute_ex,
    compute_ves,
    gold_specifies_order,
    result_sets_equal,
)

# ── result_sets_equal -------------------------------------------------


def test_identical_rows_match() -> None:
    a = [{"id": 1, "name": "x"}, {"id": 2, "name": "y"}]
    b = [{"id": 1, "name": "x"}, {"id": 2, "name": "y"}]
    assert result_sets_equal(a, b)


def test_row_order_ignored_by_default() -> None:
    a = [{"id": 1}, {"id": 2}]
    b = [{"id": 2}, {"id": 1}]
    assert result_sets_equal(a, b)


def test_row_order_matters_when_asked() -> None:
    a = [{"id": 1}, {"id": 2}]
    b = [{"id": 2}, {"id": 1}]
    assert not result_sets_equal(a, b, order_matters=True)


def test_column_order_ignored_for_dict_rows() -> None:
    a = [{"name": "x", "id": 1}]
    b = [{"id": 1, "name": "x"}]
    assert result_sets_equal(a, b)


def test_null_equals_null() -> None:
    a = [{"x": None}]
    b = [{"x": None}]
    assert result_sets_equal(a, b)


def test_different_row_counts_differ() -> None:
    assert not result_sets_equal([{"x": 1}], [{"x": 1}, {"x": 2}])


def test_float_rounding_within_tolerance() -> None:
    a = [{"v": 1.000000001}]
    b = [{"v": 1.000000002}]
    assert result_sets_equal(a, b)


# ── compute_ex --------------------------------------------------------


def test_compute_ex_returns_1_when_equal() -> None:
    assert compute_ex([{"x": 1}], [{"x": 1}]) == 1


def test_compute_ex_returns_0_when_different() -> None:
    assert compute_ex([{"x": 1}], [{"x": 2}]) == 0


def test_compute_ex_honours_gold_order_by() -> None:
    # When gold has ORDER BY, row order matters.
    sql = "SELECT id FROM t ORDER BY id"
    assert compute_ex(
        [{"id": 1}, {"id": 2}],
        [{"id": 2}, {"id": 1}],
        gold_sql=sql,
    ) == 0


def test_gold_specifies_order_detection() -> None:
    assert gold_specifies_order("SELECT 1 FROM t ORDER BY id")
    assert not gold_specifies_order("SELECT 1 FROM t WHERE id > 0")


# ── compute_ves -------------------------------------------------------


def test_ves_zero_when_ex_zero() -> None:
    assert compute_ves(0, 1.0, 0.5) == 0.0


def test_ves_one_when_pred_at_least_as_fast() -> None:
    assert compute_ves(1, 1.0, 1.0) == pytest.approx(1.0)
    assert compute_ves(1, 1.0, 0.5) == pytest.approx(1.0)  # capped at 1.0


def test_ves_proportional_to_sqrt_ratio() -> None:
    # gold = 1 s, pred = 4 s --> R = sqrt(1/4) = 0.5
    v = compute_ves(1, 1.0, 4.0)
    assert v == pytest.approx(0.5, abs=1e-6)


def test_ves_handles_zero_pred_time() -> None:
    # If prediction is implausibly fast (t_pred <= 0), default to 1.0
    assert compute_ves(1, 1.0, 0.0) == 1.0


# ── compute_em --------------------------------------------------------


def test_em_identical_sql() -> None:
    assert compute_em("SELECT 1 FROM t", "SELECT 1 FROM t") == 1


def test_em_whitespace_insensitive() -> None:
    assert compute_em("SELECT   1\n  FROM  t", "SELECT 1 FROM t") == 1


def test_em_case_insensitive_keywords() -> None:
    assert compute_em("select 1 from t", "SELECT 1 FROM t") == 1


def test_em_returns_zero_for_truly_different() -> None:
    assert compute_em(
        "SELECT id FROM t",
        "SELECT name FROM t",
    ) == 0


def test_em_returns_zero_for_unparseable() -> None:
    # Two equally-broken strings still won't match
    assert compute_em("SELECT FROM", "SELECT x FROM y") == 0

"""Tests for the Phase 5 validator pipeline (syntax + business; execution gated)."""
from __future__ import annotations

import os

import pytest

from app.validator import (
    BusinessRuleValidator,
    SyntaxValidator,
    ValidationPipeline,
)
from app.validator.execution import ExecutionValidator

# ───── Syntax ───────────────────────────────────────────────────────


def test_syntax_accepts_valid_select() -> None:
    v = SyntaxValidator()
    r = v.validate("SELECT id FROM stock_quant WHERE id > 0")
    assert r.parsed_ok
    assert "stock_quant" in r.referenced_tables


def test_syntax_rejects_empty_sql() -> None:
    v = SyntaxValidator()
    r = v.validate("")
    assert not r.parsed_ok
    assert any("empty" in i.message.lower() for i in r.issues)


def test_syntax_rejects_parse_error() -> None:
    v = SyntaxValidator()
    r = v.validate("SELEKT * FROM nothing WHERE")
    assert not r.parsed_ok


def test_syntax_rejects_two_statements() -> None:
    v = SyntaxValidator()
    r = v.validate("SELECT 1; SELECT 2")
    assert not r.parsed_ok
    assert any("statement" in i.message.lower() for i in r.issues)


def test_syntax_rejects_mutation() -> None:
    v = SyntaxValidator()
    r = v.validate("DELETE FROM stock_quant WHERE id = 1")
    # parser may accept syntactically but our pipeline forbids the node.
    assert any("forbidden" in i.message.lower() for i in r.issues)


def test_syntax_enforces_allow_list() -> None:
    v = SyntaxValidator(allowed_tables=frozenset({"stock_quant"}))
    r = v.validate("SELECT * FROM stock_quant JOIN account_move ON id = id")
    assert any("account_move" in i.message for i in r.issues)


# ───── Business ─────────────────────────────────────────────────────


def test_business_flags_empty_results_when_expected() -> None:
    biz = BusinessRuleValidator(expect_rows=True)
    r = biz.validate((), intent="supply_chain_question")
    assert any(i.kind == "business_rule" for i in r.issues)


def test_business_passes_normal_result() -> None:
    biz = BusinessRuleValidator()
    rows = ({"name": "A", "quantity": 10},)
    r = biz.validate(rows, intent="supply_chain_question")
    assert r.issues == ()


def test_business_flags_negative_quantity() -> None:
    biz = BusinessRuleValidator()
    rows = ({"name": "A", "quantity": -5},)
    r = biz.validate(rows, intent="supply_chain_question")
    assert any("negative" in i.message.lower() for i in r.issues)


def test_business_warns_on_huge_amounts() -> None:
    biz = BusinessRuleValidator()
    rows = ({"name": "A", "amount_total": 1e15},)
    r = biz.validate(rows, intent="supply_chain_question")
    assert any("implausibly" in i.message.lower() for i in r.issues)


# ───── Pipeline (mocked execution) ──────────────────────────────────


class _StubExecution(ExecutionValidator):
    """ExecutionValidator that doesn't actually hit the DB."""

    def __init__(self) -> None:  # type: ignore[no-untyped-def]
        # Skip super().__init__ — we don't need an adapter.
        self._timeout_s = 1
        self._max_rows = 100

    def validate(self, sql: str, *, execute: bool = False):  # type: ignore[override]
        from app.validator.execution import ExecutionResult
        return ExecutionResult(issues=(), rows=(), row_count=0, explained=True)


def test_pipeline_runs_syntax_then_execution() -> None:
    pipe = ValidationPipeline(
        syntax=SyntaxValidator(),
        execution=_StubExecution(),
    )
    report = pipe.run("SELECT 1")
    assert report.ok
    assert report.syntax_ok
    assert report.execution_ok


def test_pipeline_short_circuits_on_syntax_failure() -> None:
    pipe = ValidationPipeline(
        syntax=SyntaxValidator(),
        execution=_StubExecution(),
    )
    report = pipe.run("")     # empty SQL — definitely rejected
    assert not report.ok
    assert not report.syntax_ok


def test_pipeline_short_circuits_on_forbidden_statement() -> None:
    pipe = ValidationPipeline(
        syntax=SyntaxValidator(),
        execution=_StubExecution(),
    )
    report = pipe.run("DELETE FROM stock_quant WHERE id = 1")
    assert not report.ok
    assert any("forbidden" in i.message.lower() for i in report.issues)


# ───── Live execution (only if Postgres is reachable) ───────────────


@pytest.mark.integration
def test_execution_runs_explain_against_live_db() -> None:
    if os.getenv("RUN_INTEGRATION") != "1":
        pytest.skip("set RUN_INTEGRATION=1 to enable")
    from app.db.postgres import PostgresAdapter, PostgresConfig
    cfg = PostgresConfig.from_env()
    pg = PostgresAdapter(cfg)
    if not pg.ping():
        pytest.skip("Postgres not reachable")
    v = ExecutionValidator(pg, timeout_s=5)
    r = v.validate("SELECT 1 AS n")
    assert r.explained
    assert r.issues == ()


@pytest.mark.integration
def test_execution_returns_issue_for_missing_table() -> None:
    if os.getenv("RUN_INTEGRATION") != "1":
        pytest.skip("set RUN_INTEGRATION=1 to enable")
    from app.db.postgres import PostgresAdapter, PostgresConfig
    cfg = PostgresConfig.from_env()
    pg = PostgresAdapter(cfg)
    if not pg.ping():
        pytest.skip("Postgres not reachable")
    v = ExecutionValidator(pg, timeout_s=5)
    r = v.validate("SELECT * FROM definitely_no_such_table")
    assert r.issues
    assert any("does not exist" in i.message.lower() or "relation" in i.message.lower()
               for i in r.issues)

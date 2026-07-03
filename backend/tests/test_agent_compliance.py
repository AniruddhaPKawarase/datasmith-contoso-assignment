"""Tests for ComplianceProcessor — RBAC predicate injection."""
from __future__ import annotations

from app.agents.compliance import ComplianceContext, ComplianceProcessor
from app.agents.messages import MessageLog
from app.schema.metadata import (
    Column,
    SchemaMetadata,
    Table,
)


def _meta_with_company_and_warehouse() -> SchemaMetadata:
    return SchemaMetadata(
        database="t", schema="public", extracted_at="now",
        tables=(
            Table(
                name="account_move",
                columns=(
                    Column(name="id", data_type="int", is_nullable=False, is_primary_key=True),
                    Column(name="company_id", data_type="int", is_nullable=True),
                ),
                foreign_keys=(),
            ),
            Table(
                name="stock_quant",
                columns=(
                    Column(name="id", data_type="int", is_nullable=False, is_primary_key=True),
                    Column(name="warehouse_id", data_type="int", is_nullable=True),
                ),
                foreign_keys=(),
            ),
            Table(
                name="product_template",
                columns=(
                    Column(name="id", data_type="int", is_nullable=False, is_primary_key=True),
                    Column(name="name", data_type="text", is_nullable=True),
                ),
                foreign_keys=(),
            ),
        ),
    )


def test_injects_company_predicate_into_where() -> None:
    proc = ComplianceProcessor(_meta_with_company_and_warehouse())
    sql = "SELECT * FROM account_move am WHERE am.state = 'posted'"
    ctx = ComplianceContext(user_id=1, user_role="analyst",
                            company_ids=(1, 2), warehouse_ids=())
    d = proc.apply(sql, ctx)
    assert "company_id IN (1, 2)" in d.sql
    assert "WHERE" in d.sql.upper()
    assert d.bypassed is False
    assert len(d.predicates_added) == 1


def test_injects_warehouse_predicate_into_where() -> None:
    proc = ComplianceProcessor(_meta_with_company_and_warehouse())
    sql = "SELECT * FROM stock_quant sq WHERE sq.quantity > 0"
    ctx = ComplianceContext(user_id=1, user_role="analyst",
                            company_ids=(), warehouse_ids=(3, 4))
    d = proc.apply(sql, ctx)
    assert "warehouse_id IN (3, 4)" in d.sql


def test_adds_where_when_none_exists() -> None:
    proc = ComplianceProcessor(_meta_with_company_and_warehouse())
    sql = "SELECT id FROM account_move ORDER BY id"
    ctx = ComplianceContext(user_id=1, user_role="analyst",
                            company_ids=(7,), warehouse_ids=())
    d = proc.apply(sql, ctx)
    assert "WHERE" in d.sql.upper()
    assert "company_id IN (7)" in d.sql
    assert "ORDER BY" in d.sql.upper()


def test_skips_tables_without_company_column() -> None:
    proc = ComplianceProcessor(_meta_with_company_and_warehouse())
    sql = "SELECT name FROM product_template"
    ctx = ComplianceContext(user_id=1, user_role="analyst",
                            company_ids=(1,), warehouse_ids=())
    d = proc.apply(sql, ctx)
    # product_template has no company_id — no injection
    assert "company_id" not in d.sql
    assert d.predicates_added == ()


def test_admin_role_bypasses_rbac() -> None:
    proc = ComplianceProcessor(_meta_with_company_and_warehouse())
    sql = "SELECT * FROM account_move"
    ctx = ComplianceContext(user_id=1, user_role="admin",
                            company_ids=(1,), warehouse_ids=(),
                            bypass=True)
    d = proc.apply(sql, ctx)
    assert d.bypassed is True
    assert d.sql == sql


def test_empty_sql_returns_empty() -> None:
    proc = ComplianceProcessor(_meta_with_company_and_warehouse())
    ctx = ComplianceContext(user_id=1, user_role="analyst",
                            company_ids=(1,), warehouse_ids=())
    d = proc.apply("", ctx)
    assert d.sql == ""
    assert d.predicates_added == ()


def test_audit_log_records_invocation() -> None:
    log = MessageLog()
    proc = ComplianceProcessor(_meta_with_company_and_warehouse())
    sql = "SELECT * FROM account_move"
    ctx = ComplianceContext(user_id=42, user_role="analyst",
                            company_ids=(1,), warehouse_ids=())
    proc.apply(sql, ctx, message_log=log, correlation_id="abc")
    msgs = log.by_correlation("abc")
    assert len(msgs) == 1
    assert msgs[0].from_agent == "compliance"
    assert msgs[0].payload["user_id"] == 42

"""Tests for the AST-based Phase 5 ComplianceProcessor.

The key fix vs Phase 4: predicates are injected at the SELECT-scope of the
table being protected — so an alias defined inside a CTE never leaks to
the outer query's WHERE clause.
"""
from __future__ import annotations

import sqlglot

from app.agents.compliance import ComplianceContext, ComplianceProcessor
from app.schema.metadata import (
    Column,
    SchemaMetadata,
    Table,
)


def _meta() -> SchemaMetadata:
    return SchemaMetadata(
        database="t", schema="public", extracted_at="now",
        tables=(
            Table(
                name="account_move",
                columns=(
                    Column(name="id", data_type="int", is_nullable=False, is_primary_key=True),
                    Column(name="company_id", data_type="int", is_nullable=True),
                    Column(name="state", data_type="text", is_nullable=True),
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


def test_predicate_appears_inside_cte_not_outer() -> None:
    """The crucial Phase-5 regression test for Query 4."""
    sql = (
        "WITH q_finance AS ( "
        "  SELECT SUM(credit) AS revenue FROM account_move am "
        "  WHERE am.state = 'posted' "
        ") "
        "SELECT * FROM q_finance"
    )
    ctx = ComplianceContext(
        user_id=1, user_role="analyst",
        company_ids=(7,), warehouse_ids=(),
    )
    d = ComplianceProcessor(_meta()).apply(sql, ctx)

    # The predicate should be inside the CTE's WHERE, NOT after the outer SELECT.
    parsed = sqlglot.parse_one(d.sql, read="postgres")
    assert parsed is not None
    # Find every SELECT and check which one contains the company_id IN predicate.
    company_in_outer = False
    company_in_cte = False
    import sqlglot.expressions as exp
    for sel in parsed.find_all(exp.Select):
        # Render this SELECT's WHERE clause; look for company_id IN
        where = sel.args.get("where")
        if where is None:
            continue
        where_text = where.sql(dialect="postgres")
        if "company_id" in where_text and "IN (7)" in where_text:
            # which CTE is this SELECT in?
            parent = sel.parent
            while parent is not None:
                if isinstance(parent, exp.CTE):
                    company_in_cte = True
                    break
                parent = parent.parent
            else:
                company_in_outer = True

    assert company_in_cte, "Compliance predicate should land inside the CTE that references am."
    assert not company_in_outer, "Compliance predicate must NOT leak to the outer SELECT."


def test_no_company_no_predicate() -> None:
    """Tables without a company_id column are not touched."""
    sql = "SELECT name FROM product_template"
    ctx = ComplianceContext(user_id=1, user_role="analyst",
                            company_ids=(1,), warehouse_ids=())
    d = ComplianceProcessor(_meta()).apply(sql, ctx)
    assert "company_id" not in d.sql.lower()
    assert d.predicates_added == ()


def test_admin_bypass() -> None:
    sql = "SELECT * FROM account_move"
    ctx = ComplianceContext(user_id=1, user_role="admin",
                            company_ids=(1,), warehouse_ids=(),
                            bypass=True)
    d = ComplianceProcessor(_meta()).apply(sql, ctx)
    assert d.bypassed is True
    assert d.sql == sql


def test_creates_where_when_none_exists() -> None:
    sql = "SELECT id FROM account_move am ORDER BY id"
    ctx = ComplianceContext(user_id=1, user_role="analyst",
                            company_ids=(9,), warehouse_ids=())
    d = ComplianceProcessor(_meta()).apply(sql, ctx)
    assert "WHERE" in d.sql.upper()
    assert "company_id" in d.sql.lower()
    # ORDER BY preserved
    assert "ORDER BY" in d.sql.upper()


def test_unparseable_sql_returns_unchanged() -> None:
    sql = "SELECT * FROM"
    ctx = ComplianceContext(user_id=1, user_role="analyst",
                            company_ids=(1,), warehouse_ids=())
    d = ComplianceProcessor(_meta()).apply(sql, ctx)
    assert d.sql == sql
    assert d.predicates_added == ()

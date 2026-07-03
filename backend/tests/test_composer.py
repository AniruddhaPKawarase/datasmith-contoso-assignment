"""Tests for the deterministic Composer (Phase 5)."""
from __future__ import annotations

from app.agents.state import AgentOutput
from app.composer import Composer
from app.schema.domains import Domain
from app.schema.joins import JoinGraph
from app.schema.metadata import (
    Column,
    ForeignKey,
    SchemaMetadata,
    Table,
)


def _meta_with_company_link() -> SchemaMetadata:
    return SchemaMetadata(
        database="t", schema="public", extracted_at="now",
        tables=(
            Table(
                name="stock_move",
                columns=(
                    Column(name="id", data_type="int", is_nullable=False, is_primary_key=True),
                    Column(name="company_id", data_type="int", is_nullable=True),
                ),
                foreign_keys=(
                    ForeignKey(from_column="company_id", to_table="res_company", to_column="id"),
                ),
            ),
            Table(
                name="account_move",
                columns=(
                    Column(name="id", data_type="int", is_nullable=False, is_primary_key=True),
                    Column(name="company_id", data_type="int", is_nullable=True),
                ),
                foreign_keys=(
                    ForeignKey(from_column="company_id", to_table="res_company", to_column="id"),
                ),
            ),
            Table(
                name="res_company",
                columns=(
                    Column(name="id", data_type="int", is_nullable=False, is_primary_key=True),
                ),
                foreign_keys=(),
            ),
        ),
    )


def test_compose_zero_fragments_returns_empty() -> None:
    out = Composer().compose(())
    assert out.sql == ""
    assert out.join_strategy == "noop"


def test_compose_single_fragment_passes_through() -> None:
    o = AgentOutput(
        domain=Domain.INVENTORY,
        sql="SELECT * FROM stock_quant",
        confidence=0.9, used_tables=("stock_quant",),
    )
    out = Composer().compose((o,))
    assert out.sql.endswith(";")
    assert "stock_quant" in out.sql
    assert out.join_strategy == "passthrough"


def test_compose_two_fragments_cross_joins_when_no_join_key() -> None:
    inv = AgentOutput(
        domain=Domain.INVENTORY,
        sql="SELECT SUM(quantity) AS on_hand FROM stock_quant",
        confidence=0.9, used_tables=("stock_quant",),
    )
    fin = AgentOutput(
        domain=Domain.FINANCE,
        sql="SELECT SUM(credit) AS revenue FROM account_move",
        confidence=0.9, used_tables=("account_move",),
    )
    out = Composer().compose((inv, fin))
    assert "WITH" in out.sql.upper()
    assert "q_inventory" in out.sql
    assert "q_finance" in out.sql
    assert "CROSS JOIN" in out.sql.upper()
    assert out.join_strategy == "cross_join"


def test_compose_inner_joins_on_shared_company_id() -> None:
    meta = _meta_with_company_link()
    graph = JoinGraph(meta)
    inv = AgentOutput(
        domain=Domain.INVENTORY,
        sql="SELECT company_id, SUM(quantity) AS on_hand FROM stock_move GROUP BY company_id",
        confidence=0.9, used_tables=("stock_move",),
    )
    fin = AgentOutput(
        domain=Domain.FINANCE,
        sql="SELECT company_id, SUM(credit) AS revenue FROM account_move GROUP BY company_id",
        confidence=0.9, used_tables=("account_move",),
    )
    out = Composer(join_graph=graph).compose((inv, fin))
    assert "INNER JOIN" in out.sql.upper() or "JOIN" in out.sql.upper()
    assert "USING (company_id)" in out.sql
    assert out.join_strategy.startswith("inner_join:")
    assert out.shared_key == "company_id"


def test_compose_handles_unparseable_fragment_gracefully() -> None:
    bad = AgentOutput(
        domain=Domain.INVENTORY,
        sql="SELECT *** broken syntax FROM",
        confidence=0.0, used_tables=("stock_quant",),
    )
    good = AgentOutput(
        domain=Domain.FINANCE,
        sql="SELECT 1",
        confidence=0.9, used_tables=("account_move",),
    )
    out = Composer().compose((bad, good))
    assert out.join_strategy == "noop"
    assert "Parse failure" in out.notes


def test_compose_skips_empty_fragments() -> None:
    o1 = AgentOutput(domain=Domain.INVENTORY, sql="",
                       confidence=0.0, used_tables=())
    o2 = AgentOutput(
        domain=Domain.FINANCE,
        sql="SELECT SUM(credit) FROM account_move",
        confidence=0.9, used_tables=("account_move",),
    )
    out = Composer().compose((o1, o2))
    assert "account_move" in out.sql
    assert out.join_strategy == "passthrough"

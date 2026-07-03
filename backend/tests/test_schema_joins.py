"""Tests for the FK join graph + path discovery."""
from __future__ import annotations

from app.schema.joins import JoinGraph
from app.schema.metadata import Column, ForeignKey, SchemaMetadata, Table


def _meta() -> SchemaMetadata:
    """Schema: stock_move → product_product → product_template; account_move → res_partner."""
    pt = Table(
        name="product_template",
        columns=(Column(name="id", data_type="int", is_nullable=False, is_primary_key=True),),
        foreign_keys=(),
    )
    pp = Table(
        name="product_product",
        columns=(
            Column(name="id", data_type="int", is_nullable=False, is_primary_key=True),
            Column(name="product_tmpl_id", data_type="int", is_nullable=False),
        ),
        foreign_keys=(
            ForeignKey(from_column="product_tmpl_id", to_table="product_template", to_column="id"),
        ),
    )
    sm = Table(
        name="stock_move",
        columns=(
            Column(name="id", data_type="int", is_nullable=False, is_primary_key=True),
            Column(name="product_id", data_type="int", is_nullable=False),
        ),
        foreign_keys=(
            ForeignKey(from_column="product_id", to_table="product_product", to_column="id"),
        ),
    )
    am = Table(
        name="account_move",
        columns=(
            Column(name="id", data_type="int", is_nullable=False, is_primary_key=True),
            Column(name="partner_id", data_type="int", is_nullable=True),
        ),
        foreign_keys=(
            ForeignKey(from_column="partner_id", to_table="res_partner", to_column="id"),
        ),
    )
    rp = Table(
        name="res_partner",
        columns=(Column(name="id", data_type="int", is_nullable=False, is_primary_key=True),),
        foreign_keys=(),
    )
    return SchemaMetadata(
        database="test",
        schema="public",
        extracted_at="2026-05-14T00:00:00+00:00",
        tables=(pt, pp, sm, am, rp),
    )


def test_shortest_path_one_hop() -> None:
    g = JoinGraph(_meta())
    path = g.shortest_path("stock_move", "product_product")
    assert path is not None
    assert path.length == 1
    assert path.steps[0].to_sql_on() == "stock_move.product_id = product_product.id"


def test_shortest_path_two_hops() -> None:
    g = JoinGraph(_meta())
    path = g.shortest_path("stock_move", "product_template")
    assert path is not None
    assert path.length == 2
    assert path.tables == ("stock_move", "product_product", "product_template")


def test_shortest_path_same_table() -> None:
    g = JoinGraph(_meta())
    path = g.shortest_path("stock_move", "stock_move")
    assert path is not None
    assert path.length == 0


def test_shortest_path_unreachable_components() -> None:
    g = JoinGraph(_meta())
    # account_move is in a separate FK component from stock_move
    path = g.shortest_path("stock_move", "res_partner")
    assert path is None


def test_shortest_path_unknown_table() -> None:
    g = JoinGraph(_meta())
    assert g.shortest_path("ghost_table", "stock_move") is None
    assert g.shortest_path("stock_move", "ghost_table") is None


def test_max_hops_limit() -> None:
    g = JoinGraph(_meta())
    # 2-hop path exists; max_hops=1 prevents discovery
    assert g.shortest_path("stock_move", "product_template", max_hops=1) is None


def test_all_paths_returns_sorted() -> None:
    g = JoinGraph(_meta())
    paths = g.all_paths("stock_move", "product_template", max_hops=3, max_paths=5)
    assert paths
    # Sorted by length ascending
    lengths = [p.length for p in paths]
    assert lengths == sorted(lengths)


def test_to_sql_joins_renders() -> None:
    g = JoinGraph(_meta())
    path = g.shortest_path("stock_move", "product_template")
    assert path is not None
    rendered = path.to_sql_joins()
    assert "JOIN product_product" in rendered
    assert "JOIN product_template" in rendered
    assert "stock_move.product_id = product_product.id" in rendered

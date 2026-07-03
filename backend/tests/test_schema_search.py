"""Tests for the NL-term schema search index."""
from __future__ import annotations

from app.schema.metadata import Column, ForeignKey, SchemaMetadata, Table
from app.schema.search import SchemaSearch


def _meta() -> SchemaMetadata:
    sm = Table(
        name="stock_move",
        columns=(
            Column(name="id", data_type="int", is_nullable=False, is_primary_key=True),
            Column(name="product_id", data_type="int", is_nullable=False,
                   description="Product reference", odoo_ttype="many2one"),
            Column(name="quantity", data_type="numeric", is_nullable=True,
                   description="On-hand quantity"),
        ),
        foreign_keys=(ForeignKey("product_id", "product_product", "id"),),
        odoo_model="stock.move",
        odoo_description="Stock Move",
    )
    so = Table(
        name="sale_order",
        columns=(
            Column(name="id", data_type="int", is_nullable=False, is_primary_key=True),
            Column(name="amount_total", data_type="numeric", is_nullable=True,
                   description="Total order amount"),
        ),
        foreign_keys=(),
        odoo_model="sale.order",
        odoo_description="Sales Order",
    )
    am = Table(
        name="account_move",
        columns=(
            Column(name="id", data_type="int", is_nullable=False, is_primary_key=True),
        ),
        foreign_keys=(),
        odoo_model="account.move",
        odoo_description="Journal Entry",
    )
    return SchemaMetadata(
        database="test",
        schema="public",
        extracted_at="2026-05-14T00:00:00+00:00",
        tables=(sm, so, am),
    )


def test_search_finds_relevant_table() -> None:
    s = SchemaSearch(_meta())
    hits = s.search("show me current stock on hand")
    assert hits
    assert hits[0].table == "stock_move"


def test_search_returns_empty_on_no_match() -> None:
    s = SchemaSearch(_meta())
    assert s.search("xyznonsensenowordmatches") == []


def test_search_respects_allowed_tables() -> None:
    s = SchemaSearch(_meta())
    # Restrict to demand's primaries — stock_move not visible
    hits = s.search("stock quantity", allowed_tables=frozenset({"sale_order"}))
    table_names = {h.table for h in hits}
    assert "stock_move" not in table_names


def test_search_top_k_limit() -> None:
    s = SchemaSearch(_meta())
    hits = s.search("order amount", top_k=1)
    assert len(hits) <= 1


def test_search_handles_empty_query() -> None:
    s = SchemaSearch(_meta())
    assert s.search("") == []
    assert s.search("    ") == []

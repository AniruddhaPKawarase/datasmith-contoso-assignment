"""Tests for the immutable schema metadata dataclasses + JSON round-trip."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from app.schema.metadata import Column, ForeignKey, SchemaMetadata, Table


def _toy_meta() -> SchemaMetadata:
    cols_sm = (
        Column(name="id", data_type="integer", is_nullable=False, is_primary_key=True),
        Column(name="product_id", data_type="integer", is_nullable=False,
               description="Product", odoo_ttype="many2one", relation_model="product.product"),
        Column(name="quantity", data_type="numeric", is_nullable=True,
               description="On-hand quantity"),
    )
    fks_sm = (
        ForeignKey(from_column="product_id", to_table="product_product", to_column="id"),
    )
    sm = Table(
        name="stock_move",
        columns=cols_sm,
        foreign_keys=fks_sm,
        odoo_model="stock.move",
        odoo_description="Stock Move",
        row_count=84,
    )
    pp = Table(
        name="product_product",
        columns=(Column(name="id", data_type="integer", is_nullable=False, is_primary_key=True),),
        foreign_keys=(),
        odoo_model="product.product",
        odoo_description="Product Variant",
        row_count=51,
    )
    return SchemaMetadata(
        database="test_db",
        schema="public",
        extracted_at="2026-05-14T00:00:00+00:00",
        tables=(sm, pp),
        notes={"source": "test"},
    )


def test_table_column_lookup() -> None:
    meta = _toy_meta()
    sm = meta.table("stock_move")
    assert sm is not None
    assert sm.column("product_id") is not None
    assert sm.column("nonexistent") is None


def test_metadata_aggregates() -> None:
    meta = _toy_meta()
    assert meta.table_count == 2
    assert meta.total_columns == 4
    assert meta.total_foreign_keys == 1


def test_immutability_enforced() -> None:
    meta = _toy_meta()
    with pytest.raises(dataclasses.FrozenInstanceError):
        meta.tables[0].columns[0].name = "mutated"  # type: ignore[misc]


def test_json_roundtrip(tmp_path: Path) -> None:
    meta = _toy_meta()
    out = tmp_path / "schema.json"
    meta.to_json(out)
    loaded = SchemaMetadata.from_json(out)
    assert loaded.table_count == meta.table_count
    assert loaded.total_columns == meta.total_columns
    assert loaded.total_foreign_keys == meta.total_foreign_keys
    assert loaded.table("stock_move").column("product_id").description == "Product"


def test_json_includes_summary_fields(tmp_path: Path) -> None:
    out = tmp_path / "schema.json"
    _toy_meta().to_json(out)
    raw = json.loads(out.read_text(encoding="utf-8"))
    assert raw["table_count"] == 2
    assert raw["total_columns"] == 4
    assert raw["total_foreign_keys"] == 1

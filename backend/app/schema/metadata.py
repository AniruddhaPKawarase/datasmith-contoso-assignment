"""Immutable dataclasses for schema metadata.

These are value objects: never mutate, always return new instances. The
``SchemaMetadata`` aggregate is serialisable to JSON so we can cache the
introspection result on disk and avoid re-querying the DB on every startup.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ForeignKey:
    """A column-to-column foreign-key relationship."""

    from_column: str          # column on this table
    to_table: str             # referenced table
    to_column: str            # referenced column
    constraint_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Column:
    """A single column in a table."""

    name: str
    data_type: str            # postgres type, e.g. 'character varying'
    is_nullable: bool
    is_primary_key: bool = False
    default: str | None = None
    description: str = ""     # from Odoo ir_model_fields.field_description.en_US
    odoo_ttype: str = ""      # Odoo field type: char, integer, many2one, ...
    relation_model: str = ""  # for many2one/one2many — referenced Odoo model

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Table:
    """A single table with all its columns and outgoing FKs."""

    name: str
    columns: tuple[Column, ...]
    foreign_keys: tuple[ForeignKey, ...]
    odoo_model: str = ""              # e.g. 'stock.move' (None if non-Odoo table)
    odoo_description: str = ""        # from ir_model.name (English)
    row_count: int = 0                # snapshot at introspection time

    def column(self, name: str) -> Column | None:
        for col in self.columns:
            if col.name == name:
                return col
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "columns": [c.to_dict() for c in self.columns],
            "foreign_keys": [fk.to_dict() for fk in self.foreign_keys],
            "odoo_model": self.odoo_model,
            "odoo_description": self.odoo_description,
            "row_count": self.row_count,
        }


@dataclass(frozen=True)
class SchemaMetadata:
    """Whole-database snapshot. Serialisable to JSON."""

    database: str
    schema: str
    extracted_at: str                 # ISO-8601 timestamp
    tables: tuple[Table, ...]
    notes: dict[str, str] = field(default_factory=dict)

    def table(self, name: str) -> Table | None:
        for t in self.tables:
            if t.name == name:
                return t
        return None

    @property
    def table_count(self) -> int:
        return len(self.tables)

    @property
    def total_columns(self) -> int:
        return sum(len(t.columns) for t in self.tables)

    @property
    def total_foreign_keys(self) -> int:
        return sum(len(t.foreign_keys) for t in self.tables)

    def to_dict(self) -> dict[str, Any]:
        return {
            "database": self.database,
            "schema": self.schema,
            "extracted_at": self.extracted_at,
            "table_count": self.table_count,
            "total_columns": self.total_columns,
            "total_foreign_keys": self.total_foreign_keys,
            "tables": [t.to_dict() for t in self.tables],
            "notes": dict(self.notes),
        }

    def to_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @classmethod
    def from_json(cls, path: Path) -> SchemaMetadata:
        data = json.loads(path.read_text(encoding="utf-8"))
        tables = tuple(
            Table(
                name=t["name"],
                columns=tuple(Column(**c) for c in t["columns"]),
                foreign_keys=tuple(ForeignKey(**fk) for fk in t["foreign_keys"]),
                odoo_model=t.get("odoo_model", ""),
                odoo_description=t.get("odoo_description", ""),
                row_count=t.get("row_count", 0),
            )
            for t in data["tables"]
        )
        return cls(
            database=data["database"],
            schema=data["schema"],
            extracted_at=data["extracted_at"],
            tables=tables,
            notes=dict(data.get("notes", {})),
        )

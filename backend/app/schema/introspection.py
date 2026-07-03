"""Schema introspection — pulls PostgreSQL structure plus Odoo semantic metadata.

We combine two sources:

1. **PostgreSQL information_schema + pg_catalog**
   — authoritative table/column/FK structure.

2. **Odoo's ir_model and ir_model_fields**
   — semantic descriptions, business-friendly field names, Odoo field types
     (many2one / one2many / selection / monetary / ...), and relation hints
     that PG-level FKs alone don't capture (Odoo uses logical FKs via the
     ORM that may not have a hard SQL constraint).

The combined output (``SchemaMetadata``) feeds:
- Domain mapping (which tables belong to which agent)
- CSR-RAG retrieval (NL term -> relevant table/column)
- Business glossary (column semantics)
- Join-path discovery (FK graph traversal)
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.db.postgres import PostgresAdapter
from app.schema.metadata import (
    Column,
    ForeignKey,
    SchemaMetadata,
    Table,
)

logger = logging.getLogger(__name__)


_TABLES_SQL = """
SELECT
    c.table_name,
    c.column_name,
    c.ordinal_position,
    c.data_type,
    c.is_nullable = 'YES'              AS is_nullable,
    c.column_default,
    EXISTS (
        SELECT 1 FROM pg_constraint pc
        JOIN pg_class cl ON cl.oid = pc.conrelid
        JOIN pg_namespace n ON n.oid = cl.relnamespace
        WHERE pc.contype = 'p'
          AND n.nspname = c.table_schema
          AND cl.relname = c.table_name
          AND c.column_name = ANY (
              SELECT a.attname
              FROM pg_attribute a
              WHERE a.attrelid = cl.oid
                AND a.attnum = ANY (pc.conkey)
          )
    ) AS is_primary_key
FROM information_schema.columns c
WHERE c.table_schema = %s
ORDER BY c.table_name, c.ordinal_position
"""


_FKS_SQL = """
SELECT
    tc.table_name      AS from_table,
    kcu.column_name    AS from_column,
    ccu.table_name     AS to_table,
    ccu.column_name    AS to_column,
    tc.constraint_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
 AND tc.table_schema    = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
  ON ccu.constraint_name = tc.constraint_name
 AND ccu.table_schema    = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = %s
ORDER BY tc.table_name, tc.constraint_name
"""


# Odoo model -> PostgreSQL table name follows: replace '.' with '_'.
_ODOO_MODELS_SQL = """
SELECT
    m.model,
    REPLACE(m.model, '.', '_') AS table_name,
    m.name->>'en_US'           AS description
FROM ir_model m
"""

_ODOO_FIELDS_SQL = """
SELECT
    f.model,
    REPLACE(f.model, '.', '_')              AS table_name,
    f.name                                  AS column_name,
    f.field_description->>'en_US'           AS description,
    f.ttype                                 AS odoo_ttype,
    COALESCE(f.relation, '')                AS relation_model
FROM ir_model_fields f
"""


_TABLE_ROW_COUNTS_SQL = """
SELECT
    relname AS table_name,
    n_live_tup AS row_count
FROM pg_stat_user_tables
WHERE schemaname = %s
"""


class SchemaIntrospector:
    """Extracts a ``SchemaMetadata`` snapshot from a live PostgreSQL DB.

    Designed to be cheap to run (single pass over information_schema + a few
    Odoo metadata queries) but produces a result that can be cached on disk
    via ``SchemaMetadata.to_json()``.
    """

    def __init__(self, adapter: PostgresAdapter, *, schema: str = "public") -> None:
        self._db = adapter
        self._schema = schema

    def introspect(self) -> SchemaMetadata:
        """Build the full schema metadata snapshot."""
        logger.info("Introspecting schema '%s'", self._schema)
        odoo_models = self._fetch_odoo_models()
        odoo_fields = self._fetch_odoo_fields()
        fks_by_table = self._fetch_foreign_keys()
        row_counts = self._fetch_row_counts()
        columns_by_table = self._fetch_columns(odoo_fields)

        tables: list[Table] = []
        for table_name in sorted(columns_by_table.keys()):
            cols = columns_by_table[table_name]
            fks = tuple(fks_by_table.get(table_name, ()))
            odoo_info = odoo_models.get(table_name, ("", ""))
            tables.append(
                Table(
                    name=table_name,
                    columns=cols,
                    foreign_keys=fks,
                    odoo_model=odoo_info[0],
                    odoo_description=odoo_info[1],
                    row_count=row_counts.get(table_name, 0),
                )
            )

        meta = SchemaMetadata(
            database=self._database_name(),
            schema=self._schema,
            extracted_at=datetime.now(UTC).isoformat(timespec="seconds"),
            tables=tuple(tables),
            notes={
                "source": "PostgreSQL information_schema + Odoo ir_model_fields",
                "odoo_model_count": str(len(odoo_models)),
                "odoo_field_count": str(len(odoo_fields)),
            },
        )
        logger.info(
            "Introspection complete: %d tables, %d columns, %d FKs",
            meta.table_count,
            meta.total_columns,
            meta.total_foreign_keys,
        )
        return meta

    # ───── private helpers ────────────────────────────────────────────

    def _database_name(self) -> str:
        rows = self._db.fetch_all("SELECT current_database() AS db")
        return str(rows[0]["db"])

    def _fetch_odoo_models(self) -> dict[str, tuple[str, str]]:
        """Map ``table_name`` -> (odoo_model, description). Empty if not an Odoo DB."""
        try:
            rows = self._db.fetch_all(_ODOO_MODELS_SQL)
        except Exception as exc:
            logger.debug("ir_model query skipped: %s", exc)
            return {}
        return {
            r["table_name"]: (r["model"], r.get("description") or "")
            for r in rows
        }

    def _fetch_odoo_fields(self) -> dict[tuple[str, str], dict[str, str]]:
        """Map ``(table_name, column_name)`` -> {description, ttype, relation}."""
        try:
            rows = self._db.fetch_all(_ODOO_FIELDS_SQL)
        except Exception as exc:
            logger.debug("ir_model_fields query skipped: %s", exc)
            return {}
        out: dict[tuple[str, str], dict[str, str]] = {}
        for r in rows:
            key = (r["table_name"], r["column_name"])
            out[key] = {
                "description": r.get("description") or "",
                "odoo_ttype": r.get("odoo_ttype") or "",
                "relation_model": r.get("relation_model") or "",
            }
        return out

    def _fetch_foreign_keys(self) -> dict[str, list[ForeignKey]]:
        rows = self._db.fetch_all(_FKS_SQL, (self._schema,))
        out: dict[str, list[ForeignKey]] = {}
        for r in rows:
            out.setdefault(r["from_table"], []).append(
                ForeignKey(
                    from_column=r["from_column"],
                    to_table=r["to_table"],
                    to_column=r["to_column"],
                    constraint_name=r["constraint_name"],
                )
            )
        return out

    def _fetch_row_counts(self) -> dict[str, int]:
        rows = self._db.fetch_all(_TABLE_ROW_COUNTS_SQL, (self._schema,))
        return {r["table_name"]: int(r["row_count"] or 0) for r in rows}

    def _fetch_columns(
        self,
        odoo_fields: dict[tuple[str, str], dict[str, str]],
    ) -> dict[str, tuple[Column, ...]]:
        rows = self._db.fetch_all(_TABLES_SQL, (self._schema,))
        by_table: dict[str, list[Column]] = {}
        for r in rows:
            tname = r["table_name"]
            cname = r["column_name"]
            odoo = odoo_fields.get((tname, cname), {})
            col = Column(
                name=cname,
                data_type=r["data_type"],
                is_nullable=bool(r["is_nullable"]),
                is_primary_key=bool(r["is_primary_key"]),
                default=r.get("column_default"),
                description=odoo.get("description", ""),
                odoo_ttype=odoo.get("odoo_ttype", ""),
                relation_model=odoo.get("relation_model", ""),
            )
            by_table.setdefault(tname, []).append(col)
        return {t: tuple(cols) for t, cols in by_table.items()}

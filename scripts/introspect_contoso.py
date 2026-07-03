"""Introspect the Contoso Postgres DB and write contoso_schema.json.

Reuses the existing backend/app/schema/introspection.py machinery — it's
Odoo-aware but Odoo lookups fail safely to empty dicts on non-Odoo DBs,
so it works unchanged against Contoso and just leaves odoo_* fields empty.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "contoso"
os.environ["POSTGRES_USER"] = "odoo"
os.environ["POSTGRES_PASSWORD"] = "odoo_dev_pwd"

from app.db.postgres import PostgresAdapter, PostgresConfig
from app.schema.introspection import SchemaIntrospector

adapter = PostgresAdapter(PostgresConfig.from_env())
introspector = SchemaIntrospector(adapter, schema="public")
meta = introspector.introspect()

OUT = ROOT / "backend" / "data" / "contoso_schema.json"
OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(meta.to_dict(), f, indent=2)

print(f"Wrote {OUT}")
print(f"  tables:  {meta.table_count}")
print(f"  columns: {meta.total_columns}")
print(f"  FKs:     {meta.total_foreign_keys}")

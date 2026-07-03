"""Run live introspection against the Odoo Postgres DB and persist metadata.

Reads .env from project root, connects to localhost:5432/odoo, extracts the
full schema + Odoo semantic metadata, writes to
``backend/data/odoo_schema.json`` for downstream consumption.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

env_path = ROOT / ".env"
if env_path.exists():
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

# When run from the host, override the container hostname unconditionally.
# Inside docker-compose the backend uses POSTGRES_HOST=postgres; from a dev
# shell we need to talk to the published port on localhost.
os.environ["POSTGRES_HOST"] = "localhost"

from app.db.postgres import PostgresAdapter, PostgresConfig  # noqa: E402
from app.schema.introspection import SchemaIntrospector  # noqa: E402


def main() -> int:
    cfg = PostgresConfig.from_env()
    print(f"Connecting to {cfg.host}:{cfg.port}/{cfg.database} as {cfg.user}")
    adapter = PostgresAdapter(cfg)
    if not adapter.ping():
        print("Postgres unreachable.")
        return 1

    inspector = SchemaIntrospector(adapter)
    meta = inspector.introspect()

    out = ROOT / "backend" / "data" / "odoo_schema.json"
    meta.to_json(out)

    print(f"Tables:          {meta.table_count}")
    print(f"Total columns:   {meta.total_columns}")
    print(f"Total FKs:       {meta.total_foreign_keys}")
    print(f"Odoo models:     {meta.notes.get('odoo_model_count')}")
    print(f"Odoo fields:     {meta.notes.get('odoo_field_count')}")
    print(f"Persisted to:    {out.relative_to(ROOT)} ({out.stat().st_size / 1024:.1f} KB)")

    # Spot-check three critical tables
    for name in ("stock_move", "sale_order", "account_move"):
        t = meta.table(name)
        if not t:
            print(f"  MISSING: {name}")
            continue
        described = sum(1 for c in t.columns if c.description)
        m2o = sum(1 for c in t.columns if c.odoo_ttype == "many2one")
        print(f"  {name:20s}  cols={len(t.columns):3d}  described={described:3d}  many2one={m2o:3d}  FKs={len(t.foreign_keys):3d}  rows={t.row_count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Load the Cleaned Contoso Dataset (Kaggle: bhanuthakurr/cleaned-contoso-dataset)
into the local Postgres `contoso` database via Postgres's native \\COPY.

Why \\COPY, not pandas:
    FactOnlineSales.csv is 1.24 GB. pandas + chunksize hits OpenBLAS OOM
    on 8 GB RAM. \\COPY streams row-by-row on the server side — near-zero
    Python memory footprint.

Usage:
    python scripts/load_contoso.py

Env:
    CONTOSO_DATA_DIR   — where the CSVs live
                         (default: ../data/contoso/ relative to repo)
"""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = ROOT.parent / "data" / "contoso"

DATA_DIR = Path(os.getenv("CONTOSO_DATA_DIR") or DEFAULT_DATA_DIR)
DB_URL = os.getenv(
    "CONTOSO_DB_URL",
    "postgresql+psycopg://odoo:odoo_dev_pwd@localhost:5432/contoso",
)
CONTAINER = "scm-postgres"

# Curated: assignment-relevant tables only.
TABLES: list[str] = [
    "DimCustomer", "DimDate", "DimEmployee", "DimProduct",
    "DimProductCategory", "DimProductSubcategory", "DimSalesTerritory",
    "DimStore", "DimChannel", "DimPromotion", "DimCurrency",
    "FactOnlineSales", "FactSales", "FactSalesQuota",
]

SNIFF_ROWS = 500


def infer_ddl(csv_path: Path, table_name: str) -> str:
    """Read a small sample to infer column names + types → CREATE TABLE DDL."""
    df = pd.read_csv(csv_path, nrows=SNIFF_ROWS, encoding="utf-8-sig",
                     low_memory=False)
    df.columns = [c.lower() for c in df.columns]
    type_map = {
        "int64": "BIGINT",
        "float64": "DOUBLE PRECISION",
        "bool": "BOOLEAN",
        "datetime64[ns]": "TIMESTAMP",
    }
    cols = []
    for col, dt in df.dtypes.items():
        pg = type_map.get(str(dt), "TEXT")
        cols.append(f'  "{col}" {pg}')
    return (
        f'DROP TABLE IF EXISTS "{table_name}";\n'
        f'CREATE TABLE "{table_name}" (\n'
        + ",\n".join(cols)
        + "\n);"
    )


def docker_exec_psql(sql: str, db: str = "contoso") -> None:
    """Run a SQL string against the container's psql."""
    p = subprocess.run(
        ["docker", "exec", "-i", CONTAINER, "psql", "-U", "odoo",
         "-d", db, "-v", "ON_ERROR_STOP=1", "-q"],
        input=sql, text=True, capture_output=True,
    )
    if p.returncode != 0:
        raise RuntimeError(f"psql failed: {p.stderr[:500]}")


def docker_cp(local: Path, container_path: str) -> None:
    subprocess.run(
        ["docker", "cp", str(local), f"{CONTAINER}:{container_path}"],
        check=True, capture_output=True,
    )


def copy_load(csv_path: Path, table_name: str) -> int:
    """Copy CSV into container, then Postgres \\COPY → table. Delete tmp on exit."""
    container_tmp = f"/tmp/{csv_path.name}"
    docker_cp(csv_path, container_tmp)
    try:
        docker_exec_psql(
            f"""\\COPY "{table_name}" FROM '{container_tmp}' """
            f"WITH (FORMAT csv, HEADER true, NULL 'NULL', ENCODING 'UTF8');"
        )
    finally:
        # cleanup, best-effort
        subprocess.run(
            ["docker", "exec", CONTAINER, "rm", "-f", container_tmp],
            capture_output=True,
        )
    # row count
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        (n,) = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).one()
    return int(n)


def main() -> int:
    if not DATA_DIR.exists():
        print(f"ERROR: data dir not found: {DATA_DIR}")
        return 1

    engine = create_engine(DB_URL, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print(f"Connected: {DB_URL}")
    print(f"Data:      {DATA_DIR}")
    print()

    grand_rows = 0
    grand_time = 0.0
    for tbl in TABLES:
        csv = DATA_DIR / f"{tbl}.csv"
        if not csv.exists():
            print(f"  SKIP {tbl}: not found")
            continue
        target = tbl.lower()
        size_mb = csv.stat().st_size / 1e6
        print(f"  {tbl}.csv ({size_mb:6.1f} MB) → {target}",
              flush=True, end=" ... ")
        t0 = time.time()
        ddl = infer_ddl(csv, target)
        docker_exec_psql(ddl)
        rows = copy_load(csv, target)
        elapsed = time.time() - t0
        grand_rows += rows
        grand_time += elapsed
        print(f"{rows:>10,} rows in {elapsed:6.1f}s")

    print()
    print(f"Total: {grand_rows:,} rows in {grand_time:.1f}s")

    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' ORDER BY table_name"
        ))
        loaded = [r[0] for r in result]
    print(f"Loaded tables: {loaded}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

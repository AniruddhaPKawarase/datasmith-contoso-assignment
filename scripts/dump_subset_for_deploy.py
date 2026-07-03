"""Dump a subset of the local Contoso Postgres to a single SQL file that
fits within a free-tier hosted Postgres (Neon 3 GB, Supabase 500 MB).

Strategy:
- Keep ALL dim tables at full size (<20 MB combined — they're small).
- Sample factonlinesales down to WHERE calendaryear = 2009 (~4 M rows).
- Sample factsales down to calendaryear = 2009 (~1 M rows).
- Keep factsalesquota fully (small).

Output: `deploy_subset.sql` at the repo root. Restore with:

    psql <NEON_URL> -f deploy_subset.sql

Total wall time locally: ~90 s. Output file size: ~600-900 MB (compressible to
~150 MB with gzip if that helps the transfer).

Usage:
    python scripts/dump_subset_for_deploy.py \\
        --host localhost --port 5432 --user odoo --password odoo_dev_pwd \\
        --db contoso --out deploy_subset.sql
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


DIMS_FULL = [
    "dimchannel", "dimcurrency", "dimcustomer", "dimdate",
    "dimemployee", "dimgeography", "dimproduct", "dimproductcategory",
    "dimproductsubcategory", "dimpromotion", "dimsalesterritory", "dimstore",
]

FACT_QUOTA_FULL = ["factsalesquota"]

FACT_2009_ONLY = ["factonlinesales", "factsales"]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", default="5432")
    p.add_argument("--user", default="odoo")
    p.add_argument("--password", default="odoo_dev_pwd")
    p.add_argument("--db", default="contoso")
    p.add_argument("--out", default="deploy_subset.sql", type=Path)
    args = p.parse_args()

    env = {"PGPASSWORD": args.password}

    def run(cmd: list[str], stdout_to: Path | None = None) -> None:
        print("$", " ".join(cmd), flush=True)
        if stdout_to is None:
            r = subprocess.run(cmd, env={**env}, check=False, capture_output=True, text=True)
        else:
            with stdout_to.open("ab") as f:
                r = subprocess.run(cmd, env={**env}, check=False, stdout=f, stderr=subprocess.PIPE, text=True)
        if r.returncode != 0:
            sys.stderr.write((r.stderr or "") + "\n")
            raise SystemExit(f"command failed (exit {r.returncode})")

    args.out.unlink(missing_ok=True)

    # 1) Full schema + full dims + full factsalesquota (via pg_dump --data-only for those tables).
    dim_and_small_facts = DIMS_FULL + FACT_QUOTA_FULL
    tbl_flags: list[str] = []
    for t in dim_and_small_facts:
        tbl_flags.extend(["-t", f"public.{t}"])

    # Schema only for the two big fact tables (data will be inserted via COPY below).
    fact_schema_flags: list[str] = []
    for t in FACT_2009_ONLY:
        fact_schema_flags.extend(["-t", f"public.{t}"])

    schema_cmd = [
        "pg_dump",
        "-h", args.host, "-p", args.port, "-U", args.user, "-d", args.db,
        "--schema-only", "--no-owner", "--no-acl",
    ] + fact_schema_flags
    run(schema_cmd, stdout_to=args.out)

    # Full dump (schema + data) for dims and small facts.
    dims_cmd = [
        "pg_dump",
        "-h", args.host, "-p", args.port, "-U", args.user, "-d", args.db,
        "--no-owner", "--no-acl",
    ] + tbl_flags
    run(dims_cmd, stdout_to=args.out)

    # 2) 2009-only slice of the two big fact tables via psql \COPY.
    with args.out.open("a", encoding="utf-8") as f:
        f.write("\n-- 2009-only slice of factonlinesales + factsales (kept small for free-tier Postgres)\n")

    for tbl in FACT_2009_ONLY:
        copy_cmd = [
            "psql", "-h", args.host, "-p", args.port, "-U", args.user, "-d", args.db,
            "-c", (
                f"\\copy (SELECT * FROM {tbl} "
                f"WHERE datekey >= '2009-01-01' AND datekey < '2010-01-01') "
                f"TO STDOUT WITH CSV HEADER"
            ),
        ]
        csv_path = args.out.with_suffix(f".{tbl}.csv")
        with csv_path.open("w", encoding="utf-8") as fh:
            r = subprocess.run(copy_cmd, env={**env}, check=False, stdout=fh, stderr=subprocess.PIPE, text=True)
        if r.returncode != 0:
            sys.stderr.write((r.stderr or "") + "\n")
            raise SystemExit(f"COPY failed for {tbl}")

        # Append \copy from-csv to the sql script so restore is one command.
        with args.out.open("a", encoding="utf-8") as fh:
            fh.write(
                f"\\copy {tbl} FROM '{csv_path.name}' WITH CSV HEADER;\n"
            )

    print(f"\nWrote {args.out} plus per-fact CSV siblings.")
    print("Restore with:  psql <NEON_URL> -f deploy_subset.sql")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

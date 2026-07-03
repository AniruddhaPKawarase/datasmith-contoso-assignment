"""DuckDB adapter for the analytics warehouse.

DuckDB is in-process (no separate container). We keep a single file under
``data/analytics.duckdb`` that holds:

* The DataCo Smart Supply Chain dataset (180K+ orders) — Phase 8 benchmark.
* Materialised analytical views over the live Odoo data (loaded via
  ``stock_move_summary``, ``sale_funnel_daily``, etc.).

Connections are short-lived. DuckDB's single-writer model means we serialise
writes; reads can be parallel.
"""
from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb


@dataclass(frozen=True)
class DuckDBConfig:
    """Immutable DuckDB connection settings."""

    path: Path
    read_only: bool = False

    @classmethod
    def from_env(cls) -> DuckDBConfig:
        raw = os.getenv("DUCKDB_PATH", "./data/analytics.duckdb")
        # If the env value is a container-only path, redirect to backend/data.
        if raw.startswith("/data/"):
            here = Path(__file__).resolve().parents[2]
            raw = str(here / "data" / Path(raw).name)
        return cls(path=Path(raw).expanduser().resolve())


class DuckDBAdapter:
    """Thin wrapper around the DuckDB Python API for analytics queries."""

    def __init__(self, config: DuckDBConfig) -> None:
        self._cfg = config
        self._cfg.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connection(self) -> Iterator[duckdb.DuckDBPyConnection]:
        conn = duckdb.connect(str(self._cfg.path), read_only=self._cfg.read_only)
        try:
            yield conn
        finally:
            conn.close()

    def execute(
        self,
        sql: str,
        params: list[Any] | tuple[Any, ...] | None = None,
    ) -> None:
        with self.connection() as conn:
            conn.execute(sql, params or [])

    def fetch_all(
        self,
        sql: str,
        params: list[Any] | tuple[Any, ...] | None = None,
    ) -> list[tuple[Any, ...]]:
        with self.connection() as conn:
            cur = conn.execute(sql, params or [])
            return list(cur.fetchall())

    def fetch_dicts(
        self,
        sql: str,
        params: list[Any] | tuple[Any, ...] | None = None,
    ) -> list[dict[str, Any]]:
        with self.connection() as conn:
            cur = conn.execute(sql, params or [])
            cols = [d[0] for d in cur.description] if cur.description else []
            return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]

    def table_exists(self, name: str) -> bool:
        rows = self.fetch_all(
            "SELECT count(*) FROM duckdb_tables() WHERE table_name = ?",
            (name,),
        )
        return bool(rows and rows[0][0])

    def list_tables(self) -> list[str]:
        rows = self.fetch_all(
            "SELECT table_name FROM duckdb_tables() ORDER BY table_name"
        )
        return [str(r[0]) for r in rows]

    def ping(self) -> bool:
        try:
            with self.connection() as conn:
                conn.execute("SELECT 1").fetchone()
                return True
        except duckdb.Error:
            return False

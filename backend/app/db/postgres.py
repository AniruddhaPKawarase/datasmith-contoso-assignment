"""PostgreSQL adapter for the Odoo ERP database.

Uses psycopg 3 (sync). For high-throughput query execution in Phase 5 we may
add an async pool, but introspection + small validation queries don't need it.
"""
from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.rows import dict_row


@dataclass(frozen=True)
class PostgresConfig:
    """Immutable Postgres connection settings.

    Built from env at startup; pass explicitly to keep tests deterministic.
    """

    host: str
    port: int
    database: str
    user: str
    password: str
    application_name: str = "scm-nl2sql"
    connect_timeout_s: int = 10

    @classmethod
    def from_env(cls) -> PostgresConfig:
        return cls(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "odoo"),
            user=os.getenv("POSTGRES_USER", "odoo"),
            password=os.getenv("POSTGRES_PASSWORD", "odoo_dev_pwd"),
        )

    @property
    def dsn(self) -> str:
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
            f"?application_name={self.application_name}"
            f"&connect_timeout={self.connect_timeout_s}"
        )


class PostgresAdapter:
    """Thin wrapper around psycopg for read-only introspection and query exec.

    All queries are parameterised — never f-string user input into SQL. The
    only exception is identifiers (table/column names) which we validate
    against an allow-list before formatting.
    """

    def __init__(self, config: PostgresConfig) -> None:
        self._cfg = config

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection[dict[str, Any]]]:
        """Yield a short-lived connection. Caller decides commit/rollback."""
        conn: psycopg.Connection[dict[str, Any]] = psycopg.connect(
            self._cfg.dsn, row_factory=dict_row
        )
        try:
            yield conn
        finally:
            conn.close()

    def fetch_all(
        self,
        sql: str,
        params: tuple[Any, ...] | dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a SELECT and return all rows as dicts."""
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())

    def ping(self) -> bool:
        """Cheap reachability check."""
        try:
            with self.connection() as conn, conn.cursor() as cur:
                cur.execute("SELECT 1")
                return cur.fetchone() is not None
        except psycopg.Error:
            return False

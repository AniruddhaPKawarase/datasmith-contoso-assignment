"""Database adapters: Postgres (Odoo) · DuckDB (analytics) · Redis (live state)."""

from app.db.duckdb import DuckDBAdapter, DuckDBConfig
from app.db.postgres import PostgresAdapter, PostgresConfig
from app.db.redis_adapter import RedisAdapter, RedisConfig

__all__ = [
    "DuckDBAdapter",
    "DuckDBConfig",
    "PostgresAdapter",
    "PostgresConfig",
    "RedisAdapter",
    "RedisConfig",
]

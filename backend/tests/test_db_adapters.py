"""Tests for the Postgres / DuckDB / Redis adapters.

DuckDB tests run against a tmp_path file; they don't need any service.
Postgres + Redis are exercised under @pytest.mark.integration only when a
live stack is up.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.db.duckdb import DuckDBAdapter, DuckDBConfig
from app.db.postgres import PostgresConfig
from app.db.redis_adapter import RedisConfig

# ───── DuckDB (unit, no service) ─────────────────────────────────────


def test_duckdb_config_redirects_container_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DUCKDB_PATH", "/data/analytics.duckdb")
    cfg = DuckDBConfig.from_env()
    # The container path /data/X should redirect to <backend>/data/X
    assert cfg.path.name == "analytics.duckdb"
    assert cfg.path.parent.name == "data"
    assert cfg.path.parent.parent.name == "backend"
    # Result must not be the bare Unix-style /data/... path
    assert not str(cfg.path).replace("\\", "/").startswith("/data/")


def test_duckdb_create_query_list(tmp_path: Path) -> None:
    cfg = DuckDBConfig(path=tmp_path / "t.duckdb")
    db = DuckDBAdapter(cfg)
    assert db.ping()
    db.execute("CREATE TABLE demo(id INTEGER, name VARCHAR)")
    db.execute("INSERT INTO demo VALUES (1, 'alpha'), (2, 'beta')")
    rows = db.fetch_all("SELECT id, name FROM demo ORDER BY id")
    assert rows == [(1, "alpha"), (2, "beta")]
    dicts = db.fetch_dicts("SELECT id, name FROM demo ORDER BY id")
    assert dicts == [{"id": 1, "name": "alpha"}, {"id": 2, "name": "beta"}]


def test_duckdb_table_exists(tmp_path: Path) -> None:
    cfg = DuckDBConfig(path=tmp_path / "t.duckdb")
    db = DuckDBAdapter(cfg)
    db.execute("CREATE TABLE foo(x INTEGER)")
    assert db.table_exists("foo") is True
    assert db.table_exists("bar") is False
    assert "foo" in db.list_tables()


# ───── Postgres config ────────────────────────────────────────────────


def test_postgres_config_dsn_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_HOST", "test-host")
    monkeypatch.setenv("POSTGRES_PORT", "5433")
    monkeypatch.setenv("POSTGRES_DB", "testdb")
    monkeypatch.setenv("POSTGRES_USER", "u")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p")
    cfg = PostgresConfig.from_env()
    assert "postgresql://u:p@test-host:5433/testdb" in cfg.dsn
    assert "application_name=scm-nl2sql" in cfg.dsn


# ───── Redis config ──────────────────────────────────────────────────


def test_redis_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in ("REDIS_HOST", "REDIS_PORT", "REDIS_DB", "REDIS_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    cfg = RedisConfig.from_env()
    assert cfg.host == "localhost"
    assert cfg.port == 6379
    assert cfg.password is None


def test_redis_config_with_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_PASSWORD", "s3cret")
    cfg = RedisConfig.from_env()
    assert cfg.password == "s3cret"


# ───── Integration (requires running docker stack) ───────────────────


@pytest.mark.integration
def test_postgres_live_ping() -> None:
    if not os.getenv("RUN_INTEGRATION"):
        pytest.skip("set RUN_INTEGRATION=1 to enable")
    from app.db.postgres import PostgresAdapter

    cfg = PostgresConfig.from_env()
    object.__setattr__(cfg, "host", "localhost")  # override container hostname
    assert PostgresAdapter(cfg).ping()


@pytest.mark.integration
def test_redis_live_ping() -> None:
    if not os.getenv("RUN_INTEGRATION"):
        pytest.skip("set RUN_INTEGRATION=1 to enable")
    from app.db.redis_adapter import RedisAdapter

    cfg = RedisConfig.from_env()
    object.__setattr__(cfg, "host", "localhost")
    adapter = RedisAdapter(cfg)
    try:
        assert adapter.ping()
    finally:
        adapter.close()

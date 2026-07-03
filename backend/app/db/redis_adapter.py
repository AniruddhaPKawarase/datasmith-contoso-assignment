"""Redis adapter for the real-time layer.

Holds live inventory snapshots (``stock_quant`` mirror) and small per-session
state (recent agent decisions, rate-limit counters). Keep the surface minimal:
we don't want agents to treat Redis as a generic key-value sandbox.

Key schema (versioned, prefixed):

    scm:v1:quant:<warehouse_id>:<product_id>       -> integer qty
    scm:v1:quant:idx:<warehouse_id>                -> set of product ids
    scm:v1:fx:<from_ccy>:<to_ccy>                  -> float rate (cached)
    scm:v1:session:<session_id>:turns              -> list of turn JSON
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import redis


@dataclass(frozen=True)
class RedisConfig:
    """Immutable Redis connection settings."""

    host: str
    port: int
    db: int
    password: str | None = None
    key_prefix: str = "scm:v1"
    socket_timeout_s: float = 3.0

    @classmethod
    def from_env(cls) -> RedisConfig:
        return cls(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            password=os.getenv("REDIS_PASSWORD") or None,
        )


class RedisAdapter:
    """Read/write helpers for the inventory + session namespace.

    Connection pooling is delegated to ``redis-py``'s ConnectionPool.
    """

    def __init__(self, config: RedisConfig) -> None:
        self._cfg = config
        self._client = redis.Redis(
            host=config.host,
            port=config.port,
            db=config.db,
            password=config.password,
            decode_responses=True,
            socket_timeout=config.socket_timeout_s,
        )

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except redis.RedisError:
            return False

    def close(self) -> None:
        self._client.close()

    # ── Inventory snapshot ────────────────────────────────────────────

    def set_quant(self, warehouse_id: int, product_id: int, quantity: float) -> None:
        """Mirror a single ``stock_quant`` row."""
        self._client.set(
            self._quant_key(warehouse_id, product_id), str(quantity)
        )
        self._client.sadd(self._quant_index_key(warehouse_id), str(product_id))

    def get_quant(self, warehouse_id: int, product_id: int) -> float | None:
        raw = self._client.get(self._quant_key(warehouse_id, product_id))
        return float(raw) if raw is not None else None

    def list_quants_for_warehouse(self, warehouse_id: int) -> dict[int, float]:
        product_ids = self._client.smembers(self._quant_index_key(warehouse_id))
        out: dict[int, float] = {}
        for pid_str in product_ids:
            pid = int(pid_str)
            qty = self.get_quant(warehouse_id, pid)
            if qty is not None:
                out[pid] = qty
        return out

    def reset_quants_for_warehouse(self, warehouse_id: int) -> None:
        product_ids = self._client.smembers(self._quant_index_key(warehouse_id))
        pipe = self._client.pipeline()
        for pid_str in product_ids:
            pipe.delete(self._quant_key(warehouse_id, int(pid_str)))
        pipe.delete(self._quant_index_key(warehouse_id))
        pipe.execute()

    # ── FX cache ──────────────────────────────────────────────────────

    def cache_fx(self, from_ccy: str, to_ccy: str, rate: float, ttl_s: int = 3600) -> None:
        self._client.setex(self._fx_key(from_ccy, to_ccy), ttl_s, str(rate))

    def get_fx(self, from_ccy: str, to_ccy: str) -> float | None:
        raw = self._client.get(self._fx_key(from_ccy, to_ccy))
        return float(raw) if raw is not None else None

    # ── key builders ──────────────────────────────────────────────────

    def _quant_key(self, warehouse_id: int, product_id: int) -> str:
        return f"{self._cfg.key_prefix}:quant:{warehouse_id}:{product_id}"

    def _quant_index_key(self, warehouse_id: int) -> str:
        return f"{self._cfg.key_prefix}:quant:idx:{warehouse_id}"

    def _fx_key(self, from_ccy: str, to_ccy: str) -> str:
        return f"{self._cfg.key_prefix}:fx:{from_ccy}:{to_ccy}"

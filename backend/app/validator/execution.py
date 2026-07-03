"""Stage 2 — execution validation against the live Postgres database.

We use ``EXPLAIN`` (not ``EXPLAIN ANALYZE``) by default — it catches table-
missing, column-missing, type-mismatch, and most planner errors without
actually executing the query. Phase 5's ``execute`` flag flips to real
execution when we want results too (e.g. for the orchestrator's final
response).

A statement timeout is applied via ``SET LOCAL statement_timeout`` so
runaway queries are killed within ``timeout_s`` seconds.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import psycopg

from app.agents.state import ValidationIssue
from app.db.postgres import PostgresAdapter

_PgConn = psycopg.Connection[Any]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExecutionResult:
    """Output of an execution validation pass."""

    issues: tuple[ValidationIssue, ...]
    rows: tuple[dict[str, Any], ...]
    row_count: int
    explained: bool


class ExecutionValidator:
    """Runs EXPLAIN or full execution against the configured Postgres DB."""

    def __init__(
        self,
        adapter: PostgresAdapter,
        *,
        timeout_s: int = 30,
        max_rows: int = 1000,
    ) -> None:
        self._db = adapter
        self._timeout_s = timeout_s
        self._max_rows = max_rows

    def validate(self, sql: str, *, execute: bool = False) -> ExecutionResult:
        if not sql.strip():
            return ExecutionResult(
                issues=(ValidationIssue(
                    kind="execution",
                    message="Empty SQL passed to execution validator.",
                    location="composer",
                ),),
                rows=(), row_count=0, explained=False,
            )
        # Drop trailing semicolon for EXPLAIN; psycopg dislikes ;-stacked stmts.
        clean = sql.rstrip().rstrip(";")
        try:
            with self._db.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"SET LOCAL statement_timeout = {self._timeout_s * 1000}"
                    )
                if execute:
                    return self._execute(conn, clean)
                return self._explain(conn, clean)
        except psycopg.errors.QueryCanceled as exc:
            return ExecutionResult(
                issues=(ValidationIssue(
                    kind="execution",
                    message=f"Query exceeded {self._timeout_s}s timeout: {exc}",
                    location="composer",
                    suggestion="Add WHERE/LIMIT to constrain the result set.",
                ),),
                rows=(), row_count=0, explained=False,
            )
        except psycopg.Error as exc:
            return ExecutionResult(
                issues=(ValidationIssue(
                    kind="execution",
                    message=str(exc).splitlines()[0][:500],
                    location=self._guess_location(sql, str(exc)),
                    suggestion=self._suggest(str(exc)),
                ),),
                rows=(), row_count=0, explained=False,
            )

    # ── helpers ───────────────────────────────────────────────────────

    def _explain(self, conn: _PgConn, clean_sql: str) -> ExecutionResult:
        with conn.cursor() as cur:
            cur.execute(f"EXPLAIN {clean_sql}")
            # Drain the plan rows so the cursor closes cleanly.
            _ = list(cur.fetchall())
        return ExecutionResult(issues=(), rows=(), row_count=0, explained=True)

    def _execute(self, conn: _PgConn, clean_sql: str) -> ExecutionResult:
        with conn.cursor() as cur:
            cur.execute(clean_sql)
            fetched_raw = list(cur.fetchmany(self._max_rows))
        # If dict_row is the factory, fetched_raw is list[dict]; if not we wrap.
        fetched: list[dict[str, Any]] = [
            dict(r) if not isinstance(r, dict) else r for r in fetched_raw
        ]
        return ExecutionResult(
            issues=(),
            rows=tuple(fetched),
            row_count=len(fetched),
            explained=True,
        )

    @staticmethod
    def _guess_location(sql: str, error_msg: str) -> str:
        """Find the `-- domain=X` marker closest to the table name in the error."""
        # Look for "table X" or "column X" in the error and find the nearest
        # marker comment in the SQL.
        marker = "-- domain="
        if marker not in sql:
            return "composer"
        # Find the domain marker for each fragment and pick the one closest
        # to a table mentioned in the error.
        lines = sql.splitlines()
        domains: list[tuple[int, str]] = []
        for i, line in enumerate(lines):
            stripped = line.strip().lower()
            if stripped.startswith(marker.lower()):
                domains.append((i, stripped[len(marker):].strip()))
        if not domains:
            return "composer"
        # If error mentions a specific table name, locate it.
        err_lower = error_msg.lower()
        for i, _line in enumerate(lines):
            if any(tok in err_lower for tok in (
                "relation", "column", "table", "function"
            )):
                # walk forward until the next domain marker
                for di, dom in reversed(domains):
                    if di <= i:
                        return dom
        return domains[-1][1]

    @staticmethod
    def _suggest(error_msg: str) -> str:
        msg = error_msg.lower()
        if "relation" in msg and "does not exist" in msg:
            return "Check the table name spelling; ensure it's in the agent's domain."
        if "column" in msg and "does not exist" in msg:
            return "Verify the column name against the schema metadata."
        if "operator does not exist" in msg:
            return "Check data-type compatibility; an explicit CAST may be needed."
        if "missing from-clause entry" in msg:
            return (
                "An alias is being referenced outside its CTE / subquery scope. "
                "Move the predicate inside the CTE that defines the alias."
            )
        if "syntax error" in msg:
            return "Re-check the SQL for missing commas or unbalanced parens."
        return ""

"""Deterministic SQL Composer.

Takes the list of ``AgentOutput`` rows produced by the per-domain agents
and assembles them into ONE PostgreSQL statement.

Strategy
--------
1. **0 fragments** → return empty SQL; orchestrator will surface an error.
2. **1 fragment**  → pass through verbatim.
3. **2+ fragments** → wrap each fragment in a named CTE and combine the
   CTEs. The combination strategy depends on whether the agents share a
   join key:

   * If we can find a common key (via the FK graph + agent-reported
     ``used_tables``), produce::

         WITH inv_q AS (...),
              fin_q AS (...)
         SELECT * FROM inv_q
         INNER JOIN fin_q USING (<shared_key>);

   * Otherwise, the user is asking for *parallel summaries* (e.g.
     "total revenue vs total inventory value"). Produce::

         WITH inv_q AS (...),
              fin_q AS (...)
         SELECT inv_q.*, fin_q.*
         FROM inv_q CROSS JOIN fin_q;

This is the path that fixes Phase 4's Query 4 regression — UNION ALL
of mismatched columns is replaced with a CROSS-JOIN summary that the
RBAC rewriter can scope correctly.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import sqlglot
from sqlglot import exp

from app.agents.state import AgentOutput
from app.schema.joins import JoinGraph

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ComposerResult:
    """Structured Composer output."""

    sql: str
    cte_names: tuple[str, ...]
    join_strategy: str        # "passthrough" | "cross_join" | "inner_join:<key>" | "noop"
    shared_key: str = ""
    notes: str = ""


class Composer:
    """Deterministic, AST-aware Composer.

    The Composer accepts the FK ``JoinGraph`` built from Phase 2 so it
    can discover shared columns (e.g. ``product_id``, ``company_id``)
    between two agents' table sets and produce a real INNER JOIN.
    """

    def __init__(self, *, join_graph: JoinGraph | None = None) -> None:
        self._joins = join_graph

    def compose(self, outputs: tuple[AgentOutput, ...]) -> ComposerResult:
        non_empty = tuple(o for o in outputs if o.sql.strip())
        if not non_empty:
            return ComposerResult(
                sql="", cte_names=(), join_strategy="noop",
                notes="No domain agent produced SQL.",
            )
        if len(non_empty) == 1:
            out = non_empty[0]
            return ComposerResult(
                sql=_finalise(out.sql),
                cte_names=(),
                join_strategy="passthrough",
                notes=f"Single-domain pass-through ({out.domain.value}).",
            )
        return self._compose_multi(non_empty)

    # ── private ───────────────────────────────────────────────────────

    def _compose_multi(self, outputs: tuple[AgentOutput, ...]) -> ComposerResult:
        ctes: list[tuple[str, exp.Expression]] = []
        cte_names: list[str] = []
        for o in outputs:
            cte_name = f"q_{o.domain.value}"
            try:
                parsed = sqlglot.parse_one(o.sql, read="postgres")
            except sqlglot.errors.ParseError as exc:
                logger.warning("Composer could not parse %s SQL: %s", o.domain.value, exc)
                return ComposerResult(
                    sql="", cte_names=(),
                    join_strategy="noop",
                    notes=f"Parse failure in {o.domain.value} fragment: {exc}",
                )
            if parsed is None:
                return ComposerResult(
                    sql="", cte_names=(),
                    join_strategy="noop",
                    notes=f"Empty parse for {o.domain.value} fragment.",
                )
            ctes.append((cte_name, parsed))  # type: ignore[arg-type]
            cte_names.append(cte_name)

        shared_key = self._detect_shared_key(outputs)

        # Only INNER JOIN if EVERY CTE actually projects the shared key.
        # Otherwise the USING clause references a column that doesn't exist
        # in one of the CTEs' output (the Phase 7 Turn 1 regression).
        if shared_key:
            for _, ast in ctes:
                cols = _output_columns(ast)
                if cols and shared_key not in cols:
                    shared_key = ""
                    break

        # Build the CTE WITH clause.
        with_parts = ",\n".join(
            f"  {name} AS (\n    {_compact(_sql_for(ast))}\n  )"
            for name, ast in ctes
        )

        if shared_key:
            select_clause = self._cross_select_clause(ctes, shared_key=shared_key)
            join_clause = " INNER JOIN ".join(
                f"{n}" if i == 0 else f"{n} USING ({shared_key})"
                for i, n in enumerate(cte_names)
            )
            sql = f"WITH\n{with_parts}\nSELECT {select_clause}\nFROM {join_clause};"
            return ComposerResult(
                sql=sql,
                cte_names=tuple(cte_names),
                join_strategy=f"inner_join:{shared_key}",
                shared_key=shared_key,
                notes=f"Joined {len(cte_names)} CTEs on {shared_key}.",
            )

        # CROSS JOIN of single-row summaries.
        select_clause = self._cross_select_clause(ctes, shared_key=None)
        cross = " CROSS JOIN ".join(cte_names)
        sql = f"WITH\n{with_parts}\nSELECT {select_clause}\nFROM {cross};"
        return ComposerResult(
            sql=sql,
            cte_names=tuple(cte_names),
            join_strategy="cross_join",
            notes="No shared key found — CROSS JOIN of per-domain summaries.",
        )

    def _detect_shared_key(self, outputs: tuple[AgentOutput, ...]) -> str:
        """Pick a column that appears (as an FK source) in every output."""
        if self._joins is None:
            return ""
        candidate_cols: list[set[str]] = []
        for o in outputs:
            cols: set[str] = set()
            for tbl in o.used_tables:
                cols.update(self._joins.outgoing_columns(tbl))
            candidate_cols.append(cols)
        common = set.intersection(*candidate_cols) if candidate_cols else set()
        # Prefer well-known business keys.
        for preferred in ("company_id", "product_id", "partner_id"):
            if preferred in common:
                return preferred
        return next(iter(sorted(common)), "")

    def _cross_select_clause(
        self,
        ctes: list[tuple[str, exp.Expression]],
        *,
        shared_key: str | None,
    ) -> str:
        cols: list[str] = []
        seen: set[str] = set()
        if shared_key:
            cols.append(shared_key)
            seen.add(shared_key)
        for name, ast in ctes:
            for projection in _output_columns(ast):
                if projection in seen:
                    aliased = f"{name}.{projection} AS {name}_{projection}"
                    cols.append(aliased)
                else:
                    cols.append(f"{name}.{projection}")
                    seen.add(projection)
        return ", ".join(cols) if cols else "*"


# ── helpers ──────────────────────────────────────────────────────────


_WS_RE = re.compile(r"\s+")


def _finalise(sql: str) -> str:
    sql = sql.strip().rstrip(";").strip()
    return sql + ";"


def _compact(sql: str) -> str:
    return _WS_RE.sub(" ", sql).strip()


def _sql_for(ast: exp.Expression) -> str:
    return ast.sql(dialect="postgres")


def _output_columns(ast: exp.Expression) -> list[str]:
    """Best-effort list of the SELECT clause output column names."""
    if not isinstance(ast, exp.Select):
        # If the inner statement is a CTE / Union, fall back to "*".
        return []
    out: list[str] = []
    for proj in ast.expressions:
        alias = proj.alias_or_name
        if alias and alias != "*" and alias not in out:
            out.append(alias)
    return out

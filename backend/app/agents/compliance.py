"""Compliance — RBAC predicate injection + audit logging (Phase 5: AST-based).

Compliance is *cross-cutting* (Objective #7 in the abstract). It does not
generate SQL from scratch; instead it runs **after** the Composer and:

1. Injects row-level security predicates into the composed SQL based on
   the calling user's company / warehouse / role.
2. Records a structured audit entry into the MessageLog so every query
   that touches the DB is traceable.

Phase 5 replaces the regex-based string surgery from Phase 4 with sqlglot
AST manipulation. Each occurrence of a table that carries ``company_id``
or ``warehouse_id`` columns gets its own predicate added to the *enclosing*
SELECT's WHERE clause — that means a CTE keeps its RBAC inside the CTE,
and a top-level SELECT keeps it at the top level. This fixes the Phase 4
Query 4 regression where ``aml.company_id`` was injected at the outer
level even though ``aml`` was only visible inside a CTE.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import sqlglot
from sqlglot import exp

from app.agents.messages import AgentMessage, MessageKind, MessageLog
from app.schema.metadata import SchemaMetadata

logger = logging.getLogger(__name__)

_COMPANY_COL = "company_id"
_WAREHOUSE_COL = "warehouse_id"


@dataclass(frozen=True)
class ComplianceContext:
    """Per-request authorisation context."""

    user_id: int
    user_role: str
    company_ids: tuple[int, ...]
    warehouse_ids: tuple[int, ...]
    bypass: bool = False


@dataclass(frozen=True)
class ComplianceDecision:
    """What Compliance did to the SQL and why."""

    sql: str
    predicates_added: tuple[str, ...]
    bypassed: bool
    notes: str = ""


class ComplianceProcessor:
    """AST-aware post-Composer RBAC + audit processor.

    Build once with the schema metadata (cheap; just walks once over the
    table list to learn which tables carry the relevant columns), then
    ``apply`` per request.
    """

    def __init__(self, metadata: SchemaMetadata) -> None:
        self._meta = metadata
        self._has_company: frozenset[str] = frozenset(
            t.name for t in metadata.tables
            if any(c.name == _COMPANY_COL for c in t.columns)
        )
        self._has_warehouse: frozenset[str] = frozenset(
            t.name for t in metadata.tables
            if any(c.name == _WAREHOUSE_COL for c in t.columns)
        )

    def apply(
        self,
        sql: str,
        context: ComplianceContext,
        *,
        message_log: MessageLog | None = None,
        correlation_id: str = "",
    ) -> ComplianceDecision:
        """Return a (possibly-rewritten) SQL with RBAC predicates injected."""
        if context.bypass:
            self._audit(
                message_log, correlation_id, context,
                payload={"bypass": True, "sql_length": len(sql)},
            )
            return ComplianceDecision(
                sql=sql, predicates_added=(), bypassed=True,
                notes="Compliance bypassed (superuser).",
            )

        if not sql.strip():
            return ComplianceDecision(sql=sql, predicates_added=(), bypassed=False)

        try:
            tree = sqlglot.parse_one(sql, read="postgres")
        except sqlglot.errors.ParseError as exc:
            logger.warning("Compliance could not parse SQL: %s", exc)
            return ComplianceDecision(
                sql=sql, predicates_added=(), bypassed=False,
                notes=f"Parse failure, RBAC not applied: {exc}",
            )

        predicates_added: list[str] = []
        # Each SELECT (top-level + CTEs + sub-queries) is processed
        # independently. RBAC is scoped to the tables visible inside that
        # SELECT — no leakage across scopes.
        for select_node in tree.find_all(exp.Select):
            new_predicates = self._inject_into(select_node, context)
            predicates_added.extend(new_predicates)

        new_sql = tree.sql(dialect="postgres") + ";"
        self._audit(
            message_log, correlation_id, context,
            payload={
                "predicates_added": predicates_added,
                "num_scopes_modified": sum(1 for _ in tree.find_all(exp.Select)),
            },
        )
        return ComplianceDecision(
            sql=new_sql,
            predicates_added=tuple(predicates_added),
            bypassed=False,
            notes=f"Injected {len(predicates_added)} scoped RBAC predicate(s).",
        )

    # ── private ───────────────────────────────────────────────────────

    def _inject_into(
        self,
        select_node: exp.Select,
        ctx: ComplianceContext,
    ) -> list[str]:
        """Add RBAC predicates to this SELECT's WHERE for in-scope tables."""
        added: list[str] = []
        # Map alias -> table_name for every table directly referenced by
        # this SELECT (NOT recursing into sub-queries — those have their
        # own scope and will be visited separately by find_all).
        alias_to_table = _direct_tables_in(select_node)

        for alias, table_name in alias_to_table.items():
            if table_name in self._has_company and ctx.company_ids:
                self._and_predicate(
                    select_node, alias, _COMPANY_COL, ctx.company_ids
                )
                added.append(
                    f"{alias}.{_COMPANY_COL} IN ({_int_list(ctx.company_ids)})"
                )
            if table_name in self._has_warehouse and ctx.warehouse_ids:
                self._and_predicate(
                    select_node, alias, _WAREHOUSE_COL, ctx.warehouse_ids
                )
                added.append(
                    f"{alias}.{_WAREHOUSE_COL} IN ({_int_list(ctx.warehouse_ids)})"
                )
        return added

    @staticmethod
    def _and_predicate(
        select_node: exp.Select,
        alias: str,
        column: str,
        values: tuple[int, ...],
    ) -> None:
        """AND a new predicate into the SELECT's WHERE clause (creating one if absent)."""
        in_predicate = exp.In(
            this=exp.column(column, table=alias),
            expressions=[exp.Literal.number(v) for v in values],
        )
        existing = select_node.args.get("where")
        if existing is not None and isinstance(existing, exp.Where):
            existing.set(
                "this",
                exp.And(this=existing.this, expression=in_predicate),
            )
        else:
            select_node.where(in_predicate, copy=False)

    @staticmethod
    def _audit(
        log: MessageLog | None,
        correlation_id: str,
        ctx: ComplianceContext,
        *,
        payload: dict[str, object],
    ) -> None:
        if log is None or not correlation_id:
            return
        log.append(
            AgentMessage.make(
                correlation_id=correlation_id,
                kind=MessageKind.VALIDATION,
                from_agent="compliance",
                to_agent="orchestrator",
                payload={
                    "user_id": ctx.user_id,
                    "user_role": ctx.user_role,
                    "company_ids": list(ctx.company_ids),
                    "warehouse_ids": list(ctx.warehouse_ids),
                    **payload,
                },
            )
        )


# ── helpers ───────────────────────────────────────────────────────────


def _direct_tables_in(select_node: exp.Select) -> dict[str, str]:
    """Map ``alias -> table_name`` for every table directly inside this SELECT.

    "Directly" means in the FROM clause or any JOIN of *this* SELECT — a
    nested sub-query is a separate scope and is handled by its own
    ``find_all(Select)`` visit.
    """
    alias_to_table: dict[str, str] = {}
    for tbl in select_node.find_all(exp.Table):
        if _scope_select_for(tbl) is select_node:
            name = tbl.name.lower()
            alias = tbl.alias_or_name
            alias_to_table[alias] = name
    return alias_to_table


def _scope_select_for(node: exp.Expression) -> exp.Select | None:
    """Walk up the AST and return the nearest enclosing SELECT."""
    parent_attr = node.parent
    cur: exp.Expression | None = parent_attr if isinstance(parent_attr, exp.Expression) else None
    while cur is not None:
        if isinstance(cur, exp.Select):
            return cur
        nxt = cur.parent
        cur = nxt if isinstance(nxt, exp.Expression) else None
    return None


def _int_list(ids: tuple[int, ...]) -> str:
    return ", ".join(str(int(i)) for i in ids)

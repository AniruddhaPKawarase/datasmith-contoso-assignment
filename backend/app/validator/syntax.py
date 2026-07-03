"""Stage 1 — syntax validation via sqlglot.

Goals (cheap, no DB hit):
1. Parse the SQL string with the postgres dialect.
2. Reject statements that are NOT a single SELECT/WITH (no DDL/DML).
3. Verify every table referenced is in the allow-list (the union of all
   visible-table sets across active domain agents).
4. Flag obviously unsafe constructs (semicolon-stacked statements,
   DROP/TRUNCATE/ALTER, COPY-to-file).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import cast

import sqlglot
from sqlglot import exp

from app.agents.state import ValidationIssue

logger = logging.getLogger(__name__)


_FORBIDDEN_NODES: tuple[type[exp.Expression], ...] = (
    exp.Drop,
    exp.Alter,
    exp.AlterColumn,
    exp.TruncateTable,
    exp.Update,
    exp.Delete,
    exp.Insert,
    exp.Create,
)


@dataclass(frozen=True)
class SyntaxResult:
    """Structured output of syntax validation."""

    issues: tuple[ValidationIssue, ...]
    parsed_ok: bool
    referenced_tables: tuple[str, ...]


class SyntaxValidator:
    """Pure-Python validator — no DB connection required.

    ``allowed_tables`` is typically the union of the active agents'
    ``visible_tables`` sets. Pass ``None`` to skip the allow-list check
    (used in tests where we only care about parse correctness).
    """

    def __init__(self, *, allowed_tables: frozenset[str] | None = None) -> None:
        self._allowed = allowed_tables

    def validate(self, sql: str) -> SyntaxResult:
        issues: list[ValidationIssue] = []
        if not sql.strip():
            issues.append(
                ValidationIssue(
                    kind="syntax",
                    message="Empty SQL passed to validator.",
                    location="composer",
                )
            )
            return SyntaxResult(issues=tuple(issues), parsed_ok=False, referenced_tables=())

        try:
            statements = sqlglot.parse(sql, read="postgres")
        except sqlglot.errors.ParseError as exc:
            issues.append(
                ValidationIssue(
                    kind="syntax",
                    message=f"Could not parse SQL: {exc}",
                    location="composer",
                    suggestion="Check for missing FROM, dangling commas, or unbalanced parens.",
                )
            )
            return SyntaxResult(issues=tuple(issues), parsed_ok=False, referenced_tables=())

        non_null: list[exp.Expression] = []
        for s in statements:
            if s is not None:
                non_null.append(cast(exp.Expression, s))
        if len(non_null) != 1:
            issues.append(
                ValidationIssue(
                    kind="syntax",
                    message=(
                        f"Expected exactly one statement, found {len(non_null)}. "
                        "Semicolon-stacked statements are not supported."
                    ),
                    location="composer",
                )
            )
            return SyntaxResult(issues=tuple(issues), parsed_ok=False, referenced_tables=())

        ast: exp.Expression = non_null[0]
        # Reject mutations / DDL.
        for forbidden in _FORBIDDEN_NODES:
            if any(ast.find_all(forbidden)):
                issues.append(
                    ValidationIssue(
                        kind="syntax",
                        message=(
                            f"Forbidden statement type: {forbidden.__name__}. "
                            "Only SELECT / WITH queries are allowed."
                        ),
                        location="composer",
                    )
                )

        # Collect CTE-defined aliases — those are NOT real tables and
        # must be exempt from the allow-list check.
        cte_aliases: set[str] = set()
        for cte in ast.find_all(exp.CTE):
            alias_node = cte.args.get("alias")
            if alias_node is None:
                continue
            alias_name = (
                alias_node.this.name
                if hasattr(alias_node, "this") and alias_node.this is not None
                else alias_node.name
            )
            if alias_name:
                cte_aliases.add(alias_name.lower())

        # Collect referenced tables. sqlglot's exp.Table nodes carry the name.
        referenced: list[str] = []
        for tbl in ast.find_all(exp.Table):
            name = tbl.name
            lname = name.lower() if name else ""
            if not lname or lname in cte_aliases:
                continue
            if lname not in referenced:
                referenced.append(lname)

        if self._allowed is not None:
            out_of_set = [t for t in referenced if t not in self._allowed]
            if out_of_set:
                issues.append(
                    ValidationIssue(
                        kind="syntax",
                        message=(
                            f"SQL references {out_of_set} which is/are not in "
                            "any active agent's visible-tables set."
                        ),
                        location="composer",
                        suggestion=(
                            "Make sure the Router selected the right domains and "
                            "that the table names are correct."
                        ),
                    )
                )

        return SyntaxResult(
            issues=tuple(issues),
            parsed_ok=not issues,
            referenced_tables=tuple(referenced),
        )

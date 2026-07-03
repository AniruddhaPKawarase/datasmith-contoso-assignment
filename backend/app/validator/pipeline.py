"""End-to-end three-stage SQL validation pipeline."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.agents.state import ValidationIssue
from app.validator.business import BusinessRuleValidator
from app.validator.execution import ExecutionValidator
from app.validator.syntax import SyntaxValidator

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ValidationReport:
    """Combined output of the three validator stages."""

    issues: tuple[ValidationIssue, ...]
    referenced_tables: tuple[str, ...]
    rows: tuple[dict[str, Any], ...]
    row_count: int
    syntax_ok: bool
    execution_ok: bool
    business_ok: bool

    @property
    def ok(self) -> bool:
        return not self.issues


class ValidationPipeline:
    """Runs syntax → execution → business in order, short-circuits on errors.

    Behaviour:
    * If syntax fails, neither execution nor business runs.
    * Execution always runs in EXPLAIN-only mode by default; pass
      ``execute=True`` to also retrieve rows for the business-rule stage.
    * Business rules run only when ``execute=True`` (they need rows).
    """

    def __init__(
        self,
        *,
        syntax: SyntaxValidator,
        execution: ExecutionValidator,
        business: BusinessRuleValidator | None = None,
    ) -> None:
        self._syntax = syntax
        self._execution = execution
        self._business = business or BusinessRuleValidator()

    def run(
        self,
        sql: str,
        *,
        execute: bool = False,
        intent: str = "",
    ) -> ValidationReport:
        syn = self._syntax.validate(sql)
        if not syn.parsed_ok:
            return ValidationReport(
                issues=syn.issues,
                referenced_tables=syn.referenced_tables,
                rows=(), row_count=0,
                syntax_ok=False, execution_ok=False, business_ok=False,
            )

        exe = self._execution.validate(sql, execute=execute)
        if exe.issues:
            return ValidationReport(
                issues=syn.issues + exe.issues,
                referenced_tables=syn.referenced_tables,
                rows=(), row_count=0,
                syntax_ok=True, execution_ok=False, business_ok=False,
            )

        biz_issues: tuple[ValidationIssue, ...] = ()
        if execute:
            biz = self._business.validate(exe.rows, intent=intent)
            biz_issues = biz.issues

        return ValidationReport(
            issues=syn.issues + exe.issues + biz_issues,
            referenced_tables=syn.referenced_tables,
            rows=exe.rows,
            row_count=exe.row_count,
            syntax_ok=True,
            execution_ok=True,
            business_ok=not biz_issues,
        )

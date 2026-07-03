"""Three-stage SQL validation pipeline (Phase 5).

Stage 1 — syntax via sqlglot (no DB hit, fast)
Stage 2 — execution via Postgres EXPLAIN with a 30 s timeout
Stage 3 — business-rule sanity checks (row counts, value ranges)

Each stage returns ``ValidationIssue`` records that the orchestrator routes
back to the originating agent (self-correction loop, max 3 attempts).
"""
from app.validator.business import BusinessRuleValidator
from app.validator.execution import ExecutionValidator
from app.validator.pipeline import ValidationPipeline, ValidationReport
from app.validator.syntax import SyntaxValidator

__all__ = [
    "BusinessRuleValidator",
    "ExecutionValidator",
    "SyntaxValidator",
    "ValidationPipeline",
    "ValidationReport",
]

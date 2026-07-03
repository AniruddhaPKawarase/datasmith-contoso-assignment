"""Evaluation utilities — metric implementations + result comparison.

Per docs/eval/EVALUATION_FRAMEWORK.md sections 2-4:
    EX  -- Execution Accuracy   (result-set equality with NULL semantics)
    VES -- Valid Efficiency Score   (EX * relative-runtime factor)
    EM  -- Exact Match  (sqlglot-canonical normalisation)
"""

from app.eval.metrics import (
    compute_em,
    compute_ex,
    compute_soft_ex,
    compute_ves,
    result_sets_equal,
)

__all__ = [
    "compute_em",
    "compute_ex",
    "compute_soft_ex",
    "compute_ves",
    "result_sets_equal",
]

"""Stage 3 — business-rule sanity checks.

These are cheap heuristics that catch the common ways a syntactically and
semantically valid query is still *wrong* — empty results when the user
clearly expected data, absurd row counts, negative quantities, etc.

For Phase 5 we ship a small set; the abstract calls for more rules in
the final eval (see Objective #2 of the validator pipeline).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.agents.state import ValidationIssue


@dataclass(frozen=True)
class BusinessResult:
    issues: tuple[ValidationIssue, ...]


class BusinessRuleValidator:
    """Applies sanity-check rules to executed query results.

    Parameters
    ----------
    expect_rows :
        If True, an empty result set is flagged as suspicious.
    max_row_warning :
        Above this row count we emit a warning (not a hard reject).
    """

    def __init__(
        self,
        *,
        expect_rows: bool = True,
        max_row_warning: int = 100_000,
    ) -> None:
        self._expect_rows = expect_rows
        self._max_row_warning = max_row_warning

    def validate(
        self,
        rows: tuple[dict[str, Any], ...],
        *,
        intent: str = "",
    ) -> BusinessResult:
        issues: list[ValidationIssue] = []

        if self._expect_rows and not rows and intent == "supply_chain_question":
            issues.append(
                ValidationIssue(
                    kind="business_rule",
                    message="Query returned zero rows but a real result was expected.",
                    location="composer",
                    suggestion=(
                        "Likely cause: an overly-tight WHERE clause, wrong "
                        "JOIN key, or a temporal filter outside the demo "
                        "data range."
                    ),
                )
            )

        if len(rows) > self._max_row_warning:
            issues.append(
                ValidationIssue(
                    kind="business_rule",
                    message=(
                        f"Result set has {len(rows)} rows — exceeds the "
                        f"{self._max_row_warning} sanity ceiling."
                    ),
                    location="composer",
                    suggestion="Add aggregation or LIMIT to constrain the result.",
                )
            )

        # Spot-check for absurd numeric values in obvious money / qty cols.
        for row in rows[:50]:
            for col, value in row.items():
                if not isinstance(value, int | float):
                    continue
                col_lower = col.lower()
                if ("qty" in col_lower or "quantity" in col_lower) and value < 0:
                    issues.append(
                        ValidationIssue(
                            kind="business_rule",
                            message=(
                                f"Column `{col}` returned negative quantity "
                                f"{value}; quantities should be non-negative."
                            ),
                            location="composer",
                        )
                    )
                    break
                if ("amount" in col_lower or "price" in col_lower) and abs(value) > 1e12:
                    issues.append(
                        ValidationIssue(
                            kind="business_rule",
                            message=(
                                f"Column `{col}` returned implausibly large "
                                f"value {value:.2g}."
                            ),
                            location="composer",
                        )
                    )
                    break

        return BusinessResult(issues=tuple(issues))

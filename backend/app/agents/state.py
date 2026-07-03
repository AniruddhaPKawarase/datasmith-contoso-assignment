"""LangGraph state schema for the NL-to-SQL pipeline.

LangGraph nodes are pure functions ``state -> partial_state`` operating on a
TypedDict. We model the *whole* lifecycle of a single query (and its
self-correction attempts) inside one ``AgentState``. Multi-turn context is
attached as ``history`` (compressed older turns + last 5 active turns).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypedDict

from app.schema.domains import Domain
from app.temporal import TemporalContext


@dataclass(frozen=True)
class SubQuery:
    """One domain agent's slice of the user query.

    Filled by the Router/Planner, consumed by the matching domain agent.
    """

    domain: Domain
    natural_language: str               # the rewritten sub-question for this agent
    rationale: str = ""                 # why the Router routed it here
    requires_tables: tuple[str, ...] = ()  # optional schema hint


@dataclass(frozen=True)
class ValidationIssue:
    """One problem found by a validator pass."""

    kind: str                           # "syntax" | "execution" | "business_rule"
    message: str
    location: str = ""                  # e.g. "composer" | a domain name
    suggestion: str = ""


@dataclass(frozen=True)
class AgentOutput:
    """One domain agent's contribution to the final SQL."""

    domain: Domain
    sql: str
    confidence: float                   # 0..1
    used_tables: tuple[str, ...] = ()
    notes: str = ""


class AgentState(TypedDict, total=False):
    """LangGraph state. All fields are optional — nodes fill in what they own.

    Convention: never mutate; nodes return a new dict of only the fields they
    changed (LangGraph merges with the previous state).
    """

    # ── Input ─────────────────────────────────────────────────────────
    query: str
    session_id: str
    user_role: str
    user_company_ids: tuple[int, ...]
    user_warehouse_ids: tuple[int, ...]

    # ── Routing output ────────────────────────────────────────────────
    intent: str                          # see Router._ALLOWED_INTENTS
    domains: tuple[Domain, ...]
    sub_queries: tuple[SubQuery, ...]
    router_reasoning: str

    # ── Generation output (per-domain) ────────────────────────────────
    agent_outputs: tuple[AgentOutput, ...]

    # ── Composition ───────────────────────────────────────────────────
    composed_sql: str

    # ── Validation + correction ───────────────────────────────────────
    validation_issues: tuple[ValidationIssue, ...]
    attempt: int                         # 1..MAX_ATTEMPTS

    # ── Execution ─────────────────────────────────────────────────────
    rows: tuple[dict[str, Any], ...]
    row_count: int

    # ── Final response ────────────────────────────────────────────────
    explanation: str
    confidence: float
    final_error: str

    # ── Multi-turn context ────────────────────────────────────────────
    history_summary: str                 # compressed summary of older turns
    recent_turns: tuple[dict[str, Any], ...]  # last N turn dicts

    # ── Temporal context (Phase 6) ────────────────────────────────────
    temporal: TemporalContext

    # ── Ambiguity (Phase 6) ───────────────────────────────────────────
    clarification_question: str


def fresh_state(
    *,
    query: str,
    session_id: str,
    user_role: str = "analyst",
    user_company_ids: tuple[int, ...] = (),
    user_warehouse_ids: tuple[int, ...] = (),
    history_summary: str = "",
    recent_turns: tuple[dict[str, Any], ...] = (),
) -> AgentState:
    """Construct a starting state for a new query."""
    return AgentState(
        query=query,
        session_id=session_id,
        user_role=user_role,
        user_company_ids=user_company_ids,
        user_warehouse_ids=user_warehouse_ids,
        intent="",
        domains=(),
        sub_queries=(),
        router_reasoning="",
        agent_outputs=(),
        composed_sql="",
        validation_issues=(),
        attempt=0,
        rows=(),
        row_count=0,
        explanation="",
        confidence=0.0,
        final_error="",
        history_summary=history_summary,
        recent_turns=recent_turns,
        temporal=TemporalContext(),
        clarification_question="",
    )


@dataclass(frozen=True)
class OrchestratorLimits:
    """Configurable bounds for the LangGraph pipeline."""

    max_correction_attempts: int = 3
    sql_timeout_s: int = 30
    max_schema_tokens_per_agent: int = 4000
    extra: dict[str, int] = field(default_factory=dict)

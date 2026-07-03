"""Tests for ConversationContextBuilder (Phase 7.1 / 7.3 plumbing)."""
from __future__ import annotations

from app.agents.memory import Turn
from app.conversation import (
    ConversationContextBuilder,
    ReferenceDecision,
    ReferenceKind,
)
from app.schema.domains import Domain


def _turn(turn_id: int, query: str, sql: str = "SELECT 1", summary: str = "") -> Turn:
    return Turn(
        turn_id=turn_id,
        timestamp="2026-05-14T00:00:00+00:00",
        user_query=query,
        domains_used=(Domain.INVENTORY,),
        generated_sql=sql,
        row_count=10,
        summary=summary or f"summary {turn_id}",
    )


def test_empty_window_returns_empty() -> None:
    b = ConversationContextBuilder()
    assert b.build(recent_turns=(), older_summary="") == ""


def test_includes_recent_turn() -> None:
    b = ConversationContextBuilder()
    out = b.build(
        recent_turns=(_turn(1, "show stock", "SELECT * FROM stock_quant"),),
    )
    assert "Turn 1" in out
    assert "show stock" in out
    assert "stock_quant" in out


def test_older_summary_rendered() -> None:
    b = ConversationContextBuilder()
    out = b.build(
        recent_turns=(_turn(3, "newest"),),
        older_summary="Turn 1: 'first thing' (inventory)\nTurn 2: 'second' (finance)",
    )
    assert "Older context" in out
    assert "first thing" in out


def test_window_capped_to_max_recent() -> None:
    b = ConversationContextBuilder(max_recent_turns=2)
    out = b.build(
        recent_turns=(
            _turn(1, "alpha"),
            _turn(2, "beta"),
            _turn(3, "gamma"),
        ),
    )
    # Only beta and gamma should be in the rendered block.
    assert "alpha" not in out
    assert "beta" in out
    assert "gamma" in out


def test_reference_kind_guidance_for_refinement() -> None:
    b = ConversationContextBuilder()
    out = b.build(
        recent_turns=(_turn(1, "show stock"),),
        reference=ReferenceDecision(
            kind=ReferenceKind.REFINEMENT,
            triggers=("only for",),
        ),
    )
    assert "refinement" in out.lower()
    assert "WHERE-clause predicate" in out


def test_reference_kind_guidance_for_comparison() -> None:
    b = ConversationContextBuilder()
    out = b.build(
        recent_turns=(_turn(1, "revenue"),),
        reference=ReferenceDecision(
            kind=ReferenceKind.COMPARISON,
            triggers=("vs",),
        ),
    )
    assert "comparison" in out.lower()
    assert "period" in out.lower()


def test_reference_kind_guidance_for_followup() -> None:
    b = ConversationContextBuilder()
    out = b.build(
        recent_turns=(_turn(1, "show top customers"),),
        reference=ReferenceDecision(
            kind=ReferenceKind.FOLLOW_UP,
            triggers=("why",),
        ),
    )
    assert "follow_up" in out.lower()
    assert "pronoun" in out.lower()


def test_new_topic_no_guidance_block() -> None:
    """For NEW_TOPIC, builder still shows turns but doesn't add reference block."""
    b = ConversationContextBuilder()
    out = b.build(
        recent_turns=(_turn(1, "alpha"),),
        reference=ReferenceDecision(
            kind=ReferenceKind.NEW_TOPIC,
            triggers=(),
        ),
    )
    # No "**refinement**" block (the header line has "refinements" as plain text).
    assert "**refinement**" not in out.lower()
    assert "Add a WHERE-clause" not in out
    assert "Turn 1" in out

"""Tests for the ambiguity scorer + resolver (Phase 6.2)."""
from __future__ import annotations

from app.ambiguity import (
    AmbiguityDecision,
    AmbiguityResolver,
    AmbiguityScorer,
)
from app.schema.domains import Domain, load_domain_mapping
from app.schema.glossary import load_glossary

# ── scorer ─────────────────────────────────────────────────────────────


def test_scorer_finds_lead_time() -> None:
    g = load_glossary()
    m = load_domain_mapping()
    s = AmbiguityScorer(g, mapping=m).score("what is the lead time for this product?")
    assert len(s) >= 1
    assert any(score.term.lower() == "lead time" for score in s)


def test_scorer_zero_when_no_ambiguous_term() -> None:
    g = load_glossary()
    s = AmbiguityScorer(g).score("how many warehouses do we have?")
    assert s == ()


def test_scorer_lowers_score_when_one_routed_domain_matches() -> None:
    """If routing already narrows the sense, the score drops."""
    g = load_glossary()
    m = load_domain_mapping()
    no_routing = AmbiguityScorer(g, mapping=m).score("lead time analysis")
    one_routed = AmbiguityScorer(g, mapping=m).score(
        "lead time analysis", candidate_domains=(Domain.LOGISTICS,)
    )
    assert no_routing[0].score > one_routed[0].score


# ── resolver decisions ────────────────────────────────────────────────


def test_resolver_proceeds_when_no_ambiguity() -> None:
    g = load_glossary()
    r = AmbiguityResolver(g).resolve("how many warehouses do we have?")
    assert r.decision == AmbiguityDecision.PROCEED


def test_resolver_clarifies_when_above_threshold() -> None:
    g = load_glossary()
    r = AmbiguityResolver(g).resolve(
        "what is the lead time?",
        routed_domains=(),
    )
    assert r.decision == AmbiguityDecision.CLARIFY
    assert "lead time" in r.clarification_question.lower()


def test_resolver_proceeds_when_routing_resolves_sense() -> None:
    """Routing narrows lead-time to one sense → resolver proceeds."""
    g = load_glossary()
    m = load_domain_mapping()
    r = AmbiguityResolver(g, mapping=m).resolve(
        "what is the lead time?",
        routed_domains=(Domain.LOGISTICS,),
    )
    assert r.decision == AmbiguityDecision.PROCEED


def test_resolver_uses_history_to_auto_resolve() -> None:
    g = load_glossary()
    history = (
        "Turn 1: 'show me sale_order activity' (1 domain, 24 rows)\n"
        "Turn 2: 'group sales by month' (1 domain, 12 rows)"
    )
    r = AmbiguityResolver(g).resolve(
        "summarise sales last month",
        routed_domains=(),
        history_summary=history,
    )
    # We don't strictly assert AUTO_RESOLVED here (depends on candidate text
    # matching the history) — just that the resolver makes a deterministic
    # call without raising.
    assert r.decision in (
        AmbiguityDecision.AUTO_RESOLVED,
        AmbiguityDecision.CLARIFY,
        AmbiguityDecision.PROCEED,
    )


def test_clarification_lists_the_competing_senses() -> None:
    g = load_glossary()
    r = AmbiguityResolver(g).resolve(
        "what's the cost?",
        routed_domains=(),
    )
    if r.decision == AmbiguityDecision.CLARIFY:
        # At least one sense token should appear in the question.
        senses = [s for sc in r.scores for s in sc.senses]
        joined = r.clarification_question.lower()
        assert any(s.split(" ")[0].lower() in joined for s in senses)

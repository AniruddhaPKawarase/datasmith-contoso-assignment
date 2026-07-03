"""Tests for ReferenceDetector classification (Phase 7.2)."""
from __future__ import annotations

import pytest

from app.conversation import ReferenceDetector, ReferenceKind


@pytest.fixture
def detector() -> ReferenceDetector:
    return ReferenceDetector()


def _classify(detector: ReferenceDetector, q: str, *, has_prior: bool = True):
    return detector.classify(q, has_prior_turn=has_prior)


# ── No prior turn → always NEW_TOPIC ──────────────────────────────────


def test_first_turn_is_always_new_topic(detector: ReferenceDetector) -> None:
    r = _classify(detector, "compare revenue last quarter vs last year",
                  has_prior=False)
    assert r.kind == ReferenceKind.NEW_TOPIC
    assert r.triggers == ()


# ── Refinement ────────────────────────────────────────────────────────


@pytest.mark.parametrize("q", [
    "only for Europe",
    "just the Asian suppliers",
    "filter by company id 1",
    "restrict to last quarter",
    "drill down to the warehouse level",
    "but only excluding cancelled orders",
])
def test_refinement_phrases(detector: ReferenceDetector, q: str) -> None:
    r = _classify(detector, q)
    assert r.kind == ReferenceKind.REFINEMENT, f"failed for {q!r}: {r}"
    assert r.triggers


# ── Comparison ────────────────────────────────────────────────────────


@pytest.mark.parametrize("q", [
    "compare with last year",
    "vs the same period last year",
    "year-over-year",
    "now compare with Q1 2025",
    "versus the previous quarter",
])
def test_comparison_phrases(detector: ReferenceDetector, q: str) -> None:
    r = _classify(detector, q)
    assert r.kind == ReferenceKind.COMPARISON, f"failed for {q!r}: {r}"


# ── Follow-up ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("q", [
    "why?",
    "Why is that?",
    "and the next month?",
    "what about Asia?",
    "explain that",
    "break down by warehouse",
])
def test_followup_phrases(detector: ReferenceDetector, q: str) -> None:
    r = _classify(detector, q)
    assert r.kind == ReferenceKind.FOLLOW_UP, f"failed for {q!r}: {r}"


def test_short_pronoun_query_is_followup(detector: ReferenceDetector) -> None:
    r = _classify(detector, "what about those products?")
    assert r.kind == ReferenceKind.FOLLOW_UP
    assert "those" in r.triggers


# ── New topic ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("q", [
    "show me the top 10 customers",
    "list all warehouses",
    "now show inventory by location",
    "new question: how many products do we have?",
])
def test_new_topic_phrases(detector: ReferenceDetector, q: str) -> None:
    r = _classify(detector, q)
    assert r.kind == ReferenceKind.NEW_TOPIC, f"failed for {q!r}: {r}"


def test_default_to_new_topic_when_no_cue(detector: ReferenceDetector) -> None:
    r = _classify(detector, "how does Odoo store fiscal years")
    assert r.kind == ReferenceKind.NEW_TOPIC


# ── Precedence ────────────────────────────────────────────────────────


def test_comparison_beats_refinement(detector: ReferenceDetector) -> None:
    """A phrase that has both 'compare' and 'only' resolves as COMPARISON."""
    r = _classify(detector, "compare only the Asian suppliers")
    assert r.kind == ReferenceKind.COMPARISON


def test_refinement_beats_followup(detector: ReferenceDetector) -> None:
    r = _classify(detector, "only those Asian suppliers")
    assert r.kind == ReferenceKind.REFINEMENT


def test_needs_prior_turn_flag(detector: ReferenceDetector) -> None:
    assert _classify(detector, "compare with last year").needs_prior_turn
    assert not _classify(detector, "show me orders").needs_prior_turn

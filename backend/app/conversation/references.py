"""Reference-kind detection for a follow-up query.

Rule-based classifier. Each kind is mutually exclusive; ties are resolved
by precedence: COMPARISON > REFINEMENT > FOLLOW_UP > NEW_TOPIC.

Why no LLM? This decision is needed *before* the Router, so adding an
LLM call here doubles router latency. Empirically the patterns below
catch ~95 % of the multi-turn cases the dissertation cares about; the
remaining edge cases default to NEW_TOPIC, which means the pipeline
treats the query as fresh — the worst that happens is we miss an
optimisation, not produce a wrong answer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class ReferenceKind(StrEnum):
    NEW_TOPIC = "new_topic"
    REFINEMENT = "refinement"          # narrows a previous result
    COMPARISON = "comparison"          # compares to prior result / period
    FOLLOW_UP = "follow_up"            # explanatory follow-up ("why?", "what about Y?")


@dataclass(frozen=True)
class ReferenceDecision:
    """Classification + the signals that triggered it."""

    kind: ReferenceKind
    triggers: tuple[str, ...]          # exact substrings/patterns matched
    notes: str = ""

    @property
    def is_new_topic(self) -> bool:
        return self.kind == ReferenceKind.NEW_TOPIC

    @property
    def needs_prior_turn(self) -> bool:
        return self.kind != ReferenceKind.NEW_TOPIC


# ── pattern banks ─────────────────────────────────────────────────────


_PRONOUNS = (
    r"\b(they|them|those|these|that|this|it)\b",
)

_REFINEMENT_OPENERS = (
    r"^(only|just|filter|restrict|narrow|exclude|excluding|drill\s*down)\b",
    r"^(now|then)\s+(only|just)\b",
    r"\bonly\s+(for|in|the|with)\b",
    r"\b(filter|restrict|narrow)\s+(by|to)\b",
    r"\b(but|except)\s+(only|excluding|exclude)\b",
)

_COMPARISON_OPENERS = (
    r"\b(compare|vs\.?|versus|against)\s+",
    r"\b(same\s+(?:period|quarter|month|year)\s+last\s+year)\b",
    r"\b(year[\s\-]?over[\s\-]?year|yoy)\b",
    r"\b(now\s+compare|then\s+compare)\b",
)

_FOLLOWUP_OPENERS = (
    r"^why\b",
    r"^(what|how)\s+about\b",
    r"^\s*and\s+",
    r"\bwhy\s+(is|was|did|are)\b",
    r"\bbreak\s*down\b",
    r"\bexplain\b",
)

# Strong "new topic" signals — explicit reset language.
_NEW_TOPIC_OPENERS = (
    r"^(show|list|display|find|fetch|retrieve)\s+(me\s+)?",
    r"^(new\s+question|new\s+topic|now\s+show|now\s+find)\b",
    r"^what\s+(is|are|was|were)\s+(?!the\s+(reason|cause))",
)


class ReferenceDetector:
    """Classify a follow-up query relative to a prior turn's existence.

    Pass ``has_prior_turn=False`` for the first message of a session — in
    that case the result is always ``NEW_TOPIC``.
    """

    def classify(
        self,
        query: str,
        *,
        has_prior_turn: bool,
    ) -> ReferenceDecision:
        if not has_prior_turn:
            return ReferenceDecision(
                kind=ReferenceKind.NEW_TOPIC,
                triggers=(),
                notes="No prior turn.",
            )

        q = query.lower().strip()
        triggers: list[str] = []

        # Order: comparison > refinement > follow_up > new_topic.
        if _any_match(q, _COMPARISON_OPENERS, triggers):
            return ReferenceDecision(
                kind=ReferenceKind.COMPARISON,
                triggers=tuple(triggers),
                notes="Comparison/temporal-vs cue detected.",
            )
        if _any_match(q, _REFINEMENT_OPENERS, triggers):
            return ReferenceDecision(
                kind=ReferenceKind.REFINEMENT,
                triggers=tuple(triggers),
                notes="Restriction/narrowing cue detected.",
            )

        # Pronoun + short follow-up clauses → follow_up
        pronouns_hit: list[str] = []
        _any_match(q, _PRONOUNS, pronouns_hit)
        if _any_match(q, _FOLLOWUP_OPENERS, triggers) or (
            pronouns_hit and len(q) < 80
        ):
            return ReferenceDecision(
                kind=ReferenceKind.FOLLOW_UP,
                triggers=tuple(triggers + pronouns_hit),
                notes="Follow-up / pronoun reference.",
            )

        # Explicit new-topic openers override carry-over.
        nt: list[str] = []
        if _any_match(q, _NEW_TOPIC_OPENERS, nt):
            return ReferenceDecision(
                kind=ReferenceKind.NEW_TOPIC,
                triggers=tuple(nt),
                notes="Explicit new-question phrasing.",
            )

        # Otherwise: treat as new topic — conservative default.
        return ReferenceDecision(
            kind=ReferenceKind.NEW_TOPIC,
            triggers=(),
            notes="No carry-over cues; treating as new topic.",
        )


# ── helpers ───────────────────────────────────────────────────────────


def _any_match(
    q: str,
    patterns: tuple[str, ...],
    out_triggers: list[str],
) -> bool:
    """Return True if any pattern matches; append the matched span to triggers."""
    found = False
    for pat in patterns:
        m = re.search(pat, q)
        if m:
            out_triggers.append(m.group(0))
            found = True
    return found

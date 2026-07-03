"""Ambiguity detection + resolution.

Inspired by AmbiSQL (Liu et al. 2025) and Odin (Patel et al. 2025).
The flow:

1. ``AmbiguityScorer`` looks at the user query through the Glossary's
   ambiguous-term lens (e.g. "lead time" → {procurement, manufacturing,
   delivery}). Each candidate gets an evidence-based score.
2. ``AmbiguityResolver`` decides:
     * **auto-resolve** — context (history, routed domain) selects one
       sense unambiguously;
     * **clarify** — emit a structured clarification question for the
       user;
     * **ignore** — score below threshold, proceed without disambiguation.
"""

from app.ambiguity.resolver import (
    AmbiguityDecision,
    AmbiguityResolution,
    AmbiguityResolver,
)
from app.ambiguity.scorer import AmbiguityScore, AmbiguityScorer

__all__ = [
    "AmbiguityDecision",
    "AmbiguityResolution",
    "AmbiguityResolver",
    "AmbiguityScore",
    "AmbiguityScorer",
]

"""Decide whether to auto-resolve, clarify, or ignore ambiguous terms."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.ambiguity.scorer import AmbiguityScore, AmbiguityScorer
from app.schema.domains import Domain, DomainMapping
from app.schema.glossary import Glossary


class AmbiguityDecision(StrEnum):
    """What the resolver wants the orchestrator to do."""

    PROCEED = "proceed"                # ambiguity below threshold or already auto-resolved
    CLARIFY = "clarify"                # ask the user a structured question
    AUTO_RESOLVED = "auto_resolved"    # we picked a sense based on context


@dataclass(frozen=True)
class AmbiguityResolution:
    """Final decision for a query + the rationale."""

    decision: AmbiguityDecision
    scores: tuple[AmbiguityScore, ...]
    clarification_question: str = ""
    resolved_senses: dict[str, str] | None = None
    notes: str = ""


_CLARIFY_THRESHOLD = 0.55


class AmbiguityResolver:
    """Lightweight rules-based resolver.

    Combines the Scorer's evidence with two signals the Router can provide
    (the routed domains and the conversation history) to decide whether
    the pipeline should proceed or pause for clarification.
    """

    def __init__(
        self,
        glossary: Glossary,
        *,
        mapping: DomainMapping | None = None,
        clarify_threshold: float = _CLARIFY_THRESHOLD,
    ) -> None:
        self._scorer = AmbiguityScorer(glossary, mapping=mapping)
        self._threshold = clarify_threshold

    def resolve(
        self,
        query: str,
        *,
        routed_domains: tuple[Domain, ...] = (),
        history_summary: str = "",
    ) -> AmbiguityResolution:
        scores = self._scorer.score(query, candidate_domains=routed_domains)
        if not scores:
            return AmbiguityResolution(
                decision=AmbiguityDecision.PROCEED,
                scores=(),
                notes="No ambiguous terms found in query.",
            )

        # Auto-resolve: every score < threshold AND each ambiguous term has
        # exactly one routed sense in play.
        max_score = max(s.score for s in scores)
        if max_score < self._threshold:
            return AmbiguityResolution(
                decision=AmbiguityDecision.PROCEED,
                scores=scores,
                notes=f"All ambiguity scores below {self._threshold:.2f}.",
            )

        # History contains the prior sense? Use it.
        history_lower = history_summary.lower()
        auto_resolved: dict[str, str] = {}
        for s in scores:
            for sense in s.senses:
                if sense.lower() in history_lower:
                    auto_resolved[s.term] = sense
                    break
        if auto_resolved and len(auto_resolved) == len(scores):
            return AmbiguityResolution(
                decision=AmbiguityDecision.AUTO_RESOLVED,
                scores=scores,
                resolved_senses=auto_resolved,
                notes="Resolved via prior conversation context.",
            )

        return AmbiguityResolution(
            decision=AmbiguityDecision.CLARIFY,
            scores=scores,
            clarification_question=self._build_clarification(scores),
            notes="Ambiguity score above threshold and no resolving context.",
        )

    @staticmethod
    def _build_clarification(scores: tuple[AmbiguityScore, ...]) -> str:
        if not scores:
            return ""
        # First (most ambiguous) term drives the question.
        worst = max(scores, key=lambda s: s.score)
        senses_list = ", ".join(f'"{s}"' for s in worst.senses)
        return (
            f"By '{worst.term}', do you mean {senses_list}? "
            "Please clarify so I can route the query to the right specialist."
        )

"""Score ambiguous terms in a user query."""
from __future__ import annotations

from dataclasses import dataclass

from app.schema.domains import Domain, DomainMapping
from app.schema.glossary import AmbiguousTerm, Glossary


@dataclass(frozen=True)
class AmbiguityScore:
    """One ambiguous term + its competing senses + an evidence-based score."""

    term: str
    senses: tuple[str, ...]                # free-form candidate descriptions
    candidate_domains: tuple[Domain, ...]  # heuristic guess at relevant domains
    score: float                            # 0..1; higher = more ambiguous given context
    notes: str = ""


class AmbiguityScorer:
    """Score ambiguous Glossary terms against the Router's routed-domain hint.

    The Glossary stores ambiguous terms as ``AmbiguousTerm(term, candidates)``
    where each candidate is a free-form string like
    "procurement (purchase_order)". We infer the *probable* domain of each
    candidate by token-matching the DomainMapping's keywords + table names.
    """

    def __init__(
        self,
        glossary: Glossary,
        *,
        mapping: DomainMapping | None = None,
    ) -> None:
        self._gloss = glossary
        self._mapping = mapping

    def score(
        self,
        query: str,
        *,
        candidate_domains: tuple[Domain, ...] = (),
    ) -> tuple[AmbiguityScore, ...]:
        hits = self._gloss.is_ambiguous(query)
        if not hits:
            return ()
        out: list[AmbiguityScore] = []
        routed = set(candidate_domains)
        for hit in hits:
            inferred = self._infer_domains(hit)
            score = self._score_one(hit, inferred, routed)
            out.append(AmbiguityScore(
                term=hit.term,
                senses=hit.candidates,
                candidate_domains=inferred,
                score=score,
                notes=self._notes_for(inferred, routed),
            ))
        return tuple(out)

    # ── private helpers ───────────────────────────────────────────────

    def _infer_domains(self, hit: AmbiguousTerm) -> tuple[Domain, ...]:
        """Best-effort domain inference per candidate string.

        Matches Domain.value tokens (e.g. ``logistics``) and the
        mapping's keywords against each candidate's lowercased text.
        Returns the *unique* domains found, preserving order.
        """
        seen: list[Domain] = []
        for cand in hit.candidates:
            cl = cand.lower()
            for d in Domain:
                if d.value in cl and d not in seen:
                    seen.append(d)
            if self._mapping is None:
                continue
            for d, spec in self._mapping.domains.items():
                if d in seen:
                    continue
                matched = False
                for kw in spec.keywords:
                    if kw.lower() in cl:
                        seen.append(d)
                        matched = True
                        break
                if matched:
                    continue
                for tbl in spec.primary_tables:
                    if tbl.lower() in cl:
                        seen.append(d)
                        break
        return tuple(seen)

    @staticmethod
    def _score_one(
        hit: AmbiguousTerm,
        inferred: tuple[Domain, ...],
        routed: set[Domain],
    ) -> float:
        """Higher when more senses are in play / fewer disambiguating cues."""
        n_senses = len(hit.candidates)
        if n_senses <= 1:
            return 0.0
        overlap = set(inferred) & routed
        if not routed:
            return min(1.0, 0.5 + 0.1 * n_senses)
        if not overlap:
            # We routed somewhere, but no inferred sense matched — leave
            # ambiguity high; the agent will likely refuse the query.
            return min(1.0, 0.5 + 0.1 * n_senses)
        if len(overlap) == 1:
            return 0.15            # almost resolved by routing
        return min(1.0, 0.3 + 0.1 * len(overlap))

    @staticmethod
    def _notes_for(
        inferred: tuple[Domain, ...],
        routed: set[Domain],
    ) -> str:
        overlap = set(inferred) & routed
        if not routed:
            return "No routed domains yet — full ambiguity."
        if not overlap:
            routed_list = sorted(d.value for d in routed)
            return f"Routed {routed_list} don't match any sense — likely out-of-scope."
        if len(overlap) == 1:
            d = next(iter(overlap))
            return f"Routing narrows term to {d.value} sense."
        return f"Multiple routed senses: {sorted(d.value for d in overlap)}"

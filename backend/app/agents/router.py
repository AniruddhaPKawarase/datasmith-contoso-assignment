"""Router/Planner agent.

Takes the user's NL query (plus brief conversation context) and decides:

1. **Intent** — is this a supply-chain question, out of scope, or
   under-specified (needs clarification)?
2. **Domains** — which of the 5 domain specialists must be involved?
3. **Sub-queries** — one rewritten natural-language sub-question per domain.

Uses the cheap classifier model (``ModelTask.ROUTER``, default
``openai/gpt-4o-mini``) at ``temperature=0`` and JSON mode so the response
is deterministically parseable.

A simple keyword-heuristic fallback applies when the LLM call fails or
returns malformed JSON — this keeps the pipeline available offline for
tests and during cost-sensitive runs.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from app.agents.state import SubQuery
from app.llm import LLMProvider, ModelTask
from app.llm.token_tracker import TokenTracker
from app.schema.domains import Domain, DomainMapping
from app.schema.glossary import Glossary

logger = logging.getLogger(__name__)


_ALLOWED_INTENTS = ("supply_chain_question", "out_of_scope", "clarification_needed")


@dataclass(frozen=True)
class RouterDecision:
    """Structured output of a single routing pass."""

    intent: str
    domains: tuple[Domain, ...]
    sub_queries: tuple[SubQuery, ...]
    reasoning: str
    fallback_used: bool = False


_SYSTEM_PROMPT = """\
You are the Router for an NL-to-SQL system over the Microsoft Contoso
Retail Data Warehouse.

Available specialist:
- demand: all Contoso sales analytics — online and reseller channel
          sales, sales quota vs. attainment, customer demographics,
          product hierarchy, sales territories/regions, employees,
          time-series/trend queries (MoM, YoY, quarterly), rankings
          (top-N by revenue / spend / attainment), comparative
          analysis (internet vs reseller), funnels, mixed-panel
          demographic breakdowns.

The other domain names (inventory, logistics, finance, compliance)
exist in the enum for legacy reasons but have no active tables in the
Contoso deployment — never select them.

Your job:
1. Classify the query's INTENT (exactly one of):
   - "supply_chain_question": answerable from Contoso sales data
   - "out_of_scope":           unrelated (e.g. "what's the weather?")
   - "clarification_needed":   too vague or ambiguous to answer safely
2. If intent is supply_chain_question, return domains: ["demand"] with
   exactly one sub_query rephrasing the user's question in analytics terms.

Clarification protocol: if the query is missing a critical dimension
(date range, channel choice, geographic granularity, comparison
baseline), return "clarification_needed" and set reasoning to the ONE
follow-up question to ask.

Reply with ONLY valid JSON matching this schema:
{
  "intent": "<intent>",
  "domains": ["demand"],
  "sub_queries": [
    {"domain": "demand", "natural_language": "...", "rationale": "..."}
  ],
  "reasoning": "<one-sentence rationale or clarification question>"
}
"""


class RouterAgent:
    """LLM-driven domain classifier with keyword fallback."""

    def __init__(
        self,
        *,
        llm: LLMProvider,
        mapping: DomainMapping,
        glossary: Glossary,
        tracker: TokenTracker | None = None,
        model_task: ModelTask = ModelTask.ROUTER,
    ) -> None:
        self._llm = llm
        self._mapping = mapping
        self._glossary = glossary
        self._tracker = tracker
        self._task = model_task

    async def route(
        self,
        query: str,
        *,
        history_summary: str = "",
    ) -> RouterDecision:
        """Classify ``query`` into intent + domains + sub-queries."""
        ambiguous_terms = self._glossary.is_ambiguous(query)
        ambig_hint = (
            "\n\nWARNING: query contains ambiguous SCM terms — set intent to "
            f"'clarification_needed' if context is insufficient: "
            f"{[a.term for a in ambiguous_terms]}"
            if ambiguous_terms
            else ""
        )
        user_msg = (
            f"User query:\n{query.strip()}\n\n"
            f"Prior conversation summary (may be empty):\n{history_summary.strip() or '(none)'}"
            f"{ambig_hint}"
        )
        try:
            resp = await self._llm.generate(
                task=self._task,
                system=_SYSTEM_PROMPT,
                user=user_msg,
                temperature=0.0,
                max_tokens=400,
                json_mode=True,
            )
            if self._tracker is not None:
                self._tracker.record(self._task, resp)
            return self._parse(resp.text, fallback_used=False)
        except Exception as exc:
            logger.warning("Router LLM call failed (%s); using keyword fallback", exc)
            return self._keyword_fallback(query)

    # ── parsing & fallback ────────────────────────────────────────────

    def _parse(self, raw: str, *, fallback_used: bool) -> RouterDecision:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Router returned non-JSON; falling back. raw=%r", raw[:200])
            return self._keyword_fallback(raw)

        intent = str(data.get("intent", "")).strip()
        if intent not in _ALLOWED_INTENTS:
            intent = "supply_chain_question"

        domains: list[Domain] = []
        for d_str in data.get("domains") or ():
            try:
                d = Domain(str(d_str).strip().lower())
            except ValueError:
                continue
            if d not in domains:
                domains.append(d)

        sub_queries: list[SubQuery] = []
        for sq in data.get("sub_queries") or ():
            try:
                dom = Domain(str(sq.get("domain", "")).strip().lower())
            except ValueError:
                continue
            sub_queries.append(
                SubQuery(
                    domain=dom,
                    natural_language=str(sq.get("natural_language", "")).strip(),
                    rationale=str(sq.get("rationale", "")).strip(),
                )
            )

        return RouterDecision(
            intent=intent,
            domains=tuple(domains),
            sub_queries=tuple(sub_queries),
            reasoning=str(data.get("reasoning", "")).strip(),
            fallback_used=fallback_used,
        )

    def _keyword_fallback(self, query: str) -> RouterDecision:
        """Pure-Python heuristic — no LLM. Used when the model fails."""
        q = query.lower()
        votes: dict[Domain, int] = {}
        for d, spec in self._mapping.domains.items():
            if spec.cross_cutting:
                continue
            for kw in spec.keywords:
                if kw.lower() in q:
                    votes[d] = votes.get(d, 0) + 1
        if not votes:
            return RouterDecision(
                intent="clarification_needed",
                domains=(),
                sub_queries=(),
                reasoning="No domain keywords matched; fallback could not classify.",
                fallback_used=True,
            )
        chosen = sorted(votes.items(), key=lambda kv: -kv[1])
        domains = tuple(d for d, _ in chosen)
        sub_queries = tuple(
            SubQuery(domain=d, natural_language=query, rationale="keyword fallback")
            for d in domains
        )
        return RouterDecision(
            intent="supply_chain_question",
            domains=domains,
            sub_queries=sub_queries,
            reasoning=f"keyword fallback: matched {[d.value for d in domains]}",
            fallback_used=True,
        )

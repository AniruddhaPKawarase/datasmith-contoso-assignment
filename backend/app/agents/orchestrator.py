"""LangGraph orchestration of the NL-to-SQL pipeline.

The state machine looks like::

    START
      ↓
    classify_node          (Router decides intent + domains + sub-queries)
      ↓
    [intent == out_of_scope OR clarification_needed?] → respond_node → END
      ↓ no
    route_node             (assemble per-domain SubQuery records)
      ↓
    generate_node          (each domain agent emits its SQL fragment)
      ↓
    compose_node           (Composer merges fragments — Phase 5 real, stub now)
      ↓
    validate_node          (syntax → execution → business-rule; Phase 5)
      ↓
    [issues AND attempt < MAX] → generate_node       (self-correction loop)
      ↓ no
    respond_node           (assemble final response)
      ↓
    END

For Phase 3 the compose + validate + execute nodes are deliberate stubs:
they pass through whatever the (stub) domain agents produced. Phase 5
replaces them with the real Composer, federation engine, and validator.
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.base import BaseAgent
from app.agents.compliance import ComplianceContext, ComplianceProcessor
from app.agents.memory import ConversationMemory
from app.agents.messages import AgentMessage, MessageKind, MessageLog
from app.agents.router import RouterAgent, RouterDecision
from app.agents.state import (
    AgentOutput,
    AgentState,
    OrchestratorLimits,
    SubQuery,
    ValidationIssue,
)
from app.ambiguity import AmbiguityDecision, AmbiguityResolver
from app.composer import Composer
from app.conversation import (
    ConversationContextBuilder,
    ReferenceDetector,
)
from app.schema.domains import Domain
from app.temporal import TemporalContext, TemporalParser
from app.validator import ValidationPipeline

logger = logging.getLogger(__name__)


# Type alias for an async LangGraph node function.
NodeFn = Callable[[AgentState], Awaitable[AgentState]]


class Orchestrator:
    """Builds and runs the LangGraph state machine.

    Instantiated once at app startup. Each call to ``run`` is a fresh
    pipeline invocation; state mutations are local to that invocation.
    """

    def __init__(
        self,
        *,
        router: RouterAgent,
        agents: Mapping[Domain, BaseAgent],
        memory: ConversationMemory,
        composer: Composer | None = None,
        validator: ValidationPipeline | None = None,
        compliance: ComplianceProcessor | None = None,
        temporal_parser: TemporalParser | None = None,
        ambiguity_resolver: AmbiguityResolver | None = None,
        reference_detector: ReferenceDetector | None = None,
        conversation_builder: ConversationContextBuilder | None = None,
        message_log: MessageLog | None = None,
        limits: OrchestratorLimits | None = None,
        execute_on_validate: bool = False,
    ) -> None:
        self._router = router
        self._agents: dict[Domain, BaseAgent] = dict(agents)
        self._memory = memory
        self._composer = composer or Composer()
        self._validator = validator
        self._compliance = compliance
        self._temporal = temporal_parser
        self._ambiguity = ambiguity_resolver
        self._references = reference_detector
        self._conv_builder = conversation_builder or ConversationContextBuilder()
        self._log = message_log or MessageLog()
        self._limits = limits or OrchestratorLimits()
        self._execute = execute_on_validate
        self._graph = self._build_graph()

    # ── public API ────────────────────────────────────────────────────

    async def run(self, state: AgentState) -> AgentState:
        """Execute the pipeline end-to-end for one query."""
        result: AgentState = await self._graph.ainvoke(state)
        # Record turn in memory if the answer was successful enough.
        if result.get("intent") == "supply_chain_question":
            self._memory.record_turn(
                session_id=str(result.get("session_id", "")),
                user_query=str(result.get("query", "")),
                domains_used=tuple(result.get("domains", ())),
                generated_sql=str(result.get("composed_sql", "")),
                row_count=int(result.get("row_count", 0)),
                summary=str(result.get("explanation", "")),
            )
        return result

    def message_log(self) -> MessageLog:
        return self._log

    # ── graph wiring ──────────────────────────────────────────────────

    def _build_graph(self) -> Any:
        graph: StateGraph[AgentState] = StateGraph(AgentState)
        graph.add_node("classify", self._classify_node)
        graph.add_node("route", self._route_node)
        graph.add_node("generate", self._generate_node)
        graph.add_node("compose", self._compose_node)
        graph.add_node("validate", self._validate_node)
        graph.add_node("respond", self._respond_node)

        graph.add_edge(START, "classify")
        graph.add_conditional_edges(
            "classify",
            self._after_classify,
            {"route": "route", "respond": "respond"},
        )
        graph.add_node("compliance", self._compliance_node)
        graph.add_edge("route", "generate")
        graph.add_edge("generate", "compose")
        graph.add_edge("compose", "compliance")
        graph.add_edge("compliance", "validate")
        graph.add_conditional_edges(
            "validate",
            self._after_validate,
            {"retry": "generate", "respond": "respond"},
        )
        graph.add_edge("respond", END)
        return graph.compile()

    async def _compliance_node(self, state: AgentState) -> AgentState:
        """Inject RBAC predicates into the composed SQL."""
        sql = state.get("composed_sql", "")
        if not sql.strip() or self._compliance is None:
            return AgentState()
        ctx = ComplianceContext(
            user_id=0,                   # filled in once we wire real auth (post-Phase 9)
            user_role=str(state.get("user_role", "analyst")),
            company_ids=tuple(state.get("user_company_ids", ())),
            warehouse_ids=tuple(state.get("user_warehouse_ids", ())),
            bypass=str(state.get("user_role", "")).lower() in ("admin", "superuser"),
        )
        decision = self._compliance.apply(
            sql, ctx,
            message_log=self._log,
            correlation_id=str(state.get("session_id", "")),
        )
        return AgentState(composed_sql=decision.sql)

    # ── node implementations ──────────────────────────────────────────

    async def _classify_node(self, state: AgentState) -> AgentState:
        query = state.get("query", "")
        correlation = state.get("session_id", "no-session")
        self._log.append(
            AgentMessage.make(
                correlation_id=correlation,
                kind=MessageKind.QUERY,
                from_agent="user",
                to_agent="router",
                payload={"query": query},
            )
        )
        decision = await self._router.route(
            query, history_summary=state.get("history_summary", "")
        )

        # Phase 7 — multi-turn carry-over. When the user's follow-up has a
        # non-NEW_TOPIC reference (e.g. "only the top 5"), inherit the
        # prior turn's domains rather than letting the Router classify a
        # context-less fragment as clarification_needed.
        ref = None
        if self._references is not None:
            _, prior_window = self._memory.active_window(correlation)
            ref = self._references.classify(
                query, has_prior_turn=bool(prior_window)
            )
            if (
                ref is not None
                and not ref.is_new_topic
                and prior_window
                and decision.intent != "supply_chain_question"
            ):
                last = prior_window[-1]
                decision = RouterDecision(
                    intent="supply_chain_question",
                    domains=last.domains_used,
                    sub_queries=tuple(
                        SubQuery(
                            domain=d,
                            natural_language=query,
                            rationale=f"carry-over from prior turn ({ref.kind.value})",
                        )
                        for d in last.domains_used
                    ),
                    reasoning=(
                        f"Carry-over: kind={ref.kind.value}, prior domains "
                        f"{[d.value for d in last.domains_used]}"
                    ),
                    fallback_used=False,
                )

        # Phase 6 — deterministic temporal parse (always runs; cheap).
        temporal_ctx: TemporalContext = TemporalContext()
        if self._temporal is not None:
            temporal_ctx = self._temporal.parse(query)

        # Phase 6 — ambiguity resolution. Always run when we have a
        # resolver so we get a *specific* clarification question, whether
        # the Router itself classified the query as clarification_needed
        # or we promote it.
        intent = decision.intent
        clarification = ""
        if self._ambiguity is not None:
            resolution = self._ambiguity.resolve(
                query,
                routed_domains=decision.domains,
                history_summary=state.get("history_summary", ""),
            )
            if resolution.decision == AmbiguityDecision.CLARIFY:
                intent = "clarification_needed"
                clarification = resolution.clarification_question
            elif (
                decision.intent == "clarification_needed"
                and resolution.clarification_question
            ):
                clarification = resolution.clarification_question

        self._log.append(
            AgentMessage.make(
                correlation_id=correlation,
                kind=MessageKind.SUB_QUERY,
                from_agent="router",
                to_agent="orchestrator",
                payload={
                    "intent": intent,
                    "domains": [d.value for d in decision.domains],
                    "fallback_used": decision.fallback_used,
                    "temporal_expressions": [e.text for e in temporal_ctx.expressions],
                    "clarification": clarification,
                },
            )
        )
        return AgentState(
            intent=intent,
            domains=decision.domains,
            sub_queries=decision.sub_queries,
            router_reasoning=decision.reasoning,
            temporal=temporal_ctx,
            clarification_question=clarification,
        )

    async def _route_node(self, state: AgentState) -> AgentState:
        """Ensure every chosen domain has a SubQuery. Adds defaults if needed."""
        chosen = tuple(state.get("domains", ()))
        existing = {sq.domain: sq for sq in state.get("sub_queries", ())}
        sub_queries = tuple(
            existing.get(
                d,
                SubQuery(
                    domain=d,
                    natural_language=str(state.get("query", "")),
                    rationale="Router did not provide a specific rewrite.",
                ),
            )
            for d in chosen
        )
        return AgentState(sub_queries=sub_queries)

    async def _generate_node(self, state: AgentState) -> AgentState:
        outputs: list[AgentOutput] = []
        correlation = state.get("session_id", "no-session")
        # Each entry into generate counts as one attempt. Increment here
        # so the validate→generate self-correction loop terminates.
        attempt = state.get("attempt", 0) + 1
        prior_issues = state.get("validation_issues", ())
        prior_error = "\n".join(
            f"- [{i.kind}] {i.message}" for i in prior_issues
        )
        for sq in state.get("sub_queries", ()):
            agent = self._agents.get(sq.domain)
            if agent is None:
                outputs.append(
                    AgentOutput(
                        domain=sq.domain,
                        sql="",
                        confidence=0.0,
                        used_tables=(),
                        notes=f"No agent registered for {sq.domain.value}",
                    )
                )
                continue
            temporal_ctx = state.get("temporal") or TemporalContext()
            temporal_block = (
                temporal_ctx.render_prompt_block()
                if isinstance(temporal_ctx, TemporalContext)
                else ""
            )
            # Phase 7 — fetch active window + classify reference kind.
            older_summary, recent = self._memory.active_window(
                str(state.get("session_id", ""))
            )
            reference = None
            if self._references is not None:
                reference = self._references.classify(
                    str(state.get("query", "")),
                    has_prior_turn=bool(recent),
                )
            conv_block = self._conv_builder.build(
                recent_turns=recent,
                older_summary=older_summary,
                reference=reference,
            )
            try:
                result = await agent.generate_sql(
                    sq.natural_language,
                    context=conv_block,
                    attempt=attempt,
                    prior_error=prior_error,
                    temporal_block=temporal_block,
                )
            except Exception as exc:
                logger.exception("Agent %s raised", sq.domain.value)
                outputs.append(
                    AgentOutput(
                        domain=sq.domain,
                        sql="",
                        confidence=0.0,
                        used_tables=(),
                        notes=f"Agent error: {exc}",
                    )
                )
                continue
            outputs.append(
                AgentOutput(
                    domain=sq.domain,
                    sql=result.sql,
                    confidence=result.confidence,
                    used_tables=result.used_tables,
                    notes=result.rationale,
                )
            )
            self._log.append(
                AgentMessage.make(
                    correlation_id=correlation,
                    kind=MessageKind.AGENT_OUTPUT,
                    from_agent=sq.domain.value,
                    to_agent="composer",
                    payload={
                        "sql": result.sql[:500],
                        "tables": list(result.used_tables),
                        "confidence": result.confidence,
                    },
                    attempt=attempt,
                )
            )
        return AgentState(agent_outputs=tuple(outputs), attempt=attempt)

    async def _compose_node(self, state: AgentState) -> AgentState:
        """Real Composer (Phase 5): CTE-based merging with shared-key detection."""
        outputs = tuple(state.get("agent_outputs", ()))
        result = self._composer.compose(outputs)
        return AgentState(composed_sql=result.sql)

    async def _validate_node(self, state: AgentState) -> AgentState:
        """Real Validator (Phase 5): sqlglot syntax + EXPLAIN + (optional) row business-rules."""
        sql = state.get("composed_sql", "")
        if not sql.strip():
            return AgentState(
                validation_issues=(ValidationIssue(
                    kind="syntax",
                    message="Empty SQL produced by composer.",
                    location="composer",
                    suggestion="At least one domain agent must return non-empty SQL.",
                ),),
            )
        if self._validator is None:
            # Validator not configured — accept anything non-empty (test/CI mode).
            return AgentState(validation_issues=())
        report = self._validator.run(
            sql,
            execute=self._execute,
            intent=str(state.get("intent", "")),
        )
        return AgentState(
            validation_issues=report.issues,
            rows=report.rows,
            row_count=report.row_count,
        )

    async def _respond_node(self, state: AgentState) -> AgentState:
        intent = state.get("intent", "")
        issues = state.get("validation_issues", ())
        sql = state.get("composed_sql", "")
        correlation = state.get("session_id", "no-session")

        if intent == "out_of_scope":
            final_error = "Query is outside the supply-chain analytics scope."
            confidence = 0.0
            explanation = ""
        elif intent == "clarification_needed":
            cq = state.get("clarification_question", "")
            final_error = (
                cq or
                "Query is ambiguous; clarification needed before SQL can be generated."
            )
            confidence = 0.0
            explanation = state.get("router_reasoning", "")
        elif issues:
            final_error = (
                f"Validation failed after {state.get('attempt', 0)} attempt(s): "
                + "; ".join(i.message for i in issues)
            )
            confidence = 0.0
            explanation = ""
        else:
            final_error = ""
            confidence = self._aggregate_confidence(state)
            explanation = (
                f"Generated by domains: "
                f"{', '.join(d.value for d in state.get('domains', ()))}"
            )

        self._log.append(
            AgentMessage.make(
                correlation_id=correlation,
                kind=MessageKind.FINAL,
                from_agent="orchestrator",
                to_agent="user",
                payload={
                    "intent": intent,
                    "sql_length": len(sql),
                    "error": final_error,
                    "confidence": confidence,
                },
            )
        )
        return AgentState(
            final_error=final_error,
            confidence=confidence,
            explanation=explanation,
        )

    # ── routing predicates ────────────────────────────────────────────

    @staticmethod
    def _after_classify(state: AgentState) -> str:
        intent = state.get("intent", "")
        if intent in ("out_of_scope", "clarification_needed"):
            return "respond"
        if not state.get("domains"):
            return "respond"
        return "route"

    def _after_validate(self, state: AgentState) -> str:
        issues = state.get("validation_issues", ())
        attempt = state.get("attempt", 0)
        if issues and attempt < self._limits.max_correction_attempts:
            return "retry"
        return "respond"

    # ── helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _aggregate_confidence(state: AgentState) -> float:
        outs = state.get("agent_outputs", ())
        if not outs:
            return 0.0
        return round(sum(o.confidence for o in outs) / len(outs), 3)

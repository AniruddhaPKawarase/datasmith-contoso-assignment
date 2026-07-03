"""End-to-end multi-turn pipeline tests using the orchestrator with a stub agent.

Verifies that prior-turn context actually reaches the agent's `context` kwarg
and that the reference kind is correctly classified across turns.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.agents import (
    BaseAgent,
    ConversationMemory,
    Orchestrator,
    OrchestratorLimits,
    fresh_state,
)
from app.agents.base import AgentResult
from app.agents.router import RouterDecision
from app.agents.state import SubQuery
from app.conversation import ConversationContextBuilder, ReferenceDetector
from app.schema.domains import Domain, load_domain_mapping
from app.schema.glossary import load_glossary
from app.schema.metadata import Column, SchemaMetadata, Table
from app.schema.search import SchemaSearch


def _toy_meta() -> SchemaMetadata:
    return SchemaMetadata(
        database="t", schema="public", extracted_at="now",
        tables=(
            Table(
                name="stock_quant",
                columns=(
                    Column(name="id", data_type="int", is_nullable=False, is_primary_key=True),
                    Column(name="quantity", data_type="numeric", is_nullable=True),
                ),
                foreign_keys=(),
            ),
        ),
    )


class _CapturingAgent(BaseAgent):
    """Stub agent that records what context it receives."""

    def __init__(self, *, domain: Domain, **kwargs) -> None:
        self.domain = domain
        super().__init__(**kwargs)
        self.captured_contexts: list[str] = []
        self.captured_temporal: list[str] = []

    async def generate_sql(
        self,
        query: str,
        *,
        context: str = "",
        attempt: int = 1,
        prior_error: str = "",
        temporal_block: str = "",
    ) -> AgentResult:
        self.captured_contexts.append(context)
        self.captured_temporal.append(temporal_block)
        return AgentResult(
            sql=f"SELECT 1 FROM stock_quant /* {query[:60]} */",  # noqa: S608 — stub sql
            used_tables=("stock_quant",),
            confidence=0.7,
            rationale="captured",
        )


@dataclass
class _StubRouter:
    decision: RouterDecision

    async def route(self, query: str, *, history_summary: str = "") -> RouterDecision:
        return self.decision


def _build_orch(memory: ConversationMemory) -> tuple[Orchestrator, _CapturingAgent]:
    meta = _toy_meta()
    mapping = load_domain_mapping()
    glossary = load_glossary()
    search = SchemaSearch(meta)
    agent = _CapturingAgent(
        domain=Domain.INVENTORY,
        llm=None, metadata=meta, mapping=mapping,
        glossary=glossary, search=search,
    )
    router = _StubRouter(RouterDecision(
        intent="supply_chain_question",
        domains=(Domain.INVENTORY,),
        sub_queries=(SubQuery(domain=Domain.INVENTORY, natural_language="x"),),
        reasoning="",
    ))
    orch = Orchestrator(
        router=router,  # type: ignore[arg-type]
        agents={Domain.INVENTORY: agent},
        memory=memory,
        reference_detector=ReferenceDetector(),
        conversation_builder=ConversationContextBuilder(),
        limits=OrchestratorLimits(max_correction_attempts=1),
    )
    return orch, agent


async def test_first_turn_has_no_prior_context() -> None:
    memory = ConversationMemory()
    orch, agent = _build_orch(memory)
    await orch.run(fresh_state(query="show stock", session_id="s1"))
    assert agent.captured_contexts[0] == ""


async def test_second_turn_sees_prior_turn_in_context() -> None:
    memory = ConversationMemory()
    orch, agent = _build_orch(memory)
    await orch.run(fresh_state(query="show stock by warehouse", session_id="s1"))
    await orch.run(fresh_state(query="only for warehouse 1", session_id="s1"))
    assert len(agent.captured_contexts) == 2
    second_ctx = agent.captured_contexts[1]
    assert "Turn 1" in second_ctx
    assert "show stock by warehouse" in second_ctx
    assert "refinement" in second_ctx.lower()


async def test_third_turn_followup_carries_pronoun_guidance() -> None:
    memory = ConversationMemory()
    orch, agent = _build_orch(memory)
    await orch.run(fresh_state(query="show stock by warehouse", session_id="s2"))
    await orch.run(fresh_state(query="only for warehouse 1", session_id="s2"))
    await orch.run(fresh_state(query="why is that?", session_id="s2"))
    third_ctx = agent.captured_contexts[2]
    assert "follow_up" in third_ctx.lower()
    assert "pronoun" in third_ctx.lower()


async def test_session_isolation() -> None:
    memory = ConversationMemory()
    orch, agent = _build_orch(memory)
    await orch.run(fresh_state(query="show stock", session_id="sA"))
    await orch.run(fresh_state(query="only for warehouse 1", session_id="sB"))
    # sB has no prior turn from sA — context should be empty.
    assert agent.captured_contexts[1] == ""

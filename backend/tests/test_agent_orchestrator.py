"""End-to-end tests for the LangGraph orchestrator with stub agents."""
from __future__ import annotations

from dataclasses import dataclass

from app.agents import (
    BaseAgent,
    ConversationMemory,
    MessageKind,
    Orchestrator,
    OrchestratorLimits,
    fresh_state,
)
from app.agents.base import AgentResult
from app.agents.router import RouterDecision
from app.agents.state import SubQuery
from app.schema.domains import Domain, load_domain_mapping
from app.schema.glossary import load_glossary
from app.schema.metadata import (
    Column,
    SchemaMetadata,
    Table,
)
from app.schema.search import SchemaSearch


def _toy_meta() -> SchemaMetadata:
    return SchemaMetadata(
        database="t",
        schema="public",
        extracted_at="2026-05-14T00:00:00+00:00",
        tables=(
            Table(
                name="stock_quant",
                columns=(
                    Column(name="id", data_type="int", is_nullable=False, is_primary_key=True),
                    Column(name="quantity", data_type="numeric", is_nullable=True),
                ),
                foreign_keys=(),
                odoo_model="stock.quant",
                odoo_description="Stock On-Hand",
            ),
            Table(
                name="sale_order",
                columns=(
                    Column(name="id", data_type="int", is_nullable=False, is_primary_key=True),
                    Column(name="amount_total", data_type="numeric", is_nullable=True),
                ),
                foreign_keys=(),
                odoo_model="sale.order",
                odoo_description="Sales Order",
            ),
            Table(
                name="account_move",
                columns=(
                    Column(name="id", data_type="int", is_nullable=False, is_primary_key=True),
                ),
                foreign_keys=(),
                odoo_model="account.move",
                odoo_description="Journal Entry",
            ),
        ),
    )


class _CannedAgent(BaseAgent):
    """Test double that returns a configured AgentResult per call."""

    def __init__(self, *, domain: Domain, sql: str, confidence: float = 0.7, **kwargs):
        type(self).domain = domain
        super().__init__(**kwargs)
        self._sql = sql
        self._confidence = confidence
        self.calls = 0

    async def generate_sql(
        self,
        query: str,
        *,
        context: str = "",
        attempt: int = 1,
        prior_error: str = "",
        temporal_block: str = "",
    ) -> AgentResult:
        self.calls += 1
        return AgentResult(
            sql=self._sql,
            used_tables=("dummy_table",),
            confidence=self._confidence,
            rationale=f"canned, attempt={attempt}, prior={bool(prior_error)}",
        )


@dataclass
class _StubRouter:
    """Plain object exposing the same `route` async surface as RouterAgent."""

    decision: RouterDecision

    async def route(self, query: str, *, history_summary: str = "") -> RouterDecision:
        return self.decision


def _make_orchestrator(
    *,
    router_decision: RouterDecision,
    agent_sqls: dict[Domain, str],
    agent_confidence: float = 0.7,
):
    meta = _toy_meta()
    mapping = load_domain_mapping()
    glossary = load_glossary()
    search = SchemaSearch(meta)
    agents: dict[Domain, BaseAgent] = {
        d: _CannedAgent(
            domain=d,
            sql=sql,
            confidence=agent_confidence,
            llm=None,  # not invoked
            metadata=meta,
            mapping=mapping,
            glossary=glossary,
            search=search,
        )
        for d, sql in agent_sqls.items()
    }
    router = _StubRouter(router_decision)
    return Orchestrator(
        router=router,  # type: ignore[arg-type]
        agents=agents,
        memory=ConversationMemory(),
        limits=OrchestratorLimits(max_correction_attempts=3),
    )


# ───── single-domain happy path ──────────────────────────────────────


async def test_single_domain_happy_path() -> None:
    decision = RouterDecision(
        intent="supply_chain_question",
        domains=(Domain.INVENTORY,),
        sub_queries=(
            SubQuery(domain=Domain.INVENTORY, natural_language="stock?"),
        ),
        reasoning="inventory only",
    )
    orch = _make_orchestrator(
        router_decision=decision,
        agent_sqls={Domain.INVENTORY: "SELECT 1 FROM stock_quant"},
    )
    result = await orch.run(
        fresh_state(query="how much stock do we have?", session_id="t1")
    )
    assert result["intent"] == "supply_chain_question"
    assert "stock_quant" in result["composed_sql"]
    assert result["confidence"] > 0
    assert result["final_error"] == ""


# ───── multi-domain composition ──────────────────────────────────────


async def test_multi_domain_composes_via_ctes() -> None:
    """Phase 5: real Composer produces CTE-based merges, not UNION ALL."""
    decision = RouterDecision(
        intent="supply_chain_question",
        domains=(Domain.INVENTORY, Domain.FINANCE),
        sub_queries=(
            SubQuery(domain=Domain.INVENTORY, natural_language="stock?"),
            SubQuery(domain=Domain.FINANCE, natural_language="revenue?"),
        ),
        reasoning="both",
    )
    orch = _make_orchestrator(
        router_decision=decision,
        agent_sqls={
            Domain.INVENTORY: "SELECT 'i' AS d, count(*) AS n FROM stock_quant",
            Domain.FINANCE: "SELECT 'f' AS d, sum(credit) AS total FROM account_move",
        },
    )
    result = await orch.run(
        fresh_state(query="stock and revenue last quarter", session_id="t2")
    )
    sql = result["composed_sql"]
    assert "WITH" in sql.upper()
    assert "q_inventory" in sql
    assert "q_finance" in sql
    assert "stock_quant" in sql
    assert "account_move" in sql
    # No-shared-key fallback should produce a CROSS JOIN
    assert "CROSS JOIN" in sql.upper() or "INNER JOIN" in sql.upper()


# ───── out-of-scope short-circuits ───────────────────────────────────


async def test_out_of_scope_skips_generation() -> None:
    decision = RouterDecision(
        intent="out_of_scope",
        domains=(),
        sub_queries=(),
        reasoning="unrelated",
    )
    orch = _make_orchestrator(
        router_decision=decision,
        agent_sqls={Domain.INVENTORY: "should not run"},
    )
    result = await orch.run(
        fresh_state(query="what's the weather like?", session_id="t3")
    )
    assert result["intent"] == "out_of_scope"
    assert result["composed_sql"] == ""
    assert "outside" in result["final_error"].lower()


async def test_clarification_skips_generation() -> None:
    decision = RouterDecision(
        intent="clarification_needed",
        domains=(),
        sub_queries=(),
        reasoning="ambiguous lead time",
    )
    orch = _make_orchestrator(
        router_decision=decision,
        agent_sqls={Domain.INVENTORY: "should not run"},
    )
    result = await orch.run(
        fresh_state(query="lead time", session_id="t4")
    )
    assert result["intent"] == "clarification_needed"
    assert "ambiguous" in result["final_error"].lower()


# ───── self-correction loop ──────────────────────────────────────────


async def test_empty_sql_triggers_retry_then_gives_up() -> None:
    decision = RouterDecision(
        intent="supply_chain_question",
        domains=(Domain.INVENTORY,),
        sub_queries=(
            SubQuery(domain=Domain.INVENTORY, natural_language="x"),
        ),
        reasoning="",
    )
    orch = _make_orchestrator(
        router_decision=decision,
        agent_sqls={Domain.INVENTORY: ""},   # empty SQL — validator rejects
    )
    result = await orch.run(
        fresh_state(query="x", session_id="t5")
    )
    assert result["final_error"]
    # After 3 attempts we give up
    assert result["attempt"] == 3


# ───── message log captures the flow ─────────────────────────────────


async def test_message_log_records_full_flow() -> None:
    decision = RouterDecision(
        intent="supply_chain_question",
        domains=(Domain.DEMAND,),
        sub_queries=(SubQuery(domain=Domain.DEMAND, natural_language="orders?"),),
        reasoning="",
    )
    orch = _make_orchestrator(
        router_decision=decision,
        agent_sqls={Domain.DEMAND: "SELECT 1 FROM sale_order"},
    )
    await orch.run(fresh_state(query="orders last week", session_id="t6"))
    log = orch.message_log()
    msgs = log.by_correlation("t6")
    kinds = [m.kind for m in msgs]
    assert MessageKind.QUERY in kinds
    assert MessageKind.SUB_QUERY in kinds
    assert MessageKind.AGENT_OUTPUT in kinds
    assert MessageKind.FINAL in kinds

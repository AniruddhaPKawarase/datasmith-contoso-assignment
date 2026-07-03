"""Tests for LLMDomainAgent + SQL extraction helpers."""
from __future__ import annotations

from app.agents.specialists import (
    FewShot,
    LLMDomainAgent,
    build_specialists,
    extract_sql,
    load_few_shots,
    tables_referenced,
)
from app.llm import LLMResponse
from app.schema.domains import Domain, load_domain_mapping
from app.schema.glossary import load_glossary
from app.schema.metadata import (
    Column,
    SchemaMetadata,
    Table,
)
from app.schema.search import SchemaSearch

# ───── SQL extraction ────────────────────────────────────────────────


def test_extract_sql_bare_select() -> None:
    out = extract_sql("SELECT 1 FROM t WHERE id = 2")
    assert out == "SELECT 1 FROM t WHERE id = 2;"


def test_extract_sql_with_markdown_fence() -> None:
    out = extract_sql("Sure!\n```sql\nSELECT 2 FROM t\n```\nDone.")
    assert "SELECT 2 FROM t" in out
    assert out.endswith(";")


def test_extract_sql_with_prose() -> None:
    response = "Here is the SQL:\nSELECT count(*) FROM stock_quant;\n\nLet me know."
    out = extract_sql(response)
    assert out.startswith("SELECT count(*)")


def test_extract_sql_out_of_domain() -> None:
    assert extract_sql("OUT_OF_DOMAIN") == ""
    assert extract_sql("Sorry, OUT_OF_DOMAIN.") == ""


def test_extract_sql_no_sql_returns_empty() -> None:
    assert extract_sql("I don't know") == ""


def test_tables_referenced_picks_up_joins() -> None:
    sql = (
        "SELECT * FROM stock_move sm "
        "JOIN product_product pp ON pp.id = sm.product_id "
        "LEFT JOIN stock_location l ON l.id = sm.location_id"
    )
    tables = tables_referenced(sql)
    assert "stock_move" in tables
    assert "product_product" in tables
    assert "stock_location" in tables


def test_tables_referenced_lowercases() -> None:
    sql = "SELECT * FROM Account_Move JOIN res_partner"
    assert "account_move" in tables_referenced(sql)
    assert "res_partner" in tables_referenced(sql)


# ───── Few-shot loading ──────────────────────────────────────────────


def test_load_few_shots_real_files() -> None:
    for d in (Domain.INVENTORY, Domain.LOGISTICS, Domain.FINANCE, Domain.DEMAND):
        shots = load_few_shots(d)
        assert len(shots) >= 5, f"{d.value} should have ≥5 curated examples"
        for fs in shots:
            assert fs.query.strip()
            assert fs.sql.strip()


# ───── LLMDomainAgent end-to-end with mocked LLM ─────────────────────


def _toy_meta() -> SchemaMetadata:
    cols = (
        Column(name="id", data_type="int", is_nullable=False, is_primary_key=True),
        Column(name="quantity", data_type="numeric", is_nullable=True),
        Column(name="product_id", data_type="int", is_nullable=True),
    )
    return SchemaMetadata(
        database="t", schema="public", extracted_at="now",
        tables=(
            Table(name="stock_quant", columns=cols, foreign_keys=(),
                  odoo_model="stock.quant", odoo_description="Stock"),
            Table(name="stock_warehouse", columns=cols, foreign_keys=(),
                  odoo_model="stock.warehouse", odoo_description="Warehouse"),
        ),
    )


class _FakeLLM:
    def __init__(self, text: str) -> None:
        self._text = text
        self.calls = 0
        self.last_messages: dict[str, str] = {}

    async def generate(self, **kwargs: object) -> LLMResponse:
        self.calls += 1
        self.last_messages = {
            "system": str(kwargs.get("system", "")),
            "user": str(kwargs.get("user", "")),
        }
        return LLMResponse(
            text=self._text, model="test", provider="fake",
            prompt_tokens=10, completion_tokens=5,
            latency_ms=1, finish_reason="stop",
        )

    async def aclose(self) -> None:
        return None


def _make_agent(*, domain: Domain, llm_text: str) -> LLMDomainAgent:
    meta = _toy_meta()
    mapping = load_domain_mapping()
    glossary = load_glossary()
    search = SchemaSearch(meta)
    return LLMDomainAgent(
        domain=domain,
        few_shots=(FewShot(query="ex", sql="SELECT 1 FROM stock_quant;"),),
        llm=_FakeLLM(llm_text),  # type: ignore[arg-type]
        metadata=meta,
        mapping=mapping,
        glossary=glossary,
        search=search,
    )


async def test_specialist_returns_clean_sql() -> None:
    agent = _make_agent(
        domain=Domain.INVENTORY,
        llm_text="SELECT id, quantity FROM stock_quant WHERE quantity > 0",
    )
    result = await agent.generate_sql("what stock do we have?")
    assert "stock_quant" in result.sql
    assert result.used_tables == ("stock_quant",)
    assert result.confidence > 0


async def test_specialist_rejects_out_of_scope_tables() -> None:
    agent = _make_agent(
        domain=Domain.INVENTORY,
        llm_text="SELECT * FROM account_move",      # not in visible set
    )
    result = await agent.generate_sql("revenue?")
    assert result.sql == ""
    assert "outside" in result.rationale.lower() or "domain" in result.rationale.lower()


async def test_specialist_handles_out_of_domain_token() -> None:
    agent = _make_agent(
        domain=Domain.INVENTORY,
        llm_text="OUT_OF_DOMAIN",
    )
    result = await agent.generate_sql("what's the weather?")
    assert result.sql == ""
    assert result.confidence == 0.0


async def test_specialist_includes_few_shots_in_prompt() -> None:
    agent = _make_agent(
        domain=Domain.INVENTORY,
        llm_text="SELECT 1 FROM stock_quant",
    )
    await agent.generate_sql("show me stock")
    user_msg = agent._llm.last_messages["user"]  # type: ignore[attr-defined]
    assert "Few-shot examples" in user_msg
    assert "ex" in user_msg                  # query of our fake few-shot


async def test_specialist_system_prompt_lists_visible_tables() -> None:
    agent = _make_agent(
        domain=Domain.INVENTORY,
        llm_text="SELECT 1 FROM stock_quant",
    )
    sys = agent.system_prompt()
    assert "INVENTORY" in sys.upper()
    assert "Visible tables" in sys


def test_build_specialists_creates_four_domains() -> None:
    meta = _toy_meta()
    mapping = load_domain_mapping()
    glossary = load_glossary()
    search = SchemaSearch(meta)
    llm = _FakeLLM("SELECT 1")
    out = build_specialists(
        llm=llm,                                  # type: ignore[arg-type]
        metadata=meta, mapping=mapping,
        glossary=glossary, search=search,
    )
    assert set(out.keys()) == {Domain.INVENTORY, Domain.LOGISTICS,
                                 Domain.FINANCE, Domain.DEMAND}
    # Each agent has its own domain set on the instance
    for d, agent in out.items():
        assert agent.domain == d

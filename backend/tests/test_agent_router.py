"""Tests for the RouterAgent — parsing, fallback, ambiguity hints."""
from __future__ import annotations

import pytest

from app.agents.router import RouterAgent
from app.llm import LLMResponse
from app.schema.domains import Domain, load_domain_mapping
from app.schema.glossary import load_glossary


class _FakeLLM:
    """Stand-in LLMProvider that returns a canned response."""

    def __init__(self, text: str, *, raise_exc: Exception | None = None) -> None:
        self._text = text
        self._raise = raise_exc
        self.calls = 0

    async def generate(self, **kwargs: object) -> LLMResponse:
        self.calls += 1
        if self._raise is not None:
            raise self._raise
        return LLMResponse(
            text=self._text,
            model="test",
            provider="fake",
            prompt_tokens=10,
            completion_tokens=5,
            latency_ms=1,
            finish_reason="stop",
        )

    async def aclose(self) -> None:
        return None


@pytest.fixture
def real_mapping_and_glossary():
    return load_domain_mapping(), load_glossary()


async def test_router_parses_clean_json(real_mapping_and_glossary) -> None:
    mapping, glossary = real_mapping_and_glossary
    llm = _FakeLLM(
        '{"intent": "supply_chain_question", "domains": ["inventory", "finance"], '
        '"sub_queries": [{"domain": "inventory", "natural_language": "stock?"}], '
        '"reasoning": "asked about stock and cost"}'
    )
    router = RouterAgent(llm=llm, mapping=mapping, glossary=glossary)  # type: ignore[arg-type]
    decision = await router.route("how much stock do we have and at what cost?")
    assert decision.intent == "supply_chain_question"
    assert Domain.INVENTORY in decision.domains
    assert Domain.FINANCE in decision.domains
    assert decision.fallback_used is False
    assert decision.sub_queries[0].domain == Domain.INVENTORY


async def test_router_falls_back_on_llm_exception(real_mapping_and_glossary) -> None:
    mapping, glossary = real_mapping_and_glossary
    llm = _FakeLLM("", raise_exc=RuntimeError("network down"))
    router = RouterAgent(llm=llm, mapping=mapping, glossary=glossary)  # type: ignore[arg-type]
    decision = await router.route("show stock level by warehouse")
    assert decision.fallback_used is True
    # Keyword 'stock level' is one of inventory's keywords
    assert Domain.INVENTORY in decision.domains


async def test_router_clarifies_when_no_keywords_match(real_mapping_and_glossary) -> None:
    mapping, glossary = real_mapping_and_glossary
    llm = _FakeLLM("", raise_exc=RuntimeError("boom"))
    router = RouterAgent(llm=llm, mapping=mapping, glossary=glossary)  # type: ignore[arg-type]
    decision = await router.route("what is the meaning of life?")
    assert decision.intent == "clarification_needed"
    assert decision.fallback_used is True
    assert decision.domains == ()


async def test_router_rejects_unknown_intent(real_mapping_and_glossary) -> None:
    """Invalid 'intent' values are coerced to 'supply_chain_question'."""
    mapping, glossary = real_mapping_and_glossary
    llm = _FakeLLM('{"intent": "made_up", "domains": ["finance"]}')
    router = RouterAgent(llm=llm, mapping=mapping, glossary=glossary)  # type: ignore[arg-type]
    decision = await router.route("revenue last year")
    assert decision.intent == "supply_chain_question"


async def test_router_handles_malformed_json(real_mapping_and_glossary) -> None:
    mapping, glossary = real_mapping_and_glossary
    llm = _FakeLLM("not json at all { broken")
    router = RouterAgent(llm=llm, mapping=mapping, glossary=glossary)  # type: ignore[arg-type]
    decision = await router.route("show me stock")
    # Falls back to keyword path
    assert decision.fallback_used is True


async def test_router_skips_unknown_domains_in_response(real_mapping_and_glossary) -> None:
    mapping, glossary = real_mapping_and_glossary
    llm = _FakeLLM(
        '{"intent": "supply_chain_question", '
        '"domains": ["inventory", "marketing", "logistics"], "sub_queries": []}'
    )
    router = RouterAgent(llm=llm, mapping=mapping, glossary=glossary)  # type: ignore[arg-type]
    decision = await router.route("inventory and logistics")
    assert Domain.INVENTORY in decision.domains
    assert Domain.LOGISTICS in decision.domains
    assert len(decision.domains) == 2  # marketing dropped

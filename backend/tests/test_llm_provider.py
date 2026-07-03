"""Tests for LLMProvider across all backends with respx-mocked HTTP."""
from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
import respx

from app.llm.config import LLMConfig, ModelTask
from app.llm.provider import LLMProvider, LLMProviderError


@pytest.fixture
async def provider(llm_config: LLMConfig) -> AsyncIterator[LLMProvider]:
    p = LLMProvider(llm_config)
    try:
        yield p
    finally:
        await p.aclose()


# ───── OpenAI ─────────────────────────────────────────────────────────


@respx.mock
async def test_openai_success(
    monkeypatch: pytest.MonkeyPatch, provider: LLMProvider
) -> None:
    monkeypatch.setenv("LLM_MODEL_SQL_GEN", "openai/gpt-4o-mini")
    cfg = LLMConfig.from_env()
    p = LLMProvider(cfg)
    respx.post("https://test.openai.local/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "SELECT 1;"}, "finish_reason": "stop"}
                ],
                "usage": {"prompt_tokens": 42, "completion_tokens": 8},
            },
        )
    )
    resp = await p.generate(
        task=ModelTask.SQL_GEN, system="sql expert", user="hello"
    )
    assert resp.text == "SELECT 1;"
    assert resp.provider == "openai"
    assert resp.model == "gpt-4o-mini"
    assert resp.prompt_tokens == 42
    await p.aclose()


# ───── Anthropic ──────────────────────────────────────────────────────


@respx.mock
async def test_anthropic_success(provider: LLMProvider) -> None:
    respx.post("https://test.anthropic.local/v1/messages").mock(
        return_value=httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": "SELECT 2;"}],
                "usage": {"input_tokens": 33, "output_tokens": 4},
                "stop_reason": "end_turn",
            },
        )
    )
    # Default config routes SQL_GEN to anthropic/claude-haiku-4-5
    resp = await provider.generate(
        task=ModelTask.SQL_GEN, system="sql expert", user="hello"
    )
    assert resp.text == "SELECT 2;"
    assert resp.provider == "anthropic"
    assert resp.model == "claude-haiku-4-5"
    assert resp.prompt_tokens == 33
    assert resp.completion_tokens == 4


# ───── Fallback ───────────────────────────────────────────────────────


@respx.mock
async def test_falls_back_when_primary_fails(provider: LLMProvider) -> None:
    # Primary (anthropic) blows up
    respx.post("https://test.anthropic.local/v1/messages").mock(
        return_value=httpx.Response(500, json={"error": "boom"})
    )
    # Fallback (openai) succeeds
    respx.post("https://test.openai.local/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "fallback ok"}, "finish_reason": "stop"}
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 3},
            },
        )
    )
    resp = await provider.generate(
        task=ModelTask.SQL_GEN, system="sql expert", user="hello"
    )
    assert resp.text == "fallback ok"
    assert resp.provider == "openai"


@respx.mock
async def test_raises_when_both_fail(provider: LLMProvider) -> None:
    respx.post("https://test.anthropic.local/v1/messages").mock(
        return_value=httpx.Response(500)
    )
    respx.post("https://test.openai.local/v1/chat/completions").mock(
        return_value=httpx.Response(500)
    )
    with pytest.raises(LLMProviderError):
        await provider.generate(
            task=ModelTask.SQL_GEN, system="sql expert", user="hello"
        )


async def test_missing_openai_key_raises_when_no_anthropic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("LLM_MODEL_SQL_GEN", "openai/gpt-4o-mini")
    monkeypatch.setenv("LLM_FALLBACK_MODEL", "anthropic/claude-haiku-4-5")
    cfg = LLMConfig.from_env()
    p = LLMProvider(cfg)
    try:
        with pytest.raises(LLMProviderError):
            await p.generate(
                task=ModelTask.SQL_GEN, system="s", user="u"
            )
    finally:
        await p.aclose()


# ───── Ollama (offline fallback path) ─────────────────────────────────


@respx.mock
async def test_ollama_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODEL_SQL_GEN", "ollama/qwen2.5-coder:7b")
    cfg = LLMConfig.from_env()
    p = LLMProvider(cfg)
    respx.post("http://test.ollama.local:11434/api/chat").mock(
        return_value=httpx.Response(
            200,
            json={
                "message": {"content": "local sql"},
                "prompt_eval_count": 10,
                "eval_count": 5,
            },
        )
    )
    resp = await p.generate(task=ModelTask.SQL_GEN, system="s", user="u")
    assert resp.provider == "ollama"
    assert resp.text == "local sql"
    await p.aclose()


# ───── OpenRouter (bare prefix compatibility) ─────────────────────────


@respx.mock
async def test_openrouter_with_subpath(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODEL_SQL_GEN", "openrouter/qwen/qwen3-coder:free")
    cfg = LLMConfig.from_env()
    p = LLMProvider(cfg)
    respx.post("https://test.openrouter.local/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "or sql"}, "finish_reason": "stop"}
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 2},
            },
        )
    )
    resp = await p.generate(task=ModelTask.SQL_GEN, system="s", user="u")
    assert resp.provider == "openrouter"
    assert resp.model == "qwen/qwen3-coder:free"
    await p.aclose()

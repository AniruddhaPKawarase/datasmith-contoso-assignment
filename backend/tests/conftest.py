"""Pytest fixtures."""
from __future__ import annotations

import pytest

from app.llm.config import LLMConfig


@pytest.fixture(autouse=True)
def _set_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://test.openai.local/v1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://test.anthropic.local/v1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://test.openrouter.local/api/v1")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://test.ollama.local:11434")
    monkeypatch.setenv("LLM_FALLBACK_MODEL", "openai/gpt-4o-mini")


@pytest.fixture
def llm_config() -> LLMConfig:
    return LLMConfig.from_env()

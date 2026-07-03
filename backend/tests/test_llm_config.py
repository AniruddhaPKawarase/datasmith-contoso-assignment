"""Tests for LLMConfig env resolution and model routing."""
from __future__ import annotations

import dataclasses

import pytest

from app.llm.config import LLMConfig, ModelTask, ProviderKind


def test_config_resolves_all_tasks(llm_config: LLMConfig) -> None:
    """Every ModelTask must have a configured model."""
    for task in ModelTask:
        assert llm_config.model_for(task), f"{task} has no model"


def test_config_is_immutable(llm_config: LLMConfig) -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        llm_config.openai_api_key = "mutated"  # type: ignore[misc]


def test_config_loads_test_env(llm_config: LLMConfig) -> None:
    assert llm_config.openai_api_key == "test-openai"
    assert llm_config.anthropic_api_key == "test-anthropic"
    assert llm_config.openrouter_api_key == "test-openrouter"


def test_parse_model_anthropic() -> None:
    kind, model = LLMConfig.parse_model("anthropic/claude-haiku-4-5")
    assert kind == ProviderKind.ANTHROPIC
    assert model == "claude-haiku-4-5"


def test_parse_model_openai() -> None:
    kind, model = LLMConfig.parse_model("openai/gpt-4o-mini")
    assert kind == ProviderKind.OPENAI
    assert model == "gpt-4o-mini"


def test_parse_model_ollama() -> None:
    kind, model = LLMConfig.parse_model("ollama/qwen2.5-coder:7b")
    assert kind == ProviderKind.OLLAMA
    assert model == "qwen2.5-coder:7b"


def test_parse_model_openrouter_with_subpath() -> None:
    """OpenRouter model ids have their own slashes — preserve the remainder."""
    kind, model = LLMConfig.parse_model("openrouter/qwen/qwen3-coder:free")
    assert kind == ProviderKind.OPENROUTER
    assert model == "qwen/qwen3-coder:free"


def test_parse_model_unknown_prefix_falls_back_to_openrouter() -> None:
    """Unknown prefixes default to OpenRouter for compatibility."""
    kind, model = LLMConfig.parse_model("vendor-x/some-model")
    assert kind == ProviderKind.OPENROUTER
    assert model == "vendor-x/some-model"


def test_parse_model_no_prefix_defaults_to_openrouter() -> None:
    kind, model = LLMConfig.parse_model("bare-model-id")
    assert kind == ProviderKind.OPENROUTER
    assert model == "bare-model-id"

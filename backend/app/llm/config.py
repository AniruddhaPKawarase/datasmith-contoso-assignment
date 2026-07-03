"""LLM configuration — model routing per task, multi-provider settings."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import StrEnum


class ModelTask(StrEnum):
    """Tasks that need an LLM. Each maps to a model in LLMConfig.task_models."""

    ROUTER = "router"          # Intent classification + domain routing
    SQL_GEN = "sql_gen"        # Domain-agent SQL generation
    COMPOSER = "composer"      # Cross-domain SQL composition
    VALIDATOR = "validator"    # SQL validation + error diagnosis
    AMBIGUITY = "ambiguity"    # Ambiguity detection + clarifying questions
    TEMPORAL = "temporal"      # Temporal expression normalisation (light fallback)
    EXPLAIN = "explain"        # NL explanation of generated SQL


class ProviderKind(StrEnum):
    """Supported LLM backends. Models are prefixed `<kind>/<model>`."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"


@dataclass(frozen=True)
class LLMConfig:
    """Immutable LLM configuration.

    Resolved from env at startup. Never mutate — create a new instance to change.
    Model identifiers use the form ``<provider>/<model_id>``, e.g.::

        anthropic/claude-haiku-4-5
        openai/gpt-4o-mini
        ollama/qwen2.5-coder:7b
        openrouter/qwen/qwen3-coder:free
    """

    openai_api_key: str
    openai_base_url: str
    anthropic_api_key: str
    anthropic_base_url: str
    anthropic_api_version: str
    ollama_base_url: str
    openrouter_api_key: str
    openrouter_base_url: str
    fallback_model: str
    task_models: dict[ModelTask, str] = field(default_factory=dict)
    request_timeout_s: float = 60.0
    max_retries: int = 2

    @classmethod
    def from_env(cls) -> LLMConfig:
        task_models = {
            ModelTask.ROUTER: os.getenv("LLM_MODEL_ROUTER", "openai/gpt-4o-mini"),
            ModelTask.SQL_GEN: os.getenv("LLM_MODEL_SQL_GEN", "anthropic/claude-haiku-4-5"),
            ModelTask.COMPOSER: os.getenv("LLM_MODEL_COMPOSER", "anthropic/claude-haiku-4-5"),
            ModelTask.VALIDATOR: os.getenv("LLM_MODEL_VALIDATOR", "anthropic/claude-haiku-4-5"),
            ModelTask.AMBIGUITY: os.getenv("LLM_MODEL_AMBIGUITY", "openai/gpt-4o-mini"),
            ModelTask.TEMPORAL: os.getenv("LLM_MODEL_TEMPORAL", "anthropic/claude-haiku-4-5"),
            ModelTask.EXPLAIN: os.getenv("LLM_MODEL_EXPLAIN", "openai/gpt-4o-mini"),
        }
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            anthropic_base_url=os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1"),
            anthropic_api_version=os.getenv("ANTHROPIC_API_VERSION", "2023-06-01"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            openrouter_base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            fallback_model=os.getenv("LLM_FALLBACK_MODEL", "ollama/qwen2.5-coder:7b"),
            task_models=task_models,
        )

    def model_for(self, task: ModelTask) -> str:
        return self.task_models[task]

    @staticmethod
    def parse_model(model: str) -> tuple[ProviderKind, str]:
        """Split ``provider/model_id`` into (ProviderKind, model_id).

        Defaults to OpenRouter if no recognised prefix is supplied — preserves
        backwards compatibility with bare OpenRouter slugs.
        """
        if "/" not in model:
            return ProviderKind.OPENROUTER, model
        head, _, rest = model.partition("/")
        try:
            return ProviderKind(head), rest
        except ValueError:
            return ProviderKind.OPENROUTER, model

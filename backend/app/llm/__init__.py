"""LLM abstraction layer.

All model calls go through `provider.LLMProvider`. Switching between
OpenRouter and Ollama is a config change, not a code change.
"""

from app.llm.config import LLMConfig, ModelTask, ProviderKind
from app.llm.provider import LLMProvider, LLMProviderError, LLMResponse

__all__ = [
    "LLMConfig",
    "LLMProvider",
    "LLMProviderError",
    "LLMResponse",
    "ModelTask",
    "ProviderKind",
]

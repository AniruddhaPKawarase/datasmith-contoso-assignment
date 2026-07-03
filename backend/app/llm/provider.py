"""Unified LLM provider interface — multi-backend with automatic fallback.

Supported backends:
    - openai      → https://api.openai.com/v1/chat/completions
    - anthropic   → https://api.anthropic.com/v1/messages
    - openrouter  → https://openrouter.ai/api/v1/chat/completions
    - ollama      → local inference, OpenAI-compatible chat endpoint

Routing happens via the model id prefix, e.g. ``openai/gpt-4o-mini``.
Every model call in the codebase must go through ``LLMProvider.generate()``.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.llm.config import LLMConfig, ModelTask, ProviderKind

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMResponse:
    """Immutable LLM response."""

    text: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    finish_reason: str


class LLMProviderError(Exception):
    """Raised when both primary and fallback providers fail."""


class LLMProvider:
    """Multi-backend LLM provider with automatic fallback.

    The primary backend is decided per-task by the model id's prefix
    (``openai/...``, ``anthropic/...``, ``ollama/...``, ``openrouter/...``).
    On any failure the provider falls back to ``config.fallback_model``.

    Usage::

        cfg = LLMConfig.from_env()
        provider = LLMProvider(cfg)
        resp = await provider.generate(
            task=ModelTask.SQL_GEN,
            system="You are a SQL expert.",
            user="Show me top 10 products by sales.",
        )
    """

    def __init__(self, config: LLMConfig) -> None:
        self._cfg = config
        self._client = httpx.AsyncClient(timeout=config.request_timeout_s)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def generate(
        self,
        task: ModelTask,
        system: str,
        user: str,
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Generate completion, falling back to ``config.fallback_model`` on failure."""
        primary_model = self._cfg.model_for(task)
        try:
            return await self._dispatch(
                model=primary_model,
                system=system,
                user=user,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
            )
        except Exception as exc:
            logger.warning(
                "Primary provider failed (%s) for task %s, falling back to %s",
                exc,
                task.value,
                self._cfg.fallback_model,
            )
            if self._cfg.fallback_model == primary_model:
                raise LLMProviderError(f"Primary failed and no distinct fallback: {exc}") from exc
            try:
                return await self._dispatch(
                    model=self._cfg.fallback_model,
                    system=system,
                    user=user,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                )
            except Exception as fb_exc:
                raise LLMProviderError(
                    f"Primary failed ({exc}); fallback failed ({fb_exc})"
                ) from fb_exc

    async def _dispatch(
        self,
        *,
        model: str,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> LLMResponse:
        kind, model_id = LLMConfig.parse_model(model)
        if kind == ProviderKind.OPENAI:
            return await self._call_openai(
                model_id, system, user, temperature, max_tokens, json_mode
            )
        if kind == ProviderKind.ANTHROPIC:
            return await self._call_anthropic(
                model_id, system, user, temperature, max_tokens
            )
        if kind == ProviderKind.OLLAMA:
            return await self._call_ollama(model_id, system, user, temperature, max_tokens)
        return await self._call_openrouter(
            model_id, system, user, temperature, max_tokens, json_mode
        )

    # ───── OpenAI ─────────────────────────────────────────────────────

    async def _call_openai(
        self,
        model: str,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> LLMResponse:
        if not self._cfg.openai_api_key:
            raise LLMProviderError("OPENAI_API_KEY not set")
        url = f"{self._cfg.openai_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._cfg.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        data = await self._post_with_retry(url, payload, headers)
        choice = data["choices"][0]
        usage = data.get("usage", {})
        return LLMResponse(
            text=choice["message"]["content"],
            model=model,
            provider="openai",
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_ms=data.get("_latency_ms", 0),
            finish_reason=choice.get("finish_reason", "stop"),
        )

    # ───── Anthropic ──────────────────────────────────────────────────

    async def _call_anthropic(
        self,
        model: str,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        if not self._cfg.anthropic_api_key:
            raise LLMProviderError("ANTHROPIC_API_KEY not set")
        url = f"{self._cfg.anthropic_base_url}/messages"
        headers = {
            "x-api-key": self._cfg.anthropic_api_key,
            "anthropic-version": self._cfg.anthropic_api_version,
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        data = await self._post_with_retry(url, payload, headers)
        # Anthropic returns content as a list of blocks, each with type+text.
        blocks = data.get("content", [])
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        usage = data.get("usage", {})
        return LLMResponse(
            text=text,
            model=model,
            provider="anthropic",
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
            latency_ms=data.get("_latency_ms", 0),
            finish_reason=data.get("stop_reason", "end_turn"),
        )

    # ───── OpenRouter ─────────────────────────────────────────────────

    async def _call_openrouter(
        self,
        model: str,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> LLMResponse:
        if not self._cfg.openrouter_api_key:
            raise LLMProviderError("OPENROUTER_API_KEY not set")
        url = f"{self._cfg.openrouter_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._cfg.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        data = await self._post_with_retry(url, payload, headers)
        choice = data["choices"][0]
        usage = data.get("usage", {})
        return LLMResponse(
            text=choice["message"]["content"],
            model=model,
            provider="openrouter",
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_ms=data.get("_latency_ms", 0),
            finish_reason=choice.get("finish_reason", "stop"),
        )

    # ───── Ollama ─────────────────────────────────────────────────────

    async def _call_ollama(
        self,
        model: str,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        url = f"{self._cfg.ollama_base_url}/api/chat"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        start = time.perf_counter()
        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        latency_ms = int((time.perf_counter() - start) * 1000)
        return LLMResponse(
            text=data["message"]["content"],
            model=model,
            provider="ollama",
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            latency_ms=latency_ms,
            finish_reason="stop",
        )

    # ───── Shared retry helper ────────────────────────────────────────

    async def _post_with_retry(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        """POST with exponential backoff. Embeds ``_latency_ms`` into the JSON."""
        start = time.perf_counter()
        last_exc: Exception | None = None
        for attempt in range(self._cfg.max_retries + 1):
            try:
                resp = await self._client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data: dict[str, Any] = resp.json()
                data["_latency_ms"] = int((time.perf_counter() - start) * 1000)
                return data
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt < self._cfg.max_retries:
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue
                raise
        raise LLMProviderError(f"Exhausted retries: {last_exc}")

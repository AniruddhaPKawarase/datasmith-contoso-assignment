"""Token usage tracking for cost monitoring and ablation studies."""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from threading import Lock

from app.llm.config import ModelTask
from app.llm.provider import LLMResponse

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TokenSnapshot:
    """Immutable per-task token accounting snapshot."""

    task: ModelTask
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    call_count: int


class TokenTracker:
    """Thread-safe in-process token accounting.

    For production, swap for an MLflow-backed implementation. For dev + tests,
    this is enough.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._by_task: dict[ModelTask, dict[str, int]] = defaultdict(
            lambda: {"prompt": 0, "completion": 0, "latency_ms": 0, "calls": 0}
        )
        self._models_seen: dict[ModelTask, tuple[str, str]] = {}

    def record(self, task: ModelTask, response: LLMResponse) -> None:
        with self._lock:
            bucket = self._by_task[task]
            bucket["prompt"] += response.prompt_tokens
            bucket["completion"] += response.completion_tokens
            bucket["latency_ms"] += response.latency_ms
            bucket["calls"] += 1
            self._models_seen[task] = (response.model, response.provider)

    def snapshot(self) -> list[TokenSnapshot]:
        with self._lock:
            out: list[TokenSnapshot] = []
            for task, bucket in self._by_task.items():
                model, provider = self._models_seen.get(task, ("?", "?"))
                out.append(
                    TokenSnapshot(
                        task=task,
                        model=model,
                        provider=provider,
                        prompt_tokens=bucket["prompt"],
                        completion_tokens=bucket["completion"],
                        latency_ms=bucket["latency_ms"],
                        call_count=bucket["calls"],
                    )
                )
            return out

    def reset(self) -> None:
        with self._lock:
            self._by_task.clear()
            self._models_seen.clear()

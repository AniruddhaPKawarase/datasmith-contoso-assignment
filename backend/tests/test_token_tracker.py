"""Tests for TokenTracker accounting."""
from __future__ import annotations

from app.llm.config import ModelTask
from app.llm.provider import LLMResponse
from app.llm.token_tracker import TokenTracker


def _resp(prompt: int, completion: int) -> LLMResponse:
    return LLMResponse(
        text="x",
        model="qwen-test",
        provider="openrouter",
        prompt_tokens=prompt,
        completion_tokens=completion,
        latency_ms=42,
        finish_reason="stop",
    )


def test_tracker_aggregates_per_task() -> None:
    tracker = TokenTracker()
    tracker.record(ModelTask.SQL_GEN, _resp(10, 20))
    tracker.record(ModelTask.SQL_GEN, _resp(30, 40))
    tracker.record(ModelTask.ROUTER, _resp(5, 5))

    snap = {s.task: s for s in tracker.snapshot()}
    assert snap[ModelTask.SQL_GEN].prompt_tokens == 40
    assert snap[ModelTask.SQL_GEN].completion_tokens == 60
    assert snap[ModelTask.SQL_GEN].call_count == 2
    assert snap[ModelTask.ROUTER].call_count == 1


def test_tracker_reset_clears() -> None:
    tracker = TokenTracker()
    tracker.record(ModelTask.SQL_GEN, _resp(1, 1))
    tracker.reset()
    assert tracker.snapshot() == []

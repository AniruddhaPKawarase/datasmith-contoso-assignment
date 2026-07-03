"""Tests for ConversationMemory."""
from __future__ import annotations

from app.agents.memory import ConversationMemory
from app.schema.domains import Domain


def _record(mem: ConversationMemory, session: str, q: str) -> None:
    mem.record_turn(
        session_id=session,
        user_query=q,
        domains_used=(Domain.INVENTORY,),
        generated_sql="SELECT 1",
        row_count=1,
        summary="ok",
    )


def test_record_and_window() -> None:
    m = ConversationMemory(window_size=3)
    for i in range(2):
        _record(m, "s1", f"q{i}")
    summary, recent = m.active_window("s1")
    assert summary == ""
    assert len(recent) == 2


def test_window_compresses_older() -> None:
    m = ConversationMemory(window_size=2)
    for i in range(5):
        _record(m, "s1", f"q{i}")
    summary, recent = m.active_window("s1")
    assert len(recent) == 2
    assert "Turn 1" in summary
    assert "Turn 2" in summary
    assert "Turn 3" in summary
    assert "Turn 4" not in summary  # still in active window


def test_unknown_session_returns_empty() -> None:
    m = ConversationMemory()
    summary, recent = m.active_window("ghost")
    assert summary == "" and recent == ()


def test_reset_clears_session() -> None:
    m = ConversationMemory()
    _record(m, "s1", "q")
    m.reset("s1")
    assert m.active_window("s1") == ("", ())


def test_eviction_when_max_reached() -> None:
    m = ConversationMemory(max_sessions=2)
    _record(m, "a", "q")
    _record(m, "b", "q")
    _record(m, "c", "q")
    assert m.session_count() == 2
    # 'a' was evicted (LRU)
    assert m.active_window("a") == ("", ())
    assert m.active_window("c")[1]

"""Tests for the agent message protocol."""
from __future__ import annotations

import dataclasses

import pytest

from app.agents.messages import AgentMessage, MessageKind, MessageLog


def test_make_creates_unique_ids() -> None:
    a = AgentMessage.make(
        correlation_id="c", kind=MessageKind.QUERY,
        from_agent="user", to_agent="router",
    )
    b = AgentMessage.make(
        correlation_id="c", kind=MessageKind.QUERY,
        from_agent="user", to_agent="router",
    )
    assert a.id != b.id


def test_message_immutable() -> None:
    m = AgentMessage.make(
        correlation_id="c", kind=MessageKind.QUERY,
        from_agent="u", to_agent="r",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.from_agent = "x"  # type: ignore[misc]


def test_log_filters_by_correlation() -> None:
    log = MessageLog()
    log.append(AgentMessage.make(
        correlation_id="A", kind=MessageKind.QUERY,
        from_agent="u", to_agent="r",
    ))
    log.append(AgentMessage.make(
        correlation_id="B", kind=MessageKind.QUERY,
        from_agent="u", to_agent="r",
    ))
    assert len(log.by_correlation("A")) == 1
    assert len(log.by_correlation("B")) == 1
    assert len(log.all()) == 2


def test_log_clear() -> None:
    log = MessageLog()
    log.append(AgentMessage.make(
        correlation_id="A", kind=MessageKind.QUERY,
        from_agent="u", to_agent="r",
    ))
    log.clear()
    assert log.all() == ()

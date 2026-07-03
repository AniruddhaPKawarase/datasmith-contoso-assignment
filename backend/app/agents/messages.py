"""Agent communication protocol.

Even though the LangGraph state passes data between nodes implicitly, we
keep an explicit log of every meaningful inter-agent message. This gives us:

1. **Auditability** — every domain agent's contribution is traceable in the
   compliance log (required by Objective #7 in the abstract).
2. **Debuggability** — replay a session by reading the message stream.
3. **Future federation** — when we split agents into remote workers (post-
   dissertation), the same message format is the wire protocol.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class MessageKind(StrEnum):
    """The kinds of messages agents exchange."""

    QUERY = "query"                      # user query into the orchestrator
    SUB_QUERY = "sub_query"              # Router -> domain agent
    AGENT_OUTPUT = "agent_output"        # domain agent -> Composer
    COMPOSED_SQL = "composed_sql"        # Composer -> Validator
    VALIDATION = "validation"            # Validator -> orchestrator
    EXECUTION = "execution"              # DB -> orchestrator
    CLARIFICATION = "clarification"      # any agent -> user
    ERROR = "error"
    FINAL = "final"                      # orchestrator -> user


@dataclass(frozen=True)
class AgentMessage:
    """One unit of communication in the agent graph."""

    id: str
    correlation_id: str                  # groups all messages from one user query
    timestamp: str                       # ISO-8601
    kind: MessageKind
    from_agent: str                      # "user" | "router" | "inventory" | ...
    to_agent: str                        # "router" | "composer" | "user" | ...
    payload: dict[str, Any] = field(default_factory=dict)
    attempt: int = 1                     # which self-correction attempt produced this

    @classmethod
    def make(
        cls,
        *,
        correlation_id: str,
        kind: MessageKind,
        from_agent: str,
        to_agent: str,
        payload: dict[str, Any] | None = None,
        attempt: int = 1,
    ) -> AgentMessage:
        return cls(
            id=str(uuid.uuid4()),
            correlation_id=correlation_id,
            timestamp=datetime.now(UTC).isoformat(timespec="milliseconds"),
            kind=kind,
            from_agent=from_agent,
            to_agent=to_agent,
            payload=dict(payload or {}),
            attempt=attempt,
        )


class MessageLog:
    """In-memory message log. Production swaps for SQLite/Postgres-backed."""

    def __init__(self) -> None:
        self._messages: list[AgentMessage] = []

    def append(self, msg: AgentMessage) -> None:
        self._messages.append(msg)

    def by_correlation(self, correlation_id: str) -> list[AgentMessage]:
        return [m for m in self._messages if m.correlation_id == correlation_id]

    def all(self) -> tuple[AgentMessage, ...]:
        return tuple(self._messages)

    def clear(self) -> None:
        self._messages.clear()

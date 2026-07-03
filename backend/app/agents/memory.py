"""Multi-turn conversation memory.

Each session is a sequence of ``Turn`` objects. The active window
(``window_size`` most recent turns) feeds the agent prompts directly;
older turns get compressed into a single rolling summary.

Reference resolution (pronouns, "compare with last year", etc.) is the
caller's responsibility — this module only stores and retrieves.
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.schema.domains import Domain


@dataclass(frozen=True)
class Turn:
    """One question/answer pair."""

    turn_id: int
    timestamp: str                       # ISO-8601
    user_query: str
    domains_used: tuple[Domain, ...]
    generated_sql: str
    row_count: int
    summary: str                         # short NL summary of the answer

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "timestamp": self.timestamp,
            "user_query": self.user_query,
            "domains_used": [d.value for d in self.domains_used],
            "generated_sql": self.generated_sql,
            "row_count": self.row_count,
            "summary": self.summary,
        }


@dataclass
class Session:
    """One user's conversation history."""

    session_id: str
    turns: list[Turn] = field(default_factory=list)
    older_summary: str = ""              # rolling compressed summary

    def next_turn_id(self) -> int:
        return len(self.turns) + 1


class ConversationMemory:
    """Thread-safe in-process store of sessions.

    Window: ``window_size`` most recent turns kept verbatim. Anything older
    is folded into ``older_summary`` (compression is a no-op by default —
    swap in an LLM-driven compressor in Phase 7).
    """

    def __init__(
        self,
        window_size: int = 5,
        max_sessions: int = 1024,
    ) -> None:
        self._lock = threading.Lock()
        self._sessions: OrderedDict[str, Session] = OrderedDict()
        self._window = window_size
        self._max = max_sessions

    def get(self, session_id: str) -> Session:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                session = Session(session_id=session_id)
                self._sessions[session_id] = session
            self._sessions.move_to_end(session_id)
            self._evict_if_needed_locked()
            return session

    def record_turn(
        self,
        session_id: str,
        *,
        user_query: str,
        domains_used: tuple[Domain, ...],
        generated_sql: str,
        row_count: int,
        summary: str,
    ) -> Turn:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                session = Session(session_id=session_id)
                self._sessions[session_id] = session
            turn = Turn(
                turn_id=session.next_turn_id(),
                timestamp=datetime.now(UTC).isoformat(timespec="seconds"),
                user_query=user_query,
                domains_used=domains_used,
                generated_sql=generated_sql,
                row_count=row_count,
                summary=summary,
            )
            session.turns.append(turn)
            self._compress_if_needed_locked(session)
            self._sessions.move_to_end(session_id)
            self._evict_if_needed_locked()
            return turn

    def active_window(
        self, session_id: str
    ) -> tuple[str, tuple[Turn, ...]]:
        """Return (older_summary, recent_turns_in_order)."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return "", ()
            window = tuple(session.turns[-self._window:])
            return session.older_summary, window

    def reset(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def session_count(self) -> int:
        return len(self._sessions)

    # ── internal ──────────────────────────────────────────────────────

    def _compress_if_needed_locked(self, session: Session) -> None:
        if len(session.turns) <= self._window:
            return
        overflow = session.turns[: -self._window]
        session.turns = session.turns[-self._window:]
        summary_lines = [session.older_summary] if session.older_summary else []
        for t in overflow:
            summary_lines.append(
                f"Turn {t.turn_id}: '{t.user_query}' "
                f"({len(t.domains_used)} domains, {t.row_count} rows)"
            )
        session.older_summary = "\n".join(s for s in summary_lines if s).strip()

    def _evict_if_needed_locked(self) -> None:
        while len(self._sessions) > self._max:
            self._sessions.popitem(last=False)

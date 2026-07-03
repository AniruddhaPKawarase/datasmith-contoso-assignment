"""Build the conversation-context block injected into agent prompts."""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.conversation.references import ReferenceDecision, ReferenceKind

if TYPE_CHECKING:
    from app.agents.memory import Turn


class ConversationContextBuilder:
    """Render the active conversation window for the agent prompt.

    The block is intentionally compact (~10 lines) so it doesn't crowd
    out schema context. Older turns are folded into a single summary
    line by ``ConversationMemory``; only the most recent turn is shown
    in full.
    """

    def __init__(self, max_recent_turns: int = 3) -> None:
        self._max_recent = max_recent_turns

    def build(
        self,
        *,
        recent_turns: tuple[Turn, ...],
        older_summary: str = "",
        reference: ReferenceDecision | None = None,
    ) -> str:
        if not recent_turns and not older_summary:
            return ""

        kept = recent_turns[-self._max_recent:]
        lines: list[str] = ["## Prior conversation (use to resolve pronouns / refinements)"]

        if older_summary:
            lines.append(f"Older context: {older_summary}")

        for t in kept:
            domains = ",".join(d.value for d in t.domains_used) or "-"
            sql_oneline = " ".join(t.generated_sql.split())[:240]
            ellipsis = "..." if len(sql_oneline) == 240 else ""
            lines.append(
                f"- Turn {t.turn_id} [{domains}] '{t.user_query}'"
            )
            if sql_oneline:
                lines.append(f"    SQL: {sql_oneline}{ellipsis}")
            if t.summary:
                lines.append(f"    Summary: {t.summary[:120]}")

        if reference is not None and not reference.is_new_topic:
            triggers = ", ".join(reference.triggers) or "n/a"
            lines.append(
                f"\nThis turn is classified as **{reference.kind.value}** "
                f"(triggers: {triggers})."
            )
            lines.append(self._guidance(reference.kind))

        return "\n".join(lines)

    @staticmethod
    def _guidance(kind: ReferenceKind) -> str:
        if kind == ReferenceKind.REFINEMENT:
            return (
                "Add a WHERE-clause predicate to the prior turn's SQL "
                "without changing its FROM/JOIN shape."
            )
        if kind == ReferenceKind.COMPARISON:
            return (
                "Produce a result with one row per period being compared "
                "(prior result vs the new period). Reuse the prior SELECT list."
            )
        if kind == ReferenceKind.FOLLOW_UP:
            return (
                "Resolve pronouns to entities from the most-recent SQL "
                "result. Drill one level deeper if the user asks 'why?'."
            )
        return ""

"""MAC-SQL baseline reimplementation.

Reference paper:
    Wang B., Ren C., Yang J., Liang X., Bai J., Zhang Q., Yan Z., Li Z.,
    Sun Z.  *MAC-SQL: A Multi-Agent Collaborative Framework for Text-to-SQL.*
    COLING 2025  ·  arXiv 2312.11242.
    Cached locally at docs/paper/01_MAC-SQL_Wang_COLING2025.pdf.

We reimplement MAC-SQL's three-agent pipeline against our existing
``LLMProvider`` so the head-to-head holds the LLM backbone constant
(fairness contract — see EVALUATION_FRAMEWORK §5):

    Selector   — schema-link the question to a relevant table subset
    Decomposer — break the NL question into sub-questions and emit SQL
    Refiner    — given execution feedback, refine SQL up to N times

The three agents share the same claude-haiku-4-5 backbone as our system,
the same prompt token budget (≤4 000 tokens per call), and the same
3-attempt correction cap.

This is **not** a port of their public code; it is a faithful
reimplementation of the algorithm described in §3 of the paper, using
the same prompt structure but our infrastructure adapters. The
methodological argument is *"both systems get the same model and the
same schema; the only difference is the architecture"*.
"""
from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass

from app.agents.specialists import extract_sql, tables_referenced
from app.llm import LLMProvider, ModelTask
from app.llm.token_tracker import TokenTracker
from app.schema.metadata import SchemaMetadata
from app.schema.search import SchemaSearch

ExecutorFn = Callable[[str], tuple[bool, str]]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BaselineOutput:
    """Common return type for any baseline's ``predict`` method."""

    sql: str
    used_tables: tuple[str, ...]
    attempts: int                       # 1..N
    notes: str = ""


_SELECTOR_SYSTEM = """\
You are the Schema-Linker for a Text-to-SQL system. Given a natural-
language question and a catalogue of database tables, return ONLY
the tables relevant to answering the question.

Reply with ONLY a JSON array of table names, e.g.
    ["account_move", "res_partner"]
"""


_DECOMPOSER_SYSTEM = """\
You are the SQL Decomposer for a Text-to-SQL system. Given a natural-
language question and a list of relevant tables (with their columns),
write ONE valid PostgreSQL statement that answers the question.

If the question is complex, break it into mental sub-questions and
solve each with a CTE; combine the CTEs into a final SELECT.

Output ONLY the SQL — no markdown, no commentary. End with a semicolon.
"""


_REFINER_SYSTEM = """\
You are the SQL Refiner for a Text-to-SQL system. Given a previous SQL
attempt that failed with an execution error, write a corrected
PostgreSQL statement that addresses the error.

Output ONLY the corrected SQL — no markdown, no commentary. End with
a semicolon.
"""


class MacSqlBaseline:
    """Pipeline-axis multi-agent baseline.

    Parameters
    ----------
    llm            : the shared ``LLMProvider``  (same one our system uses)
    metadata       : full schema introspection cache (498 tables)
    search         : the same ``SchemaSearch`` our system uses
    max_correction : MAC-SQL's Refiner attempt budget (default 3)
    tracker        : optional ``TokenTracker`` to bill MAC-SQL's API spend
    """

    def __init__(
        self,
        *,
        llm: LLMProvider,
        metadata: SchemaMetadata,
        search: SchemaSearch,
        max_correction: int = 3,
        tracker: TokenTracker | None = None,
    ) -> None:
        self._llm = llm
        self._meta = metadata
        self._search = search
        self._max_correction = max_correction
        self._tracker = tracker

    # ── public API (matches the orchestrator's expected shape) ────────

    async def predict(
        self,
        query: str,
        *,
        history_summary: str = "",
        executor: ExecutorFn | None = None,
    ) -> BaselineOutput:
        """Run the full Selector → Decomposer → Refiner pipeline.

        If ``executor`` is provided, it will be called with the candidate
        SQL after the Decomposer step; an error string is fed back into
        the Refiner. Without ``executor`` we run Decomposer only once
        (i.e. degenerate to a 2-stage pipeline).
        """
        selected = await self._selector(query)
        candidate = await self._decomposer(query, selected)
        attempts = 1

        # Refiner loop
        last_error = ""
        while executor is not None and attempts < self._max_correction:
            ok, err = executor(candidate)
            if ok:
                break
            last_error = err
            candidate = await self._refiner(query, selected, candidate, err)
            attempts += 1

        return BaselineOutput(
            sql=candidate,
            used_tables=tables_referenced(candidate),
            attempts=attempts,
            notes=("ok" if not last_error else f"final-err: {last_error[:120]}"),
        )

    # ── stage implementations ─────────────────────────────────────────

    async def _selector(self, query: str) -> tuple[str, ...]:
        """Schema-link: return the top-k relevant tables as a tuple."""
        hits = self._search.search(query, top_k=12)
        table_names = tuple(h.table for h in hits)
        # Build a compact catalogue snippet for the LLM call so it can
        # confirm or prune.
        cat = []
        for t_name in table_names:
            t = self._meta.table(t_name)
            if t is None:
                continue
            desc = t.odoo_description or ""
            cat.append(f"  - {t.name}  ({desc})")
        catalogue = "\n".join(cat)

        user = (
            f"Question:\n{query}\n\n"
            f"Candidate tables (from BM25 retrieval):\n{catalogue}\n\n"
            "Return the JSON array of the tables that are actually "
            "needed to answer this question (subset of the candidates)."
        )
        raw = await self._call_llm(
            system=_SELECTOR_SYSTEM, user=user,
            task=ModelTask.ROUTER, max_tokens=300,
        )
        # Parse a JSON array out of the response, tolerating prose.
        match = re.search(r"\[[^\]]*\]", raw, re.DOTALL)
        if not match:
            return table_names[:6]            # fallback: top-6 from BM25
        try:
            import json
            picked = json.loads(match.group(0))
        except (json.JSONDecodeError, ValueError):
            return table_names[:6]
        valid = tuple(
            t for t in picked
            if isinstance(t, str) and self._meta.table(t) is not None
        )
        return valid if valid else table_names[:6]

    async def _decomposer(
        self, query: str, selected: tuple[str, ...]
    ) -> str:
        """Emit one PostgreSQL statement."""
        schema_block = self._render_schema(selected)
        user = (
            f"## Selected tables and columns\n{schema_block}\n\n"
            f"## Question\n{query.strip()}\n\n"
            "Output ONE valid PostgreSQL statement."
        )
        raw = await self._call_llm(
            system=_DECOMPOSER_SYSTEM, user=user,
            task=ModelTask.SQL_GEN, max_tokens=900,
        )
        return extract_sql(raw)

    async def _refiner(
        self,
        query: str,
        selected: tuple[str, ...],
        prior_sql: str,
        prior_error: str,
    ) -> str:
        """Given an execution error, regenerate corrected SQL."""
        schema_block = self._render_schema(selected)
        user = (
            f"## Selected tables and columns\n{schema_block}\n\n"
            f"## Question\n{query.strip()}\n\n"
            f"## Previous SQL attempt\n{prior_sql}\n\n"
            f"## Execution error\n{prior_error}\n\n"
            "Output the corrected PostgreSQL statement only."
        )
        raw = await self._call_llm(
            system=_REFINER_SYSTEM, user=user,
            task=ModelTask.VALIDATOR, max_tokens=900,
        )
        return extract_sql(raw)

    # ── helpers ───────────────────────────────────────────────────────

    def _render_schema(self, selected: tuple[str, ...]) -> str:
        lines: list[str] = []
        for t_name in selected:
            t = self._meta.table(t_name)
            if t is None:
                continue
            lines.append(f"### {t.name}  — {t.odoo_description}")
            for col in t.columns[:18]:        # cap for token budget
                desc = f"  -- {col.description}" if col.description else ""
                lines.append(f"  {col.name}  ({col.data_type}){desc}")
            if len(t.columns) > 18:
                lines.append(f"  ... +{len(t.columns) - 18} more cols")
            lines.append("")
        return "\n".join(lines)

    async def _call_llm(self, *, system: str, user: str,
                        task: ModelTask, max_tokens: int) -> str:
        resp = await self._llm.generate(
            task=task, system=system, user=user,
            temperature=0.0, max_tokens=max_tokens,
        )
        if self._tracker is not None:
            self._tracker.record(task, resp)
        return resp.text

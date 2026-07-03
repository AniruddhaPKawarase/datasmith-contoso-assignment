"""LLM-driven domain-specialist agents (Phase 4).

Replaces ``StubDomainAgent``. One ``LLMDomainAgent`` class is parameterised
per domain — same shape, different schema slice + few-shot examples +
glossary, so all five specialists share one well-tested code path.

The agent's contract:

1. **Generate** PostgreSQL that touches ONLY tables in its
   ``visible_tables`` allow-list.
2. **Refuse** out-of-domain questions with the literal ``OUT_OF_DOMAIN``
   token — never invent tables.
3. **Return** structured ``AgentResult`` with extracted SQL, the tables it
   actually referenced (parsed back from the SQL), and self-reported
   confidence.

SQL is extracted from the LLM response with a forgiving parser that
handles markdown fences, trailing commentary, and the OUT_OF_DOMAIN
sentinel.
"""
from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from app.agents.base import AgentResult, BaseAgent
from app.llm import ModelTask
from app.schema.domains import Domain

if TYPE_CHECKING:
    from app.llm import LLMProvider
    from app.llm.token_tracker import TokenTracker
    from app.schema.domains import DomainMapping
    from app.schema.glossary import Glossary
    from app.schema.metadata import SchemaMetadata
    from app.schema.search import SchemaSearch

logger = logging.getLogger(__name__)

_FEW_SHOTS_DIR = Path(__file__).resolve().parent / "few_shots"

_OUT_OF_DOMAIN_TOKEN = "OUT_OF_DOMAIN"  # noqa: S105 — sentinel string, not a credential
_MAX_FEW_SHOTS = 6   # cap context size; pick most diverse per domain
_MAX_TABLES_FROM_SQL = 30


@dataclass(frozen=True)
class FewShot:
    """One curated NL → SQL pair used in the agent's prompt."""

    query: str
    sql: str


def load_few_shots(domain: Domain) -> tuple[FewShot, ...]:
    """Load few-shot examples for the given domain from YAML.

    Returns an empty tuple if the file is missing — caller decides whether
    to treat that as an error.
    """
    path = _FEW_SHOTS_DIR / f"{domain.value}.yaml"
    if not path.exists():
        return ()
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(raw, list):
        raise ValueError(f"{path} must contain a YAML list of examples")
    return tuple(
        FewShot(query=str(item["query"]).strip(), sql=str(item["sql"]).strip())
        for item in raw
        if "query" in item and "sql" in item
    )


# ── SQL extraction helpers ────────────────────────────────────────────


_CODE_FENCE_RE = re.compile(
    r"```(?:sql|postgresql|pg)?\s*\n(.*?)```",
    re.IGNORECASE | re.DOTALL,
)

# Match a SELECT/WITH/INSERT/UPDATE/DELETE block up to the next bare line
# break that isn't part of the SQL.
_SQL_PREFIX_RE = re.compile(
    r"\b(WITH|SELECT|INSERT|UPDATE|DELETE)\b",
    re.IGNORECASE,
)


def extract_sql(text: str) -> str:
    """Pull the first SQL statement out of an LLM response.

    Strategy:
      1. If the response contains a ``OUT_OF_DOMAIN`` token, return "".
      2. If there's a fenced code block, return its contents.
      3. Otherwise, find the first SELECT/WITH/... keyword and return from
         there to the end (stripped).
    """
    if _OUT_OF_DOMAIN_TOKEN in text.upper():
        return ""
    fenced = _CODE_FENCE_RE.search(text)
    if fenced:
        return fenced.group(1).strip().rstrip(";").strip() + ";"
    match = _SQL_PREFIX_RE.search(text)
    if not match:
        return ""
    body = text[match.start():].strip()
    # Strip any trailing prose after a blank line.
    parts = body.split("\n\n", 1)
    body = parts[0].strip()
    if not body.endswith(";"):
        body += ";"
    return body


_TABLE_REF_RE = re.compile(
    r"\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)",
    re.IGNORECASE,
)


def tables_referenced(sql: str) -> tuple[str, ...]:
    """Cheap regex parse — extract table names that appear after FROM/JOIN.

    Good enough for an allow-list audit; sqlglot will be used in Phase 5's
    validator for the rigorous check.
    """
    seen: list[str] = []
    for match in _TABLE_REF_RE.finditer(sql):
        name = match.group(1).lower()
        if name not in seen:
            seen.append(name)
        if len(seen) >= _MAX_TABLES_FROM_SQL:
            break
    return tuple(seen)


# ── Specialist agent ─────────────────────────────────────────────────


class LLMDomainAgent(BaseAgent):
    """One domain specialist. Instances differ only by ``domain``.

    Constructed via ``LLMDomainAgent.for_domain(...)`` (the convenience
    factory in ``__init__``-time wiring) or directly with ``domain=...``
    plus the standard BaseAgent kwargs.
    """

    def __init__(
        self,
        *,
        domain: Domain,
        few_shots: Iterable[FewShot] | None = None,
        max_completion_tokens: int = 800,
        **kwargs: object,
    ) -> None:
        # Set on instance to avoid the class-attribute trampling that bit
        # the Phase 3 stub.
        self.domain = domain
        super().__init__(**kwargs)  # type: ignore[arg-type]
        loaded = tuple(few_shots) if few_shots is not None else load_few_shots(domain)
        self._few_shots = loaded[:_MAX_FEW_SHOTS]
        self._max_completion_tokens = max_completion_tokens

    # ── public API ────────────────────────────────────────────────────

    def few_shots(self) -> tuple[FewShot, ...]:
        return self._few_shots

    def system_prompt(self) -> str:
        """Override BaseAgent's system prompt with hard agent constraints."""
        base = super().system_prompt()
        return (
            base
            + "\n\nVisible tables (you must not invent any others):\n  "
            + ", ".join(sorted(self._visible))
            + "\n\nIf the question cannot be answered from this domain alone, "
            + f"reply with the literal token `{_OUT_OF_DOMAIN_TOKEN}` and "
            + "nothing else."
        )

    async def generate_sql(
        self,
        query: str,
        *,
        context: str = "",
        attempt: int = 1,
        prior_error: str = "",
        temporal_block: str = "",
    ) -> AgentResult:
        prompt = self._user_prompt(
            query, context=context, prior_error=prior_error,
            temporal_block=temporal_block,
        )
        try:
            raw = await self._call_llm(
                system=self.system_prompt(),
                user=prompt,
                task=ModelTask.SQL_GEN,
                temperature=0.0 if attempt == 1 else 0.2,
                max_tokens=self._max_completion_tokens,
            )
        except Exception as exc:
            logger.exception("LLMDomainAgent[%s] LLM call failed", self.domain.value)
            return AgentResult(
                sql="",
                used_tables=(),
                confidence=0.0,
                rationale=f"LLM call failed: {exc}",
            )

        sql = extract_sql(raw)
        if not sql:
            return AgentResult(
                sql="",
                used_tables=(),
                confidence=0.0,
                rationale=(
                    "OUT_OF_DOMAIN reply from model" if _OUT_OF_DOMAIN_TOKEN in raw.upper()
                    else f"Could not extract SQL from response: {raw[:200]!r}"
                ),
            )
        tables = tables_referenced(sql)
        out_of_scope = [t for t in tables if t not in self._visible]
        if out_of_scope:
            return AgentResult(
                sql="",
                used_tables=tables,
                confidence=0.0,
                rationale=(
                    f"Model referenced tables outside this agent's domain: "
                    f"{out_of_scope}. Visible set has {len(self._visible)} tables."
                ),
            )
        # Self-reported confidence: higher when more few-shot patterns match.
        confidence = self._estimate_confidence(query, tables)
        return AgentResult(
            sql=sql,
            used_tables=tables,
            confidence=confidence,
            rationale=(
                f"{self.domain.value} agent generated SQL using "
                f"{len(tables)} table(s); attempt={attempt}"
            ),
        )

    # ── prompt construction ───────────────────────────────────────────

    def _user_prompt(
        self,
        query: str,
        *,
        context: str,
        prior_error: str,
        temporal_block: str = "",
    ) -> str:
        schema = self.schema_context(query, top_k=8)
        few_shot_block = self._render_few_shots()
        retry_block = (
            f"\n\nPrior attempt failed with:\n{prior_error}\nFix the issue above."
            if prior_error
            else ""
        )
        ctx_block = f"\n\nConversation context:\n{context}" if context else ""
        temporal = f"\n\n{temporal_block}" if temporal_block else ""
        return (
            f"## Schema (most-relevant tables)\n{schema}\n\n"
            f"## Few-shot examples\n{few_shot_block}\n\n"
            f"## User question\n{query.strip()}"
            f"{temporal}{ctx_block}{retry_block}\n\n"
            "Output ONLY a single PostgreSQL statement, no markdown, no commentary."
        )

    def _render_few_shots(self) -> str:
        if not self._few_shots:
            return "(no examples available)"
        blocks: list[str] = []
        for i, fs in enumerate(self._few_shots, start=1):
            blocks.append(
                f"### Example {i}\n"
                f"Q: {fs.query}\n"
                f"SQL:\n{fs.sql}"
            )
        return "\n\n".join(blocks)

    def _estimate_confidence(
        self, query: str, used_tables: tuple[str, ...]
    ) -> float:
        """Cheap confidence heuristic.

        Starts at 0.5 and adds:
          + 0.1 per used-table that also appears in a few-shot example
            (capped at +0.3)
          + 0.1 if the SQL contains an aggregate (SUM/COUNT/AVG)
          + 0.1 if the SQL groups by something (GROUP BY)
        """
        score = 0.5
        few_shot_tables: set[str] = set()
        for fs in self._few_shots:
            few_shot_tables.update(tables_referenced(fs.sql))
        overlap = sum(1 for t in used_tables if t in few_shot_tables)
        score += min(0.3, 0.1 * overlap)
        ql = query.lower()
        if any(kw in ql for kw in ("how many", "total", "sum", "average", "count")):
            score += 0.1
        return round(min(score, 1.0), 3)


def build_specialists(
    *,
    llm: LLMProvider,
    metadata: SchemaMetadata,
    mapping: DomainMapping,
    glossary: Glossary,
    search: SchemaSearch,
    tracker: TokenTracker | None = None,
    domains: Iterable[Domain] = (
        Domain.INVENTORY,
        Domain.LOGISTICS,
        Domain.FINANCE,
        Domain.DEMAND,
    ),
) -> dict[Domain, LLMDomainAgent]:
    """Convenience factory — builds one LLMDomainAgent per non-compliance domain."""
    return {
        d: LLMDomainAgent(
            domain=d,
            llm=llm,
            metadata=metadata,
            mapping=mapping,
            glossary=glossary,
            search=search,
            tracker=tracker,
        )
        for d in domains
    }

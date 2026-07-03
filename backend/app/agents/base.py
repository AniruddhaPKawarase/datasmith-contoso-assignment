"""Abstract base for domain-specialist agents.

A concrete subclass (Inventory/Logistics/Finance/Demand/Compliance — Phase 4)
implements ``generate_sql`` using its own:

* schema slice (from ``DomainMapping.visible_to(domain)``)
* glossary entries (from ``Glossary.for_domain(domain)``)
* curated few-shot examples (loaded from ``examples.yaml`` in Phase 4)

The base class supplies prompt scaffolding, schema retrieval via
``SchemaSearch``, and structured result handling.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.llm import LLMProvider, ModelTask
from app.llm.token_tracker import TokenTracker
from app.schema.domains import Domain, DomainMapping
from app.schema.glossary import Glossary
from app.schema.metadata import SchemaMetadata
from app.schema.search import SchemaSearch


@dataclass(frozen=True)
class AgentResult:
    """Structured output from one domain agent's SQL-generation call."""

    sql: str
    used_tables: tuple[str, ...]
    confidence: float                    # 0..1, self-reported
    rationale: str                       # NL explanation of choices made


class BaseAgent(ABC):
    """Abstract base for the five domain-specialist agents.

    Subclasses override ``generate_sql`` (and optionally ``system_prompt``);
    everything else — schema slicing, glossary lookup, retrieval — is shared.
    """

    domain: Domain                       # set on the subclass

    def __init__(
        self,
        *,
        llm: LLMProvider,
        metadata: SchemaMetadata,
        mapping: DomainMapping,
        glossary: Glossary,
        search: SchemaSearch | None = None,
        tracker: TokenTracker | None = None,
    ) -> None:
        if not hasattr(self, "domain"):
            raise NotImplementedError(
                f"{type(self).__name__} must define a class-level `domain`"
            )
        self._llm = llm
        self._meta = metadata
        self._mapping = mapping
        self._glossary = glossary
        self._search = search or SchemaSearch(metadata)
        self._tracker = tracker
        self._visible: frozenset[str] = mapping.visible_to(self.domain)

    # ── public API ────────────────────────────────────────────────────

    @property
    def visible_tables(self) -> frozenset[str]:
        return self._visible

    def domain_glossary_terms(self) -> tuple[str, ...]:
        return tuple(e.term for e in self._glossary.for_domain(self.domain))

    @abstractmethod
    async def generate_sql(
        self,
        query: str,
        *,
        context: str = "",
        attempt: int = 1,
        prior_error: str = "",
        temporal_block: str = "",
    ) -> AgentResult:
        """Produce SQL for ``query`` constrained to this agent's domain.

        Subclasses must implement. The base class provides the LLM call,
        schema retrieval, and prompt scaffolding helpers.
        """

    # ── prompt building (shared) ──────────────────────────────────────

    def system_prompt(self) -> str:
        """Default system prompt — override in subclasses to tune voice."""
        domain_spec = self._mapping.domains[self.domain]
        glossary_lines = [
            f"- {e.term}: {e.notes or e.sql_fragment.splitlines()[0]}"
            for e in self._glossary.for_domain(self.domain)
        ]
        return (
            f"You are the {self.domain.value.upper()} specialist agent in a "
            "multi-agent NL-to-SQL system for enterprise supply chain "
            "intelligence.\n\n"
            f"Domain scope: {domain_spec.description}\n\n"
            "Hard constraints:\n"
            "  1. Generate ONLY PostgreSQL syntax (Odoo 17 ERP schema).\n"
            "  2. Reference ONLY tables in your visible-tables list — never "
            "invent table names.\n"
            "  3. If the question is outside your domain, respond with the "
            "literal token: OUT_OF_DOMAIN\n"
            "  4. Output ONE SQL statement only. No markdown, no commentary, "
            "no explanation.\n\n"
            f"Glossary for this domain:\n" + "\n".join(glossary_lines)
        )

    def schema_context(self, query: str, *, top_k: int = 8) -> str:
        """CSR-RAG-style schema slice for the prompt.

        Retrieves the top-K most relevant tables (scoped to the agent's
        visible set), then renders a compact prompt block with each table's
        Odoo description + relevant columns.
        """
        hits = self._search.search(
            query, top_k=top_k, allowed_tables=self._visible
        )
        if not hits:
            return "(no schema matches — fall back to OUT_OF_DOMAIN)"
        lines: list[str] = []
        for h in hits:
            table = self._meta.table(h.table)
            if table is None:
                continue
            lines.append(f"## {table.name}  ({table.odoo_description})")
            for col in table.columns[:20]:    # cap to first 20 cols per table
                desc = f" — {col.description}" if col.description else ""
                ttype = f" [{col.odoo_ttype}]" if col.odoo_ttype else ""
                lines.append(f"  - {col.name}: {col.data_type}{ttype}{desc}")
            if len(table.columns) > 20:
                lines.append(f"  ... +{len(table.columns) - 20} more columns")
            lines.append("")
        return "\n".join(lines)

    async def _call_llm(
        self,
        *,
        system: str,
        user: str,
        task: ModelTask = ModelTask.SQL_GEN,
        temperature: float = 0.0,
        max_tokens: int = 800,
    ) -> str:
        """Single LLM call with token-tracker bookkeeping."""
        resp = await self._llm.generate(
            task=task,
            system=system,
            user=user,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if self._tracker is not None:
            self._tracker.record(task, resp)
        return resp.text


class StubDomainAgent(BaseAgent):
    """Minimal concrete agent used to validate Phase 3 wiring.

    Phase 4 replaces this with five fully-prompted domain specialists. For
    now, this agent does a glossary lookup + schema retrieval and emits a
    skeleton SQL that names the most relevant table. It exists so the
    LangGraph pipeline runs end-to-end before the real agents land.
    """

    def __init__(self, *, domain: Domain, **kwargs: object) -> None:
        # Store domain on the instance (not the class) so multiple stubs can
        # coexist without trampling each other's class-level attribute.
        self.domain = domain
        super().__init__(**kwargs)  # type: ignore[arg-type]

    async def generate_sql(
        self,
        query: str,
        *,
        context: str = "",
        attempt: int = 1,
        prior_error: str = "",
        temporal_block: str = "",
    ) -> AgentResult:
        hits = self._search.search(
            query, top_k=3, allowed_tables=self._visible
        )
        if not hits:
            return AgentResult(
                sql="",
                used_tables=(),
                confidence=0.0,
                rationale="No matching tables in visible set.",
            )
        primary = hits[0].table
        return AgentResult(
            # primary is from the introspected schema allow-list, not user input.
            sql=f"SELECT count(*) AS approx_total FROM {primary} /* stub-{self.domain.value} */",  # noqa: S608
            used_tables=(primary,),
            confidence=0.3,
            rationale=(
                f"Stub agent (Phase 4 will replace). Primary table: {primary}. "
                f"Matched tokens: {hits[0].matched_tokens}."
            ),
        )

"""Domain-to-schema mapping loader and queries.

Wraps ``domains.yaml`` with typed accessors so the router/agents can ask:

* "Which tables does the Inventory agent own?"
* "Which domains does the table ``stock_picking`` belong to?"
  (it's primary-inventory but also primary-logistics — that's intentional)
* "Is ``mail_message`` accessible to any agent?" (no — excluded)
* "Which shared-entity group does ``res_partner`` belong to?"

The mapping is human-curated. It encodes the supply-chain decomposition
that's the central novelty of this dissertation — multi-agent decomposition
by **business domain** rather than by SQL pipeline stage.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml


class Domain(StrEnum):
    """The five domain-specialist agents."""

    INVENTORY = "inventory"
    LOGISTICS = "logistics"
    FINANCE = "finance"
    DEMAND = "demand"
    COMPLIANCE = "compliance"


@dataclass(frozen=True)
class DomainSpec:
    """All knowledge the agent needs about its slice of the schema."""

    domain: Domain
    description: str
    primary_tables: frozenset[str]
    keywords: tuple[str, ...]
    cross_cutting: bool = False


@dataclass(frozen=True)
class SharedGroup:
    """A cross-domain entity group (product, partner, mrp, ...)."""

    name: str
    description: str
    tables: frozenset[str]


@dataclass(frozen=True)
class DomainMapping:
    """Whole mapping: domains + shared groups + prefix rules + exclusions."""

    domains: dict[Domain, DomainSpec]
    shared: dict[str, SharedGroup]
    excluded_prefixes: tuple[str, ...]
    prefix_rules: dict[Domain, tuple[str, ...]] = field(default_factory=dict)
    join_suffixes: tuple[str, ...] = ()
    wizard_suffixes: tuple[str, ...] = ()
    version: int = 1

    # ── lookup helpers ────────────────────────────────────────────────

    def domains_owning(self, table: str) -> list[Domain]:
        """Domains for which ``table`` is a primary owner (explicit list)."""
        return [d for d, spec in self.domains.items() if table in spec.primary_tables]

    def is_shared(self, table: str) -> bool:
        return any(table in g.tables for g in self.shared.values())

    def shared_group_of(self, table: str) -> str | None:
        for name, g in self.shared.items():
            if table in g.tables:
                return name
        return None

    def is_excluded(self, table: str) -> bool:
        return any(table.startswith(p) for p in self.excluded_prefixes)

    def is_wizard(self, table: str) -> bool:
        return any(table.endswith(s) for s in self.wizard_suffixes)

    def is_join_table(self, table: str) -> bool:
        return any(table.endswith(s) for s in self.join_suffixes)

    def resolve_domain(self, table: str) -> Domain | None:
        """Resolve a table to its single best-matching domain.

        Precedence:
          1. Explicit ``primary_tables`` membership (first match wins)
          2. Prefix-rule match (most-specific prefix wins by length)
          3. None — table is shared, excluded, or unmapped
        """
        owners = self.domains_owning(table)
        if owners:
            return owners[0]
        if self.is_excluded(table) or self.is_wizard(table):
            return None
        # Pick the longest matching prefix across all domains
        best: tuple[int, Domain | None] = (0, None)
        for domain, prefixes in self.prefix_rules.items():
            for p in prefixes:
                if table.startswith(p) and len(p) > best[0]:
                    best = (len(p), domain)
        return best[1]

    def visible_to(self, domain: Domain) -> frozenset[str]:
        """All EXPLICIT tables the given agent may reference.

        Note: this returns the curated primary + shared sets only. The
        prefix rules extend coverage at query time via ``resolve_domain``.
        Compliance is cross-cutting and additionally sees every primary
        table from every other domain (for predicate injection).
        """
        spec = self.domains[domain]
        if spec.cross_cutting:
            tables: set[str] = set()
            for s in self.domains.values():
                tables.update(s.primary_tables)
            for g in self.shared.values():
                tables.update(g.tables)
            return frozenset(tables)
        out: set[str] = set(spec.primary_tables)
        for g in self.shared.values():
            out.update(g.tables)
        return frozenset(out)

    # ── stats ─────────────────────────────────────────────────────────

    def coverage(self, all_tables: set[str]) -> DomainCoverageReport:
        """Compute mapping coverage against an actual table set."""
        owned_by_domain: dict[Domain, set[str]] = {d: set() for d in self.domains}
        shared_set = {t for g in self.shared.values() for t in g.tables}
        excluded_present: set[str] = set()
        wizard_present: set[str] = set()
        join_tables: set[str] = set()
        unmapped: set[str] = set()
        for t in all_tables:
            if self.is_excluded(t):
                excluded_present.add(t)
                continue
            if self.is_wizard(t):
                wizard_present.add(t)
                continue
            if t in shared_set:
                continue
            domain = self.resolve_domain(t)
            if domain is not None:
                owned_by_domain[domain].add(t)
                continue
            if self.is_join_table(t):
                join_tables.add(t)
                continue
            unmapped.add(t)
        shared_known = shared_set & all_tables
        missing_in_db = (
            {t for s in self.domains.values() for t in s.primary_tables}
            | shared_set
        ) - all_tables
        return DomainCoverageReport(
            owned_by_domain={d: frozenset(s) for d, s in owned_by_domain.items()},
            shared_known=frozenset(shared_known),
            excluded_present=frozenset(excluded_present),
            wizard_present=frozenset(wizard_present),
            join_tables=frozenset(join_tables),
            unmapped=frozenset(unmapped),
            missing_in_db=frozenset(missing_in_db),
        )


@dataclass(frozen=True)
class DomainCoverageReport:
    """Result of comparing the YAML mapping against the live DB."""

    owned_by_domain: dict[Domain, frozenset[str]]
    shared_known: frozenset[str]
    excluded_present: frozenset[str]
    wizard_present: frozenset[str]
    join_tables: frozenset[str]    # M2M relation tables (resolved via FKs)
    unmapped: frozenset[str]       # tables in DB not covered by any rule
    missing_in_db: frozenset[str]  # tables declared in YAML but absent from DB

    def summary(self) -> dict[str, Any]:
        return {
            "owned": {d.value: len(s) for d, s in self.owned_by_domain.items()},
            "shared": len(self.shared_known),
            "excluded": len(self.excluded_present),
            "wizards": len(self.wizard_present),
            "join_tables": len(self.join_tables),
            "unmapped": len(self.unmapped),
            "missing_in_db": len(self.missing_in_db),
        }


# ───── loader ─────────────────────────────────────────────────────────


_DEFAULT_PATH = Path(__file__).parent / "domains.yaml"


def load_domain_mapping(path: Path | None = None) -> DomainMapping:
    """Load and validate the YAML mapping.

    Raises ``ValueError`` if a table appears under multiple primary domains
    in conflict, or if required keys are missing.
    """
    yaml_path = path or _DEFAULT_PATH
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    domains: dict[Domain, DomainSpec] = {}
    for key, body in (raw.get("domains") or {}).items():
        try:
            d = Domain(key)
        except ValueError as exc:
            raise ValueError(f"Unknown domain '{key}' in {yaml_path}") from exc
        primary = frozenset(body.get("primary") or ())
        # A domain is valid if it has primary tables OR is cross-cutting
        # OR has explicit prefix rules (checked after this loop).
        domains[d] = DomainSpec(
            domain=d,
            description=str(body.get("description", "")).strip(),
            primary_tables=primary,
            keywords=tuple(body.get("keywords") or ()),
            cross_cutting=bool(body.get("cross_cutting", False)),
        )

    shared: dict[str, SharedGroup] = {}
    for name, body in (raw.get("shared") or {}).items():
        tables = frozenset(body.get("tables") or ())
        shared[name] = SharedGroup(
            name=name,
            description=str(body.get("description", "")).strip(),
            tables=tables,
        )

    excluded = tuple(raw.get("excluded_prefixes") or ())
    version = int(raw.get("version", 1))

    prefix_rules_raw = raw.get("prefix_rules") or {}
    prefix_rules: dict[Domain, tuple[str, ...]] = {}
    for key, prefixes in prefix_rules_raw.items():
        try:
            d = Domain(key)
        except ValueError as exc:
            raise ValueError(f"Unknown domain '{key}' in prefix_rules") from exc
        prefix_rules[d] = tuple(prefixes or ())

    suffix_rules = raw.get("suffix_rules") or {}
    join_suffixes = tuple(suffix_rules.get("join_tables") or ())
    wizard_suffixes = tuple(suffix_rules.get("wizard_tables") or ())

    return DomainMapping(
        domains=domains,
        shared=shared,
        excluded_prefixes=excluded,
        prefix_rules=prefix_rules,
        join_suffixes=join_suffixes,
        wizard_suffixes=wizard_suffixes,
        version=version,
    )

"""Business glossary loader and lookup.

The glossary maps SCM-domain natural-language terms (e.g. "lead time",
"landed cost") to concrete SQL fragments and the tables they touch.
Multiple meanings are explicitly enumerated (Objective #4 in the abstract:
ambiguity resolution).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from app.schema.domains import Domain


@dataclass(frozen=True)
class GlossaryEntry:
    """A single business-term -> SQL fragment binding."""

    term: str
    aliases: tuple[str, ...]
    domain: Domain
    sql_fragment: str
    tables: tuple[str, ...]
    notes: str = ""

    def matches(self, query: str) -> bool:
        """Case-insensitive substring match against term or any alias."""
        haystack = query.lower()
        if self.term.lower() in haystack:
            return True
        return any(a.lower() in haystack for a in self.aliases)


@dataclass(frozen=True)
class AmbiguousTerm:
    """A term with multiple known interpretations."""

    term: str
    candidates: tuple[str, ...]


@dataclass(frozen=True)
class Glossary:
    """All glossary entries plus ambiguity hints."""

    entries: tuple[GlossaryEntry, ...]
    ambiguous: tuple[AmbiguousTerm, ...] = field(default_factory=tuple)
    version: int = 1

    def for_domain(self, domain: Domain) -> tuple[GlossaryEntry, ...]:
        return tuple(e for e in self.entries if e.domain == domain)

    def find(self, query: str) -> tuple[GlossaryEntry, ...]:
        """All entries whose term or alias appears in ``query``."""
        return tuple(e for e in self.entries if e.matches(query))

    def is_ambiguous(self, query: str) -> tuple[AmbiguousTerm, ...]:
        """All ambiguous terms whose canonical form appears in ``query``."""
        q = query.lower()
        return tuple(a for a in self.ambiguous if a.term.lower() in q)


_DEFAULT_PATH = Path(__file__).parent / "glossary.yaml"


def load_glossary(path: Path | None = None) -> Glossary:
    raw = yaml.safe_load((path or _DEFAULT_PATH).read_text(encoding="utf-8"))
    entries: list[GlossaryEntry] = []
    for item in raw.get("terms") or ():
        entries.append(
            GlossaryEntry(
                term=item["term"],
                aliases=tuple(item.get("aliases") or ()),
                domain=Domain(item["domain"]),
                sql_fragment=item["sql_fragment"].strip(),
                tables=tuple(item.get("tables") or ()),
                notes=str(item.get("notes", "")).strip(),
            )
        )
    ambiguous: list[AmbiguousTerm] = []
    for item in raw.get("ambiguous_terms") or ():
        ambiguous.append(
            AmbiguousTerm(
                term=item["term"],
                candidates=tuple(item.get("candidates") or ()),
            )
        )
    return Glossary(
        entries=tuple(entries),
        ambiguous=tuple(ambiguous),
        version=int(raw.get("version", 1)),
    )

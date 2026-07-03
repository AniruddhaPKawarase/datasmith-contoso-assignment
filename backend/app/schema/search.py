"""Lightweight NL-term → table/column search.

This is the *baseline* retrieval used by the Router and as a fallback for
the domain agents. Phase 4 swaps in a proper CSR-RAG hybrid (BM25 +
dense embeddings) — for now we do TF/score-weighted token overlap over:

  * table name (split on '_')
  * Odoo model name
  * Odoo description
  * column names + descriptions

This is intentionally simple, fast, and dependency-free. It runs in pure
Python over the cached metadata snapshot.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from app.schema.metadata import SchemaMetadata, Table

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenise(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


@dataclass(frozen=True)
class TableMatch:
    """A scored table match for an NL query."""

    table: str
    score: float
    matched_tokens: tuple[str, ...]
    description: str


class SchemaSearch:
    """In-memory inverted index over the schema metadata.

    Build cost is O(C + F) — one pass over tables and columns. Query cost
    is O(Q * tokens_per_doc) — typically sub-millisecond for the 5,116
    columns of the Odoo schema.
    """

    def __init__(self, metadata: SchemaMetadata) -> None:
        self._tables: dict[str, Table] = {t.name: t for t in metadata.tables}
        self._table_tokens: dict[str, Counter[str]] = {}
        # idf-ish: count of tables each token appears in
        doc_freq: Counter[str] = Counter()
        for t in metadata.tables:
            tokens = self._token_bag(t)
            self._table_tokens[t.name] = tokens
            for tok in tokens:
                doc_freq[tok] += 1
        self._doc_freq = doc_freq
        self._total_tables = max(1, len(self._tables))

    def search(
        self,
        query: str,
        *,
        top_k: int = 8,
        allowed_tables: frozenset[str] | None = None,
    ) -> list[TableMatch]:
        """Return the top-K tables matching ``query``.

        If ``allowed_tables`` is given, only those tables are scored — used
        by domain agents to restrict retrieval to their owned slice of the
        schema (CSR-RAG-style scoping).
        """
        q_tokens = _tokenise(query)
        if not q_tokens:
            return []
        scored: list[TableMatch] = []
        for tname, bag in self._table_tokens.items():
            if allowed_tables is not None and tname not in allowed_tables:
                continue
            score = 0.0
            matched: list[str] = []
            for tok in q_tokens:
                tf = bag.get(tok, 0)
                if not tf:
                    continue
                idf = max(0.0, 1.0 + (self._total_tables / (1 + self._doc_freq[tok])))
                score += float(tf) * idf
                matched.append(tok)
            if score > 0:
                t = self._tables[tname]
                scored.append(
                    TableMatch(
                        table=tname,
                        score=score,
                        matched_tokens=tuple(matched),
                        description=t.odoo_description or "",
                    )
                )
        scored.sort(key=lambda m: (-m.score, m.table))
        return scored[:top_k]

    # ── helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _token_bag(table: Table) -> Counter[str]:
        bag: Counter[str] = Counter()
        bag.update(_tokenise(table.name))
        bag.update(_tokenise(table.odoo_model))
        bag.update(_tokenise(table.odoo_description))
        for c in table.columns:
            bag.update(_tokenise(c.name))
            bag.update(_tokenise(c.description))
        return bag

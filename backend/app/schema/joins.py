"""Foreign-key graph + shortest-path discovery.

Given two tables, find the shortest sequence of FK joins to connect them.
Built once from ``SchemaMetadata`` and queried by the agents at SQL-gen time.

Algorithm: undirected BFS over the FK graph (FKs are directional in PG but
we treat them as undirected for join-path purposes — A→B joins identical
to B→A modulo the SQL ON clause).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from app.schema.metadata import SchemaMetadata


@dataclass(frozen=True)
class JoinStep:
    """One hop along a join path."""

    from_table: str
    from_column: str
    to_table: str
    to_column: str

    def to_sql_on(self) -> str:
        """Render as the SQL ON clause: ``a.col = b.col``."""
        return f"{self.from_table}.{self.from_column} = {self.to_table}.{self.to_column}"


@dataclass(frozen=True)
class JoinPath:
    """A sequence of join steps connecting two tables."""

    steps: tuple[JoinStep, ...]

    @property
    def length(self) -> int:
        return len(self.steps)

    @property
    def tables(self) -> tuple[str, ...]:
        if not self.steps:
            return ()
        out = [self.steps[0].from_table]
        for s in self.steps:
            out.append(s.to_table)
        return tuple(out)

    def to_sql_joins(self) -> str:
        """Render as a chain of ``JOIN ... ON ...`` clauses."""
        return "\n".join(
            f"JOIN {s.to_table} ON {s.to_sql_on()}" for s in self.steps
        )


class JoinGraph:
    """FK adjacency graph with shortest-path queries.

    Construction is O(F) where F is the number of FK edges.
    Path queries are O(V+E) per call — fast enough for prompt-time use on
    the full 498-table schema.
    """

    def __init__(self, metadata: SchemaMetadata) -> None:
        # adjacency[table] -> list of (neighbour_table, JoinStep going table->neighbour)
        self._adj: dict[str, list[tuple[str, JoinStep]]] = {}
        for t in metadata.tables:
            self._adj.setdefault(t.name, [])
            for fk in t.foreign_keys:
                step_fwd = JoinStep(
                    from_table=t.name,
                    from_column=fk.from_column,
                    to_table=fk.to_table,
                    to_column=fk.to_column,
                )
                step_rev = JoinStep(
                    from_table=fk.to_table,
                    from_column=fk.to_column,
                    to_table=t.name,
                    to_column=fk.from_column,
                )
                self._adj.setdefault(t.name, []).append((fk.to_table, step_fwd))
                self._adj.setdefault(fk.to_table, []).append((t.name, step_rev))

    def neighbours(self, table: str) -> list[str]:
        return [nb for nb, _ in self._adj.get(table, [])]

    def outgoing_columns(self, table: str) -> set[str]:
        """Return the set of FK source-columns leaving ``table``.

        Used by the Composer to detect a shared join key between two
        agents' table sets — e.g. both inventory.stock_move and
        finance.account_move expose ``company_id``, so the Composer can
        join their CTEs on that key.
        """
        return {step.from_column for _, step in self._adj.get(table, [])}

    def shortest_path(
        self,
        source: str,
        target: str,
        max_hops: int = 6,
    ) -> JoinPath | None:
        """BFS for the shortest join path from ``source`` to ``target``.

        Returns ``None`` if no path exists within ``max_hops``.
        """
        if source == target:
            return JoinPath(steps=())
        if source not in self._adj or target not in self._adj:
            return None
        visited: set[str] = {source}
        # queue stores (current_table, path_so_far)
        queue: deque[tuple[str, tuple[JoinStep, ...]]] = deque([(source, ())])
        while queue:
            current, path = queue.popleft()
            if len(path) >= max_hops:
                continue
            for nb, step in self._adj.get(current, []):
                if nb in visited:
                    continue
                new_path = (*path, step)
                if nb == target:
                    return JoinPath(steps=new_path)
                visited.add(nb)
                queue.append((nb, new_path))
        return None

    def all_paths(
        self,
        source: str,
        target: str,
        max_hops: int = 4,
        max_paths: int = 5,
    ) -> list[JoinPath]:
        """Enumerate up to ``max_paths`` distinct simple paths.

        Useful when the agent needs to choose between alternative joins
        (e.g. product↔partner via supplierinfo vs via sale_order).
        """
        if source == target:
            return [JoinPath(steps=())]
        if source not in self._adj or target not in self._adj:
            return []
        out: list[JoinPath] = []
        stack: list[tuple[str, tuple[JoinStep, ...], frozenset[str]]] = [
            (source, (), frozenset({source}))
        ]
        while stack and len(out) < max_paths:
            current, path, seen = stack.pop()
            if len(path) >= max_hops:
                continue
            for nb, step in self._adj.get(current, []):
                if nb in seen:
                    continue
                new_path = (*path, step)
                if nb == target:
                    out.append(JoinPath(steps=new_path))
                    if len(out) >= max_paths:
                        break
                    continue
                stack.append((nb, new_path, seen | {nb}))
        out.sort(key=lambda p: p.length)
        return out

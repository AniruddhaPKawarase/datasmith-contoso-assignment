"""Mid-sem demo — three business-grade queries against the live stack.

Three demonstrations, ~3 minutes total runtime, ~$0.04 in API spend:

  D1 — Cross-domain + temporal (the central thesis demonstration)
       "Compare total revenue this quarter with on-hand inventory
        value, by company."
       Shows: Router cross-domain split → Temporal Parser → AST Composer
              → AST-scoped Compliance → Postgres EXPLAIN OK.

  D2 — Multi-turn dialogue (the carry-over demonstration)
       T1: "Show top customers by revenue this quarter."
       T2: "Only the top 5."          (REFINEMENT, inherit domains)
       T3: "Now compare with the same period last year."  (COMPARISON)
       Shows: ReferenceDetector + ConversationMemory carry-over.

  D3 — Ambiguity (the calibrated-honesty demonstration)
       "What is the lead time for our Asian suppliers?"
       Shows: Glossary ambiguity detection → structured clarification
              question → no SQL generated (no tokens burnt).

The script writes a full transcript to docs/viva/MIDSEM_DEMO_LOG_<ts>.txt
for evidence post-viva. EXPLAIN is run against the live Postgres for
every SQL produced — if it fails, the failure is logged but the demo
continues.

Run from project root:
    python scripts/midsem_demo.py
"""
from __future__ import annotations

import asyncio
import datetime as dt
import os
import sys
import textwrap
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

env_path = ROOT / ".env"
if env_path.exists():
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())
os.environ["POSTGRES_HOST"] = "localhost"
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from app.agents import (  # noqa: E402
    BaseAgent,
    ComplianceProcessor,
    ConversationMemory,
    MessageLog,
    Orchestrator,
    OrchestratorLimits,
    RouterAgent,
    build_specialists,
    fresh_state,
)
from app.ambiguity import AmbiguityResolver  # noqa: E402
from app.composer import Composer  # noqa: E402
from app.conversation import ConversationContextBuilder, ReferenceDetector  # noqa: E402
from app.db.postgres import PostgresAdapter, PostgresConfig  # noqa: E402
from app.llm import LLMConfig, LLMProvider  # noqa: E402
from app.llm.token_tracker import TokenTracker  # noqa: E402
from app.schema.domains import Domain, load_domain_mapping  # noqa: E402
from app.schema.glossary import load_glossary  # noqa: E402
from app.schema.joins import JoinGraph  # noqa: E402
from app.schema.metadata import SchemaMetadata  # noqa: E402
from app.schema.search import SchemaSearch  # noqa: E402
from app.temporal import TemporalParser  # noqa: E402

SCHEMA = ROOT / "backend" / "data" / "odoo_schema.json"
LOG_DIR = ROOT / "docs" / "viva"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"MIDSEM_DEMO_LOG_{dt.datetime.now():%Y%m%d_%H%M%S}.txt"


# ── helpers ──────────────────────────────────────────────────────────


class _Tee:
    """Write to console AND log file at the same time."""

    def __init__(self, path: Path) -> None:
        self._fh = open(path, "w", encoding="utf-8")

    def write(self, *parts: object) -> None:
        line = " ".join(str(p) for p in parts)
        # Console may be cp1252 (Windows default); strip Unicode that the
        # codec cannot encode rather than crash the whole demo.
        try:
            print(line, flush=True)
        except UnicodeEncodeError:
            enc = sys.stdout.encoding or "ascii"
            print(line.encode(enc, errors="replace").decode(enc), flush=True)
        self._fh.write(line + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()


def section_header(tee: _Tee, title: str) -> None:
    tee.write("")
    tee.write("=" * 72)
    tee.write(title)
    tee.write("=" * 72)


def step(tee: _Tee, label: str, body: str = "") -> None:
    tee.write(f"  [{label}]  {body}".rstrip())


def wrap_sql(sql: str, width: int = 78) -> str:
    return textwrap.fill(" ".join(sql.split()), width=width,
                         subsequent_indent="      ")


# ── stack assembly ───────────────────────────────────────────────────


async def build_orchestrator():
    metadata = SchemaMetadata.from_json(SCHEMA)
    mapping = load_domain_mapping()
    glossary = load_glossary()
    search = SchemaSearch(metadata)
    join_graph = JoinGraph(metadata)

    cfg = LLMConfig.from_env()
    llm = LLMProvider(cfg)
    tracker = TokenTracker()

    router = RouterAgent(llm=llm, mapping=mapping, glossary=glossary,
                         tracker=tracker)
    specialists = build_specialists(
        llm=llm, metadata=metadata, mapping=mapping,
        glossary=glossary, search=search, tracker=tracker,
    )
    agents: dict[Domain, BaseAgent] = dict(specialists)
    compliance = ComplianceProcessor(metadata)
    composer = Composer(join_graph=join_graph)
    temporal_parser = TemporalParser()
    ambiguity_resolver = AmbiguityResolver(glossary, mapping=mapping)
    memory = ConversationMemory()
    log = MessageLog()

    orch = Orchestrator(
        router=router,
        agents=agents,
        memory=memory,
        composer=composer,
        validator=None,                       # demo uses its own EXPLAIN
        compliance=compliance,
        temporal_parser=temporal_parser,
        ambiguity_resolver=ambiguity_resolver,
        reference_detector=ReferenceDetector(),
        conversation_builder=ConversationContextBuilder(),
        message_log=log,
        limits=OrchestratorLimits(max_correction_attempts=2),
    )
    pg = PostgresAdapter(PostgresConfig.from_env())
    return orch, llm, tracker, pg


# ── individual demo cases ────────────────────────────────────────────


async def run_query(*, orch, tee: _Tee, pg, query: str, label: str,
                    session_id: str,
                    user_company_ids: tuple[int, ...] = (1,)) -> dict[str, object]:
    step(tee, label, query)
    t0 = time.time()
    state = fresh_state(
        query=query, session_id=session_id,
        user_company_ids=user_company_ids,
    )
    result = await orch.run(state)
    elapsed_ms = int((time.time() - t0) * 1000)

    intent = result.get("intent", "")
    domains = [d.value for d in result.get("domains", ())]
    sql = result.get("composed_sql", "") or ""

    step(tee, "intent  ", intent)
    step(tee, "domains ", ", ".join(domains) if domains else "(none)")
    step(tee, "latency ", f"{elapsed_ms} ms")

    final_error = result.get("final_error", "")
    if final_error:
        step(tee, "panel   ", final_error)

    if sql.strip():
        tee.write("")
        tee.write("  Composed SQL:")
        for line in wrap_sql(sql).splitlines():
            tee.write(f"    {line}")
        tee.write("")
        explain_ok, explain_msg = check_explain(pg, sql)
        step(tee, "EXPLAIN ", "OK" if explain_ok else f"FAIL — {explain_msg}")
    else:
        tee.write("  No SQL produced — by design (see panel field above).")

    return {
        "intent": intent, "domains": domains, "sql": sql,
        "latency_ms": elapsed_ms,
        "final_error": final_error,
    }


def check_explain(pg: PostgresAdapter, sql: str) -> tuple[bool, str]:
    if not pg.ping():
        return False, "Postgres unreachable"
    clean = sql.rstrip().rstrip(";")
    try:
        with pg.connection() as conn, conn.cursor() as cur:
            cur.execute(f"EXPLAIN {clean}")
            cur.fetchall()
        return True, ""
    except Exception as exc:
        return False, str(exc).splitlines()[0][:180]


async def demo_1_cross_domain(orch, tee, pg) -> None:
    section_header(
        tee, "D1.  Cross-domain  +  Temporal  +  AST Compliance")
    tee.write(
        "  Demonstrates the dissertation's central thesis:"
        " domain-axis decomposition with deterministic temporal "
        "reasoning and per-CTE-scoped RBAC.")
    tee.write("")
    await run_query(
        orch=orch, tee=tee, pg=pg,
        query=("Compare total revenue this quarter with on-hand inventory "
               "value, by company."),
        label="Q1.1 ",
        session_id="midsem-d1",
        user_company_ids=(1,),
    )


async def demo_2_multi_turn(orch, tee, pg) -> None:
    section_header(
        tee, "D2.  Multi-turn dialogue — refinement and comparison")
    tee.write(
        "  Demonstrates the ReferenceDetector inheriting domains "
        "across turns. The Router sees the first query; turns 2 and 3 "
        "carry the prior domains and temporal context.")
    tee.write("")
    await run_query(
        orch=orch, tee=tee, pg=pg,
        query="Show top customers by revenue this quarter.",
        label="T1   ",
        session_id="midsem-d2",
    )
    await run_query(
        orch=orch, tee=tee, pg=pg,
        query="Only the top 5.",
        label="T2   ",
        session_id="midsem-d2",
    )
    await run_query(
        orch=orch, tee=tee, pg=pg,
        query="Now compare with the same period last year.",
        label="T3   ",
        session_id="midsem-d2",
    )


async def demo_3_ambiguity(orch, tee, pg) -> None:
    section_header(
        tee, "D3.  Ambiguity — calibrated refusal")
    tee.write(
        "  Demonstrates the AmbiguityResolver. The system recognises "
        "'lead time' has three glossary senses, refuses to guess, "
        "and asks a structured clarification question.")
    tee.write("")
    await run_query(
        orch=orch, tee=tee, pg=pg,
        query="What is the lead time for our Asian suppliers?",
        label="Q3.1 ",
        session_id="midsem-d3",
    )


# ── main ─────────────────────────────────────────────────────────────


async def main() -> int:
    tee = _Tee(LOG_FILE)
    section_header(tee, "MID-SEM DEMO  —  Domain-Aware Multi-Agent NL-to-SQL")
    tee.write(f"  Run timestamp:   {dt.datetime.now():%Y-%m-%d %H:%M:%S}")
    tee.write(f"  Log file:        {LOG_FILE.relative_to(ROOT)}")
    tee.write(f"  Schema cache:    backend/data/odoo_schema.json")
    tee.write(f"  Postgres:        localhost:5432/odoo  (Odoo 17, 498 tables)")

    if not SCHEMA.exists():
        tee.write("ERROR: missing schema cache. Run scripts/introspect_odoo.py first.")
        tee.close()
        return 1

    orch, llm, tracker, pg = await build_orchestrator()
    try:
        await demo_1_cross_domain(orch, tee, pg)
        await demo_2_multi_turn(orch, tee, pg)
        await demo_3_ambiguity(orch, tee, pg)
    finally:
        await llm.aclose()

    section_header(tee, "TOKEN USAGE  &  ESTIMATED COST")
    grand_in = 0
    grand_out = 0
    for snap in tracker.snapshot():
        tee.write(
            f"  {snap.task.value:12s}  {snap.model:32s}  "
            f"{snap.call_count} call(s)  "
            f"in={snap.prompt_tokens}  out={snap.completion_tokens}"
        )
        grand_in += snap.prompt_tokens
        grand_out += snap.completion_tokens
    tee.write("")
    # rough mid-2026 pricing for the two configured models
    cost = (grand_in * 1e-6 * 0.20) + (grand_out * 1e-6 * 1.00)
    tee.write(f"  TOTAL    in={grand_in}  out={grand_out}  ≈ ${cost:.4f}")

    section_header(tee, "DEMO COMPLETE")
    tee.write(f"  Transcript saved to {LOG_FILE.relative_to(ROOT)}")
    tee.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

"""Phase 4 live smoke test — real domain specialists generating real SQL.

Differs from smoke_orchestrator.py (Phase 3) in that the agents are NOW
LLM-driven (Anthropic Haiku 4.5) and produce real PostgreSQL targeting
the actual Odoo schema. Compliance injects RBAC predicates post-compose.

Run from project root:
    python scripts/smoke_phase4.py
"""
from __future__ import annotations

import asyncio
import os
import sys
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
from app.db.postgres import PostgresAdapter, PostgresConfig  # noqa: E402
from app.llm import LLMConfig, LLMProvider  # noqa: E402
from app.llm.token_tracker import TokenTracker  # noqa: E402
from app.schema.domains import Domain, load_domain_mapping  # noqa: E402
from app.schema.glossary import load_glossary  # noqa: E402
from app.schema.metadata import SchemaMetadata  # noqa: E402
from app.schema.search import SchemaSearch  # noqa: E402

SCHEMA = ROOT / "backend" / "data" / "odoo_schema.json"


QUERIES = [
    ("How many products do we have in stock right now?", "inventory", ()),
    ("List the top 5 customers by total invoiced value.", "finance", ()),
    ("Show recent sale orders confirmed this month.", "demand", ()),
    ("Total revenue vs total on-hand inventory value.", "cross", (1,)),  # company_id filter
]


async def main() -> int:
    if not SCHEMA.exists():
        print(f"Missing {SCHEMA}; run scripts/introspect_odoo.py first.")
        return 1
    metadata = SchemaMetadata.from_json(SCHEMA)
    mapping = load_domain_mapping()
    glossary = load_glossary()
    search = SchemaSearch(metadata)

    cfg = LLMConfig.from_env()
    llm = LLMProvider(cfg)
    tracker = TokenTracker()

    router = RouterAgent(llm=llm, mapping=mapping, glossary=glossary, tracker=tracker)
    specialists = build_specialists(
        llm=llm, metadata=metadata, mapping=mapping,
        glossary=glossary, search=search, tracker=tracker,
    )
    agents: dict[Domain, BaseAgent] = dict(specialists)
    compliance = ComplianceProcessor(metadata)
    orch = Orchestrator(
        router=router, agents=agents, memory=ConversationMemory(),
        compliance=compliance, message_log=MessageLog(),
        limits=OrchestratorLimits(max_correction_attempts=2),
    )

    # Run each query and (optionally) attempt actual execution to prove the
    # SQL is valid Postgres. We don't fail the smoke on execution errors —
    # Phase 5 will own SQL validation.
    pg_cfg = PostgresConfig.from_env()
    pg = PostgresAdapter(pg_cfg) if pg_cfg else None

    for i, (q, label, company_ids) in enumerate(QUERIES, start=1):
        print()
        print(f"----- {i}. [{label}] {q}")
        state = fresh_state(
            query=q, session_id=f"smoke4-{i}",
            user_company_ids=company_ids,
        )
        try:
            result = await orch.run(state)
        except Exception as exc:
            print(f"  orchestrator raised: {exc}")
            continue
        sql = result.get("composed_sql", "")
        print(f"  intent:        {result.get('intent')}")
        print(f"  domains:       {[d.value for d in result.get('domains', ())]}")
        print(f"  attempts:      {result.get('attempt')}")
        print(f"  confidence:    {result.get('confidence')}")
        outs = result.get("agent_outputs", ())
        for o in outs:
            print(f"  ag[{o.domain.value:<9}]  tables={list(o.used_tables)}  conf={o.confidence}")
        print(f"  SQL  ({len(sql)} chars):")
        for line in sql.splitlines()[:14]:
            print(f"    {line}")
        if len(sql.splitlines()) > 14:
            print(f"    ... +{len(sql.splitlines()) - 14} more lines")
        # Try a real execution to prove the SQL works.
        if sql and pg and pg.ping():
            try:
                with pg.connection() as conn, conn.cursor() as cur:
                    cur.execute(f"EXPLAIN {sql.rstrip(';')}")
                    print(f"  EXPLAIN: OK")
            except Exception as exc:
                msg = str(exc).splitlines()[0][:200]
                print(f"  EXPLAIN: FAIL — {msg}")
        if result.get("final_error"):
            print(f"  error:         {result['final_error']}")

    await llm.aclose()
    print()
    print("Token usage:")
    for snap in tracker.snapshot():
        print(
            f"  {snap.task.value:10s}  {snap.model:35s}  "
            f"{snap.call_count} calls  "
            f"{snap.prompt_tokens} in / {snap.completion_tokens} out"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

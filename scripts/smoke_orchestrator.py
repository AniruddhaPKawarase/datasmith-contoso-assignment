"""End-to-end smoke test of the Phase 3 orchestrator against the live stack.

Reads .env, instantiates the orchestrator the same way main.py does, and
runs three queries:

  1. A clear single-domain inventory question
  2. A cross-domain (inventory + finance) question
  3. An out-of-scope question

For each it prints the Router decision, generated SQL, confidence, and any
error. Total token cost ~$0.001.

Run from project root:
    python scripts/smoke_orchestrator.py
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
os.environ["POSTGRES_HOST"] = "localhost"  # host-side dev override

from app.agents import (  # noqa: E402
    ConversationMemory,
    MessageLog,
    Orchestrator,
    OrchestratorLimits,
    RouterAgent,
    StubDomainAgent,
    fresh_state,
)
from app.llm import LLMConfig, LLMProvider  # noqa: E402
from app.llm.token_tracker import TokenTracker  # noqa: E402
from app.schema.domains import Domain, load_domain_mapping  # noqa: E402
from app.schema.glossary import load_glossary  # noqa: E402
from app.schema.metadata import SchemaMetadata  # noqa: E402
from app.schema.search import SchemaSearch  # noqa: E402

SCHEMA = ROOT / "backend" / "data" / "odoo_schema.json"


QUERIES = [
    ("How much stock do we have for each warehouse?",            "inventory"),
    ("Compare total revenue with on-hand inventory value this quarter.", "cross"),
    ("What's the weather like today?",                           "scope"),
]


async def main() -> int:
    if not SCHEMA.exists():
        print(f"Missing schema cache at {SCHEMA}. Run scripts/introspect_odoo.py first.")
        return 1
    print(f"Loading schema cache: {SCHEMA.relative_to(ROOT)}")
    metadata = SchemaMetadata.from_json(SCHEMA)
    mapping = load_domain_mapping()
    glossary = load_glossary()
    search = SchemaSearch(metadata)

    cfg = LLMConfig.from_env()
    llm = LLMProvider(cfg)
    tracker = TokenTracker()

    router = RouterAgent(llm=llm, mapping=mapping, glossary=glossary, tracker=tracker)
    agents = {
        d: StubDomainAgent(
            domain=d,
            llm=llm, metadata=metadata, mapping=mapping,
            glossary=glossary, search=search, tracker=tracker,
        )
        for d in (Domain.INVENTORY, Domain.LOGISTICS, Domain.FINANCE,
                  Domain.DEMAND, Domain.COMPLIANCE)
    }
    log = MessageLog()
    memory = ConversationMemory()
    orch = Orchestrator(
        router=router, agents=agents, memory=memory,
        message_log=log, limits=OrchestratorLimits(max_correction_attempts=3),
    )

    try:
        for i, (q, label) in enumerate(QUERIES, start=1):
            print()
            print(f"----- {i}. [{label}] {q}")
            state = fresh_state(query=q, session_id=f"smoke-{i}")
            result = await orch.run(state)
            print(f"  intent:        {result.get('intent')}")
            print(f"  domains:       {[d.value for d in result.get('domains', ())]}")
            print(f"  attempts:      {result.get('attempt')}")
            print(f"  confidence:    {result.get('confidence')}")
            sql = result.get("composed_sql", "")
            print(f"  composed SQL:  {sql[:200] + ('...' if len(sql) > 200 else '')}")
            if result.get("final_error"):
                print(f"  error:         {result['final_error']}")
    finally:
        await llm.aclose()

    print()
    print("Token usage:")
    for snap in tracker.snapshot():
        print(
            f"  {snap.task.value:10s}  {snap.model:35s}  "
            f"{snap.call_count} calls  "
            f"{snap.prompt_tokens} in / {snap.completion_tokens} out  "
            f"avg {snap.latency_ms // max(snap.call_count, 1)} ms"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

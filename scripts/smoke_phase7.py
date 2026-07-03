"""Phase 7 live smoke — a 3-turn conversation against the running stack.

Turn 1: "show me total revenue by customer this quarter"        [NEW_TOPIC]
Turn 2: "only the top 5"                                         [REFINEMENT]
Turn 3: "compare with same period last year"                     [COMPARISON]

For each turn we print the classified reference kind, the SQL, and an
EXPLAIN check.
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
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())
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
from app.validator import (  # noqa: E402
    BusinessRuleValidator,
    ExecutionValidator,
    SyntaxValidator,
    ValidationPipeline,
)

SCHEMA = ROOT / "backend" / "data" / "odoo_schema.json"

CONVERSATION = [
    "Show me total revenue by customer this quarter.",
    "Only the top 5.",
    "Now compare with the same period last year.",
]


async def main() -> int:
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
    join_graph = JoinGraph(metadata)
    composer = Composer(join_graph=join_graph)
    all_visible: set[str] = set()
    for a in specialists.values():
        all_visible.update(a.visible_tables)
    pg = PostgresAdapter(PostgresConfig.from_env())
    validator = ValidationPipeline(
        syntax=SyntaxValidator(allowed_tables=frozenset(all_visible)),
        execution=ExecutionValidator(pg, timeout_s=30),
        business=BusinessRuleValidator(),
    )
    memory = ConversationMemory()
    orch = Orchestrator(
        router=router, agents=agents, memory=memory,
        composer=composer, validator=validator, compliance=compliance,
        temporal_parser=TemporalParser(),
        ambiguity_resolver=AmbiguityResolver(glossary, mapping=mapping),
        reference_detector=ReferenceDetector(),
        conversation_builder=ConversationContextBuilder(),
        message_log=MessageLog(),
        limits=OrchestratorLimits(max_correction_attempts=2),
    )
    detector = ReferenceDetector()
    session_id = "phase7-demo"

    for i, q in enumerate(CONVERSATION, start=1):
        print()
        print(f"===== Turn {i}: {q}")
        # Show how the detector would classify (the orchestrator does this internally too).
        _, recent = memory.active_window(session_id)
        ref = detector.classify(q, has_prior_turn=bool(recent))
        print(f"  reference kind: {ref.kind.value}  (triggers: {list(ref.triggers)})")

        state = fresh_state(query=q, session_id=session_id,
                              user_company_ids=(1,))
        result = await orch.run(state)
        print(f"  intent:        {result.get('intent')}")
        print(f"  domains:       {[d.value for d in result.get('domains', ())]}")
        sql = result.get("composed_sql", "")
        print(f"  SQL ({len(sql)} chars):")
        for line in sql.splitlines()[:14]:
            print(f"    {line}")
        if len(sql.splitlines()) > 14:
            print(f"    ... +{len(sql.splitlines()) - 14} more")
        if sql and pg.ping():
            try:
                with pg.connection() as conn, conn.cursor() as cur:
                    cur.execute(f"EXPLAIN {sql.rstrip(';')}")
                    print("  EXPLAIN: OK")
            except Exception as exc:
                msg = str(exc).splitlines()[0][:200]
                print(f"  EXPLAIN: FAIL — {msg}")
        if result.get("final_error"):
            print(f"  final_error:   {result['final_error'][:200]}")

    await llm.aclose()
    print()
    print("Token usage:")
    for snap in tracker.snapshot():
        print(f"  {snap.task.value:10s}  {snap.model:35s}  {snap.call_count} calls  "
                f"{snap.prompt_tokens} in / {snap.completion_tokens} out")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

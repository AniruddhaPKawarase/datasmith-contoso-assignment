"""FastAPI gateway — wraps the existing Orchestrator behind HTTP.

The gateway holds one set of system singletons (LLM provider, schema
metadata, mapping, glossary, search, join graph) and one `Orchestrator`
instance per session_id so that the ReferenceDetector + ConversationMemory
correctly inherit across multi-turn conversations within a session.

Endpoints:
    GET /healthz        → 200 if DB reachable, 503 otherwise
    POST /ask           → run one query through the orchestrator
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from time import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents import (
    BaseAgent,
    ConversationMemory,
    MessageLog,
    Orchestrator,
    OrchestratorLimits,
    RouterAgent,
    build_specialists,
    fresh_state,
)
from app.agents.insight_detector import detect_decline_insight
from app.agents.planner_chain import maybe_multi_step
from app.agents.viz_selector import VizSelector
from app.ambiguity import AmbiguityResolver
from app.api.models import (
    AskRequest,
    AskResponse,
    Panel,
    PlanStep,
    TokenUsage,
    Trace,
    Visualization,
)
from app.composer import Composer
from app.conversation import ConversationContextBuilder, ReferenceDetector
from app.llm import LLMConfig, LLMProvider
from app.llm.token_tracker import TokenTracker
from app.schema.domains import Domain, load_domain_mapping
from app.schema.glossary import load_glossary
from app.schema.joins import JoinGraph
from app.schema.metadata import SchemaMetadata
from app.schema.search import SchemaSearch
from app.temporal import TemporalParser

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / (os.getenv("CONTOSO_SCHEMA_PATH") or "backend/data/contoso_schema.json")

_sessions: dict[str, tuple[Orchestrator, TokenTracker]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Eagerly load all shared singletons.
    os.environ.setdefault("POSTGRES_HOST", "localhost")
    cfg = LLMConfig.from_env()
    app.state.llm = LLMProvider(cfg)
    app.state.metadata = SchemaMetadata.from_json(SCHEMA)
    app.state.mapping = load_domain_mapping()
    app.state.glossary = load_glossary()
    app.state.search = SchemaSearch(app.state.metadata)
    app.state.join_graph = JoinGraph(app.state.metadata)
    logger.info("gateway ready — schema=%d tables", len(app.state.metadata.tables))
    yield
    await app.state.llm.aclose()


app = FastAPI(title="SCM NL-to-SQL Gateway", lifespan=lifespan)

# CORS: local dev on :3000/:3001 always; production origin from $ALLOWED_ORIGIN
# (comma-separated for multiple — e.g. staging + prod Vercel URLs).
_allowed_origins = [
    "http://localhost:3000", "http://127.0.0.1:3000",
    "http://localhost:3001", "http://127.0.0.1:3001",
]
_prod_origin = os.getenv("ALLOWED_ORIGIN", "").strip()
if _prod_origin:
    _allowed_origins.extend([o.strip() for o in _prod_origin.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _session(session_id: str) -> tuple[Orchestrator, TokenTracker]:
    if session_id in _sessions:
        return _sessions[session_id]
    tracker = TokenTracker()
    router = RouterAgent(
        llm=app.state.llm,
        mapping=app.state.mapping,
        glossary=app.state.glossary,
        tracker=tracker,
    )
    specialists = build_specialists(
        llm=app.state.llm,
        metadata=app.state.metadata,
        mapping=app.state.mapping,
        glossary=app.state.glossary,
        search=app.state.search,
        tracker=tracker,
    )
    agents: dict[Domain, BaseAgent] = dict(specialists)
    orch = Orchestrator(
        router=router,
        agents=agents,
        memory=ConversationMemory(),
        composer=Composer(join_graph=app.state.join_graph),
        validator=None,
        compliance=None,  # disabled for demo; same contract as eval
        temporal_parser=TemporalParser(),
        ambiguity_resolver=AmbiguityResolver(app.state.glossary, mapping=app.state.mapping),
        reference_detector=ReferenceDetector(),
        conversation_builder=ConversationContextBuilder(),
        message_log=MessageLog(),
        limits=OrchestratorLimits(max_correction_attempts=2),
    )
    _sessions[session_id] = (orch, tracker)
    return orch, tracker


@app.get("/healthz")
async def healthz():
    """Trivial health probe — confirms the gateway is up and schema loaded."""
    meta = getattr(app.state, "metadata", None)
    n_tables = len(meta.tables) if meta is not None else 0
    return {"ok": True, "tables": n_tables, "sessions": len(_sessions)}


async def _run_one(
    query: str,
    session_id: str,
    orch,
    tracker: TokenTracker,
    llm,
) -> dict:
    """Run one NL query through orchestrator → SQL → execute → VizSelector.

    Returns a dict with all the pieces the caller needs to assemble either
    the top-level AskResponse (single-shot) or one Panel entry (multi-step).
    """
    state = fresh_state(query=query, session_id=session_id, user_company_ids=())
    try:
        result = await orch.run(state)
    except Exception as exc:
        return {"intent": "error", "sql": None, "rows": None, "err": str(exc)}

    intent = str(result.get("intent", "unknown"))
    domains_raw = result.get("domains", [])
    domains = [d.value if hasattr(d, "value") else str(d) for d in domains_raw]
    sql = str(result.get("composed_sql", "") or "") or None
    clarification = str(result.get("clarification_question", "") or "") or None
    err = str(result.get("final_error", "") or "") or None

    rows: list[dict] | None = None
    row_count = 0
    exec_err: str | None = None
    if sql and intent == "supply_chain_question":
        try:
            import psycopg
            pg_cfg = {
                "host": os.getenv("POSTGRES_HOST", "localhost"),
                "port": int(os.getenv("POSTGRES_PORT", "5432")),
                "dbname": os.getenv("POSTGRES_DB", "contoso"),
                "user": os.getenv("POSTGRES_USER", "contoso_reader"),
                "password": os.getenv("POSTGRES_PASSWORD", "contoso_read_only"),
                # sslmode: CockroachDB requires TLS; local Postgres accepts
                # 'prefer' and falls back to plain. `verify-full` needs a
                # CA bundle so we default to `require` (encrypted but no
                # cert verification) — good enough for a demo.
                "sslmode": os.getenv("POSTGRES_SSLMODE", "prefer"),
            }
            with (
                psycopg.connect(**pg_cfg, connect_timeout=10) as conn,
                conn.cursor() as cur,
            ):
                cur.execute("SET LOCAL statement_timeout = 30000")
                cur.execute(sql.rstrip().rstrip(";"))
                col_names = [d[0] for d in cur.description] if cur.description else []
                raw_rows = cur.fetchmany(100)
                rows = [{col_names[i]: _jsonify(v) for i, v in enumerate(r)}
                        for r in raw_rows]
                row_count = len(rows)
        except Exception as exc:
            exec_err = str(exc).splitlines()[0][:300]

    viz: Visualization | None = None
    if rows and intent == "supply_chain_question":
        try:
            selector = VizSelector(llm=llm, tracker=tracker)
            decision = await selector.select(query=query, sql=sql or "", rows=rows)
            insight = detect_decline_insight(rows)
            reasoning = (
                f"{decision.reasoning} · {insight}" if insight else decision.reasoning
            )
            viz = Visualization(**decision.to_dict() | {"reasoning": reasoning})
        except Exception as exc:
            logger.warning("VizSelector failed: %s", exc)
            viz = Visualization(format="table", reasoning=f"selector error: {exc}")
    elif intent == "clarification_needed":
        viz = Visualization(format="prose", reasoning="clarification needed")

    return {
        "intent": intent, "domains": domains, "sql": sql, "rows": rows,
        "row_count": row_count, "err": exec_err or err,
        "clarification": clarification, "viz": viz,
    }


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    orch, tracker = _session(req.session_id)
    t0 = time()

    # ── multi-step planner path (TC06 funnel, TC08 multi-panel) ───────
    plan = maybe_multi_step(req.query)
    panels: list[Panel] | None = None
    plan_steps_view: list[PlanStep] = []

    if plan:
        panels = []
        for step in plan:
            step_res = await _run_one(
                step.natural_language,
                f"{req.session_id}-step{step.step}",
                orch, tracker, app.state.llm,
            )
            panels.append(Panel(
                step=step.step, name=step.name,
                sql=step_res.get("sql"),
                rows=step_res.get("rows"),
                row_count=step_res.get("row_count", 0),
                visualization=step_res.get("viz"),
                error=step_res.get("err"),
            ))
            plan_steps_view.append(PlanStep(
                step=step.step, name=step.name,
                natural_language=step.natural_language,
                rationale=step.rationale,
            ))
        # For multi-step, top-level intent/domains reflect the plan itself
        top_intent = "multi_step_question"
        top_domains = ["demand"]
        top_sql = None
        top_rows = None
        top_row_count = sum(p.row_count for p in panels)
        top_err = None
        top_viz = None
        top_clarif = None
    else:
        # Single-shot path
        single = await _run_one(req.query, req.session_id, orch, tracker, app.state.llm)
        top_intent = single["intent"]
        top_domains = single.get("domains", [])
        top_sql = single.get("sql")
        top_rows = single.get("rows")
        top_row_count = single.get("row_count", 0)
        top_err = single.get("err")
        top_viz = single.get("viz")
        top_clarif = single.get("clarification")

    # Token usage + cost rollup (Planner + all Executor + VizSelector calls)
    snapshot = tracker.snapshot()
    usage = TokenUsage()
    cost = 0.0
    for s in snapshot:
        task = s.task.value
        total = s.prompt_tokens + s.completion_tokens
        if task == "router":
            usage.router += total
        elif task == "sql_gen":
            usage.sql_gen += total
        elif task == "validator":
            usage.validator += total
        # Use Haiku pricing as default — actual model may be gpt-4o-mini
        # (cheaper), so this is a conservative upper bound.
        cost += s.prompt_tokens / 1_000_000 * 1.0 + s.completion_tokens / 1_000_000 * 5.0

    trace = Trace(
        planner_intent=top_intent,
        planner_domains=list(top_domains),
        plan_steps=plan_steps_view,
        executor_notes=(
            f"Multi-step plan: {len(panels)} panel(s) executed."
            if panels else "Single-shot: one specialist, one SQL execution."
        ),
    )

    return AskResponse(
        intent=top_intent,
        domains=list(top_domains),
        sql=top_sql,
        rows=top_rows,
        row_count=top_row_count,
        latency_ms=int((time() - t0) * 1000),
        token_usage=usage,
        estimated_cost_usd=round(cost, 4),
        explain_ok=(top_err is None and (top_sql is not None or panels is not None)),
        error=top_err,
        clarification_question=top_clarif,
        visualization=top_viz,
        panels=panels,
        trace=trace,
    )


def _jsonify(v):
    """Coerce DB cell values to JSON-serialisable Python types."""
    if v is None:
        return None
    import datetime as _dt
    from decimal import Decimal
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (_dt.datetime, _dt.date, _dt.time)):
        return v.isoformat()
    if isinstance(v, (bytes, bytearray)):
        return v.hex()
    if isinstance(v, (list, tuple, set)):
        return [_jsonify(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _jsonify(val) for k, val in v.items()}
    return v

"""FastAPI entrypoint."""
from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agents import (
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
from app.ambiguity import AmbiguityResolver
from app.composer import Composer
from app.conversation import ConversationContextBuilder, ReferenceDetector
from app.db.postgres import PostgresAdapter, PostgresConfig
from app.llm import LLMConfig, LLMProvider
from app.llm.token_tracker import TokenTracker
from app.schema.domains import Domain, load_domain_mapping
from app.schema.glossary import load_glossary
from app.schema.joins import JoinGraph
from app.schema.metadata import SchemaMetadata
from app.schema.search import SchemaSearch
from app.temporal import TemporalParser
from app.validator import (
    BusinessRuleValidator,
    ExecutionValidator,
    SyntaxValidator,
    ValidationPipeline,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=os.getenv("API_LOG_LEVEL", "INFO").upper())

_HERE = Path(__file__).resolve().parent
_SCHEMA_CACHE = _HERE.parent / "data" / "odoo_schema.json"


class AppState:
    llm: LLMProvider | None = None
    tracker: TokenTracker | None = None
    orchestrator: Orchestrator | None = None
    memory: ConversationMemory | None = None
    message_log: MessageLog | None = None


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    cfg = LLMConfig.from_env()
    state.llm = LLMProvider(cfg)
    state.tracker = TokenTracker()
    state.memory = ConversationMemory()
    state.message_log = MessageLog()

    if not _SCHEMA_CACHE.exists():
        logger.warning(
            "Schema cache not found at %s — /query will return 503 until "
            "`python scripts/introspect_odoo.py` is run.",
            _SCHEMA_CACHE,
        )
    else:
        metadata = SchemaMetadata.from_json(_SCHEMA_CACHE)
        mapping = load_domain_mapping()
        glossary = load_glossary()
        search = SchemaSearch(metadata)
        router = RouterAgent(
            llm=state.llm,
            mapping=mapping,
            glossary=glossary,
            tracker=state.tracker,
        )
        specialists = build_specialists(
            llm=state.llm,
            metadata=metadata,
            mapping=mapping,
            glossary=glossary,
            search=search,
            tracker=state.tracker,
        )
        agents: dict[Domain, BaseAgent] = dict(specialists)
        compliance = ComplianceProcessor(metadata)
        join_graph = JoinGraph(metadata)
        composer = Composer(join_graph=join_graph)

        # Build the validator pipeline. The allow-list is the union of all
        # five specialists' visible-tables sets — any table referenced in
        # the composed SQL must live in at least one agent's slice.
        all_visible: set[str] = set()
        for agent in specialists.values():
            all_visible.update(agent.visible_tables)
        pg_cfg = PostgresConfig.from_env()
        pg_adapter = PostgresAdapter(pg_cfg)
        validator = ValidationPipeline(
            syntax=SyntaxValidator(allowed_tables=frozenset(all_visible)),
            execution=ExecutionValidator(
                pg_adapter,
                timeout_s=int(os.getenv("MAX_SQL_TIMEOUT_SECONDS", "30")),
            ),
            business=BusinessRuleValidator(),
        )

        temporal_parser = TemporalParser()
        ambiguity_resolver = AmbiguityResolver(glossary, mapping=mapping)

        state.orchestrator = Orchestrator(
            router=router,
            agents=agents,
            memory=state.memory,
            composer=composer,
            validator=validator,
            compliance=compliance,
            temporal_parser=temporal_parser,
            ambiguity_resolver=ambiguity_resolver,
            reference_detector=ReferenceDetector(),
            conversation_builder=ConversationContextBuilder(),
            message_log=state.message_log,
            limits=OrchestratorLimits(
                max_correction_attempts=int(os.getenv("MAX_CORRECTION_ATTEMPTS", "3")),
                sql_timeout_s=int(os.getenv("MAX_SQL_TIMEOUT_SECONDS", "30")),
            ),
            execute_on_validate=os.getenv("EXECUTE_ON_VALIDATE", "0") == "1",
        )
        logger.info(
            "Orchestrator ready (%d tables, %d specialists, validator=on)",
            metadata.table_count,
            len(specialists),
        )

    try:
        yield
    finally:
        if state.llm is not None:
            await state.llm.aclose()
        logger.info("LLM provider closed")


app = FastAPI(
    title="SCM NL-to-SQL API",
    description="Domain-Aware Multi-Agent NL-to-SQL for Enterprise Supply Chain Intelligence",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    version: str
    orchestrator_ready: bool


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="0.2.0",
        orchestrator_ready=state.orchestrator is not None,
    )


class QueryRequest(BaseModel):
    query: str
    session_id: str | None = None
    user_role: str = "analyst"


class QueryResponse(BaseModel):
    intent: str
    sql: str
    domains_used: list[str]
    confidence: float
    attempts: int
    explanation: str
    error: str | None


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest) -> QueryResponse:
    """Submit a natural-language query."""
    if state.orchestrator is None:
        return QueryResponse(
            intent="error",
            sql="",
            domains_used=[],
            confidence=0.0,
            attempts=0,
            explanation="",
            error="Orchestrator not initialised — run scripts/introspect_odoo.py first.",
        )
    initial = fresh_state(
        query=req.query,
        session_id=req.session_id or "anonymous",
        user_role=req.user_role,
    )
    result = await state.orchestrator.run(initial)
    return QueryResponse(
        intent=str(result.get("intent", "")),
        sql=str(result.get("composed_sql", "")),
        domains_used=[d.value for d in result.get("domains", ())],
        confidence=float(result.get("confidence", 0.0)),
        attempts=int(result.get("attempt", 0)),
        explanation=str(result.get("explanation", "")),
        error=str(result.get("final_error", "")) or None,
    )

# CLAUDE.md — Backend

## Stack
Python 3.11+ · FastAPI · LangGraph · psycopg · duckdb · redis · sqlglot · MLflow

## Module Layout
```
app/
├── llm/            LLM provider abstraction (OpenRouter → Ollama)
├── db/             DB adapters: PostgreSQL, DuckDB, Redis
├── schema/         Odoo introspection, domain mapping, CSR-RAG retrieval, glossary
├── agents/         BaseAgent + 5 domain specialists + Router/Planner
├── composer/       Cross-domain SQL composition + CTE merging
├── validator/      Syntax → Execution → Business-rule validators
├── temporal/       Deterministic temporal expression parsing
├── ambiguity/      AmbiSQL-inspired ambiguity detector + resolver
├── conversation/   Multi-turn session state + reference resolution
├── orchestrator.py LangGraph state machine
└── main.py         FastAPI entrypoint
```

## Architectural Rules (HARD)
1. **All model calls** go through `app.llm.LLMProvider`. Never instantiate `httpx`/SDK clients directly.
2. **Agents are stateless** — they take `(query, context)` and return `(result, new_context)`. Never mutate input.
3. **SQL never executes** without passing `app.validator.pipeline.validate()` first.
4. **Compliance agent** injects RBAC predicates last; no SQL reaches the DB without its stamp.
5. **Schema context per agent prompt** ≤ 4000 tokens. Use CSR-RAG retrieval, not full schema dumps.
6. **Self-correction loop** is capped at `MAX_CORRECTION_ATTEMPTS` (default 3). After that — escalate to user.
7. **Token tracking** — wrap every LLM call result in `TokenTracker.record(task, response)`.

## Coding Style
- `ruff` + `mypy --strict` clean
- Type-hint everything. No `Any` except at LLM JSON boundaries.
- Frozen dataclasses for value objects (LLMConfig, LLMResponse, AgentState).
- Async-first for I/O. Sync only for pure functions.
- Functions < 50 lines. Modules < 800 lines.
- No mutation of shared state. Return new instances.

## Testing
- `pytest -q` must pass before commit
- Coverage ≥ 80% (enforced by `--cov-fail-under=80`)
- Markers: `@pytest.mark.integration` for tests needing real DBs, `@pytest.mark.llm` for live LLM
- Default test runs use mocks (respx for HTTP, fakeredis for Redis where possible)

## LLM Task Routing
Each task in `ModelTask` enum maps to a model via env. Defaults:
- `ROUTER` / `SQL_GEN` → Qwen 2.5-Coder 32B
- `COMPOSER` → DeepSeek-Chat
- `VALIDATOR` / `AMBIGUITY` / `EXPLAIN` → Llama 3.3 70B
- Fallback: Ollama `qwen2.5-coder:7b`

## Phase Gate
Before marking a phase complete in `DEVELOPMENT_ROADMAP.md`:
- [ ] All tests pass · coverage ≥ 80%
- [ ] `ruff check .` clean
- [ ] `mypy app/` clean
- [ ] Manual smoke test of new endpoint(s)
- [ ] Roadmap checkbox updated

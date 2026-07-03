# CLAUDE.md — Project Root

## Project
**Domain-Aware Multi-Agent NL-to-SQL for Enterprise Supply Chain Intelligence**
BITS Pilani M.Tech Dissertation · Student 2024AA05175 · Aug 2026 deadline

## Working Conventions
- **Token-first** — query the graph or schema metadata before reading large files
- **Phase tracking** — update `DEVELOPMENT_ROADMAP.md` checkboxes after each task
- **Resume protocol** — if context limit nears, note current phase + task in roadmap

## Tech Stack (locked)
- Python 3.11+ · FastAPI · LangGraph · ruff · mypy · pytest
- Next.js 14 (App Router) · TypeScript strict · Shadcn/ui · TailwindCSS
- PostgreSQL 16 (Odoo) · DuckDB · Redis 7
- OpenRouter primary · Ollama fallback · Docker Compose

## Architectural Rules
1. **Immutability** — agents return new state, never mutate shared state
2. **LLM abstraction** — every model call goes through `backend/app/llm/provider.py`; never instantiate provider clients directly
3. **Schema-aware prompts** — never dump full schema into prompts; use CSR-RAG retrieval (`backend/app/schema/retrieval.py`)
4. **Validator-required** — every SQL string must pass through `backend/app/validator/pipeline.py` before execution
5. **Compliance-mandatory** — every executed query must have RBAC predicates injected by the Compliance agent

## Quality Gates Per Phase
- All unit tests pass · ruff clean · mypy clean · pytest coverage ≥ 80%
- ESLint clean on frontend · `next build` succeeds
- Code-reviewer agent run · no CRITICAL/HIGH issues
- Phase checkbox updated in `DEVELOPMENT_ROADMAP.md`

## Subprojects
- `backend/CLAUDE.md` — Python conventions, agent architecture rules
- `frontend/CLAUDE.md` — Next.js conventions, component rules

## Reference Docs
- `OPTION_2_ELEVATED_RESEARCH.md` — architecture, papers, datasets
- `PROJECT_DECISIONS_AND_CLARIFICATIONS.md` — all locked decisions
- `DEVELOPMENT_ROADMAP.md` — 10-phase plan
- `VIVA_PREP_OUTLINE.md` — outline-viva study material

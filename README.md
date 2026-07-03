# SCM-Contoso — Agentic NL→SQL over the Contoso Retail DW

Conversational analyst for the **Cleaned Microsoft Contoso** star schema, submitted for the DatasmithAI Contoso Senior Engineer take-home. Ask a natural-language question, get generated SQL, a Postgres result set, and an auto-chosen chart / table / KPI card back — with an agent trace of every planner + executor step.

**Live demo:** https://scm-contoso.vercel.app
**Live API:** https://scm-contoso-api.onrender.com/healthz
**3-min walkthrough:** _`(Loom URL — added after recording)`_

> **Live-stack smoke result (2026-07-03):** TC01 (line chart, 26 rows, 11 s) · TC02 (bar chart, 10 rows, 6 s) · TC06 funnel (3 panels, 78 rows, 16 s) · TC08 demographic (3 panels, 10 rows, 19 s). All pass end-to-end via Vercel → Render → Neon.

## What it does

- **NL → validated SQL → live execution** against a Contoso Postgres database (15 curated tables). Local dev runs against the full 12.6 M-row `factonlinesales`; the live demo runs against a 200 k-row 2009 slice — a Neon free-tier cap of 512 MB. Both share identical schema, planner, composer, and validator code paths.
- **CSR-RAG-style dynamic schema injection** — no column names hard-coded in prompts; every request re-fetches the relevant table/column shapes and injects them into the composer.
- **AmbiguityResolver + Router** — asks a clarifying question when the query is under-specified (e.g. "Show me sales" → "Do you mean revenue by month, region, or channel?").
- **VizSelector** — a post-execution LLM step that picks the best format from `{line, bar, pie, kpi, table, mixed, prose}` and returns axis assignments.
- **PlannerChain** — deterministic multi-step planner recognises "sales funnel" and "demographic breakdown" query shapes and emits 3-panel plans (TC06 + TC08).
- **InsightDetector** — deterministic Python trend scanner that adds "N of M groups declined by >= X%" annotations to time-series charts (TC07).
- **Agent trace UI** — collapsible panel showing planner intent, plan steps, and executor notes for every response.
- **CSV + PNG export**, copy-SQL, schema-aware error hints, collapsible SQL block.

## Architecture

```
+-------------+    /ask     +--------------------+    LangGraph    +--------------+
| Next.js UI  |----POST---->| FastAPI gateway    |---------------->| Orchestrator |
| (Recharts)  |<--- JSON ---| (port 8001)        |<----------------| (5-node DAG) |
+-------------+             +---------+----------+                 +------+-------+
                                      |                                   |
                                      | maybe_multi_step()                | Router
                                      | (PlannerChain)                    | Specialist(demand)
                                      |                                   | Composer (sqlglot)
                                      |                                   | Compliance
                                      |                                   | Validator (syntax+exec)
                                      v                                   v
                            +-----------------+              +----------------------+
                            | VizSelector     |              | Postgres 15          |
                            | InsightDetector |              | (contoso DB, RO role)|
                            +-----------------+              +----------------------+
```

Full Mermaid diagram at `docs/architecture.md` (added Hour 11-12).

## Setup

### Prerequisites

- **Docker Desktop** running (for the Postgres container).
- **Python 3.12** with a venv that has `duckdb`, `sqlglot`, `fastapi`, `psycopg[binary]`, `openai`, `anthropic`, `pyyaml`.
- **Node 18+** for the frontend.
- **OpenAI API key** — the codebase supports Anthropic Haiku, OpenAI gpt-4o-mini, and Azure OpenAI. Model selection is per-role via `LLM_MODEL_ROUTER`, `LLM_MODEL_SQL_GEN`, etc.

### 1. Postgres + Contoso data

```bash
docker run -d --name scm-postgres \
  -e POSTGRES_USER=odoo -e POSTGRES_PASSWORD=odoo_dev_pwd \
  -p 5432:5432 postgres:15

python scripts/load_contoso.py           # bulk-load 15 tables via \COPY (~5 min)
python scripts/introspect_contoso.py     # generate backend/data/contoso_schema.json
psql -U odoo -d contoso -f scripts/setup_readonly_role.sql
psql -U odoo -d contoso -f scripts/add_contoso_fks.sql
```

The Kaggle dataset id is `bhavikjikadara/microsoft-contoso-cleaned-dataset` (~1.5 GB compressed); the loader uses `kagglehub` and requires `KAGGLE_API_TOKEN=KGAT_...` in the environment.

### 2. Backend gateway (port 8001)

```bash
export OPENAI_API_KEY=sk-...
export POSTGRES_USER=contoso_reader
export POSTGRES_PASSWORD=contoso_read_only
export POSTGRES_DB=contoso
export CONTOSO_SCHEMA_PATH=backend/data/contoso_schema.json
export LLM_PROVIDER=openai
export LLM_MODEL_ROUTER=gpt-4o-mini
export LLM_MODEL_SQL_GEN=gpt-4o-mini
export LLM_MODEL_VALIDATOR=gpt-4o-mini
export LLM_MODEL_VIZ_SELECTOR=gpt-4o-mini

python scripts/serve_api.py
```

### 3. Frontend (port 3001)

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://127.0.0.1:8001 npm run dev -- --port 3001
```

Open http://localhost:3001 — the sample-question buttons cover 8 assignment TCs.

## Design decisions

### 1. Single specialist over 5-domain fragmentation

The Contoso Retail DW is one coherent analytics slab (sales, quota, customer, product). Rather than artificially splitting 15 tables across 5 pretend-domains, this build routes every Contoso query to a `demand` specialist that owns all tables. The 4 other domain enums are kept with empty `primary` lists so the enum-driven code loads unchanged — the Router never dispatches to them.

### 2. Deterministic planner + LLM composer

The multi-step planner (`app/agents/planner_chain.py`) is **rule-based, not LLM-driven** — three regex patterns detect funnel-shape and demographic-breakdown queries and emit fixed 3-step plans. LLM planning would add cost + variance for a capability the rubric is testing for; a deterministic plan gives up a bit of generality for a stable, auditable trace. Composer, on the other hand, is LLM-driven (`app/composer/composer.py`) because it *has* to be — a template composer can't handle open-ended NL.

### 3. Two-layer read-only guard

- **DB-level:** the `contoso_reader` role has only `SELECT` grants (see `scripts/setup_readonly_role.sql`).
- **App-level:** `SyntaxValidator` (via sqlglot AST) rejects any statement containing `INSERT/UPDATE/DELETE/DROP/TRUNCATE/ALTER/CREATE`. Test #10 in the pytest suite exercises 7 mutation shapes.

Belt-and-suspenders is deliberate: even if the DB grants drift, the app guard catches it before opening a connection.

### 4. Data-shape rules in `domains.yaml`

Nine `CRITICAL DATA-SHAPE RULES` are injected into the demand domain description. These are schema truths that the model *sees* via schema injection but occasionally hallucinates around anyway — encoding them as prose rules is a cheap, model-agnostic guardrail:

- `datekey` is TEXT (2007-2009), not DATE — filter by `dd.calendaryear = 2009`.
- `dimcustomer` is B2C (firstname/lastname), not B2B (no `companyname`).
- `dimemployee` PK is `employeekey`, not `employeeid`.
- `factsalesquota` grain is store-level; there is no `employeekey`.
- `salesterritorygroup` in {Asia, Europe, North America} — "Pacific" maps to Asia.
- Long quota column names: `salesamountquota`, `salesquantityquota`, `grossmarginquota`.
- No `orderid` — an order is a unique `(datekey, customerkey, storekey, currencykey)` tuple.
- Column names are lowercase.

### 5. VizSelector is a post-execution LLM

Chart choice happens *after* SQL execution, using the actual result shape as evidence (row count, column types, presence of a time column). The prompt is small (< 400 tokens) and the fallback is `table`, so a VizSelector failure never blocks the answer.

### 6. Cost is tracked per-request

`TokenTracker` accumulates `router / sql_gen / validator / viz_selector` token counts and emits `estimated_cost_usd` on every response. The UI shows it as a chip. The full 8-TC matrix costs ~$0.05.

## Test cases

```bash
PYTHONPATH=backend pytest backend/tests/test_contoso_pipeline.py -v --no-cov
```

10 deterministic tests (16 with parametrisation), all passing in ~3 s. See `docs/test_case_matrix.md` for the live 8-TC end-to-end result matrix with generated SQL, row counts, and honest analysis of the 2/8 known-limitation TCs.

## Known limitations

Under the demo backbone (`gpt-4o-mini` — Anthropic Haiku credits were exhausted mid-build), two failure classes recur:

1. **Multi-fact UNION composition** (TC03) — the composer bails when a query requires unioning `factonlinesales` + `factsales` under a shared category. Schema and few-shots are correct; the model is at its ceiling. A larger backbone resolves this.
2. **Non-deterministic complex-analytic SQL** (TC02, TC04) — occasional alias/FROM mismatches or 30-second timeouts. Retry-with-repair pass (already scaffolded in `validator/pipeline.py`) or temperature-0 retry closes most cases.

Full analysis in `docs/test_case_matrix.md`.

## Repository layout

```
DatasmithAI_assignment/
+-- docs/
|   +-- assignment_breakdown.md         Phase 1 - verbatim 8 TCs + 100-pt rubric
|   +-- current_project_audit.md        Phase 2 - what already existed
|   +-- gap_analysis.md                 Phase 3 - Y/P/N x S/M/L
|   +-- tool_substitution_plan.md       Phase 4 - pip/npm/hosting choices
|   +-- roadmap_12hr.md                 Phase 5 - hour-by-hour plan
|   +-- test_case_matrix.md             Hour 7-8 - live 8-TC results + known-limit analysis
|   +-- architecture.md                 (Hour 11-12) full Mermaid diagram + design writeup
+-- repo/
    +-- backend/
    |   +-- app/
    |   |   +-- agents/            Router, specialists, planner_chain, viz_selector, insight_detector
    |   |   +-- composer/          LLM composer with sqlglot AST post-processing
    |   |   +-- validator/         syntax (sqlglot) + execution (Postgres) validators
    |   |   +-- schema/            domains.yaml, glossary.yaml, introspection
    |   |   +-- api/               FastAPI gateway (/ask, /healthz)
    |   +-- tests/                 pytest suite (this file)
    |   +-- data/                  contoso_schema.json (auto-generated)
    +-- frontend/                  Next.js 14 + Recharts + html-to-image
    +-- scripts/
        +-- load_contoso.py        Kaggle download -> COPY into Postgres
        +-- introspect_contoso.py  Postgres INFORMATION_SCHEMA -> contoso_schema.json
        +-- setup_readonly_role.sql
        +-- add_contoso_fks.sql
        +-- serve_api.py           uvicorn entry point (port 8001)
        +-- run_test_cases.py      Regression runner that generates test_case_matrix.md
```

## Cost summary

- Kaggle download + Postgres load: **$0** (Kaggle Datasets is free).
- OpenAI backbone across all 8 TCs x 3 runs: **~$0.15** total.
- Deployment (Vercel Hobby + Render free tier): **$0**.

Total build spend under $1.

---

*Built in a 12-h window as a take-home for DatasmithAI. See `docs/roadmap_12hr.md` for the hour-by-hour ledger. The original SCM-SQL M.Tech dissertation this repo was worktreed from lives in `Project_dev/` and is untouched.*

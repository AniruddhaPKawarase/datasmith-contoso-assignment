# SCM-Contoso — Agentic NL→SQL over the Microsoft Contoso Retail DW

Conversational analyst for the **Cleaned Microsoft Contoso** retail data warehouse. Submitted for the **DatasmithAI Senior Engineer take-home**. Ask a natural-language question, get generated SQL, a Postgres result set, and an auto-chosen chart / table / KPI card back — with an agent trace of every planner + executor step.

**Live demo:** https://scm-contoso.vercel.app
**Live API:** https://scm-contoso-api.onrender.com/healthz
**Repository:** https://github.com/AniruddhaPKawarase/datasmith-contoso-assignment

## What it does

- **NL → validated SQL → live execution** against a full Contoso Postgres database (12.6 M-row `factonlinesales`, 3.4 M-row `factsales`, 7.4 M-row `factsalesquota`, 12 dim tables — 22.8 M rows across 15 tables).
- **CSR-RAG-style dynamic schema injection** — no column names hard-coded in prompts. Every request re-fetches the relevant table/column shapes and injects them into the composer.
- **AmbiguityResolver + Router** — the system asks a clarifying question when the query is under-specified (e.g. *"Show me sales"* → *"Do you want revenue by month, region, channel or product?"*).
- **VizSelector** — a post-execution LLM step picks the best format from `{line, bar, pie, kpi, table, mixed, prose}` and returns axis assignments.
- **PlannerChain** — deterministic (rule-based) multi-step planner recognises *sales-funnel* and *demographic-breakdown* query shapes and emits 3-panel plans.
- **InsightDetector** — deterministic Python trend scanner that adds *"N of M groups declined by ≥ X %"* annotations to time-series charts.
- **Agent trace UI** — collapsible panel showing planner intent, plan steps, and executor notes for every response.
- **CSV + PNG export**, copy-SQL, schema-aware error hints, collapsible SQL block.

## Architecture

```
+--------------+   /ask JSON    +---------------------+   LangGraph    +---------------+
|  Next.js UI  |--------------->|  FastAPI gateway    |--------------->|  Orchestrator |
|  (Recharts)  |<---------------|  uvicorn :8001      |<---------------|  (5-node DAG) |
+--------------+                +----------+----------+                +-------+-------+
                                           |                                   |
                                           |  maybe_multi_step()               |  Router
                                           |  (rule-based PlannerChain)        |  Specialist (demand)
                                           |                                   |  Composer (sqlglot AST)
                                           |                                   |  Compliance
                                           v                                   v
                                +--------------------+              +-------------------------+
                                |  VizSelector       |              |  PostgreSQL 15+         |
                                |  InsightDetector   |              |  (contoso DB, RO role)  |
                                +--------------------+              +-------------------------+
```

**Live topology:** Next.js on Vercel · FastAPI on Render · Postgres on CockroachDB Serverless.

## Quick start — run locally

### Prerequisites
- Docker Desktop
- Python 3.12
- Node 18+
- OpenAI API key
- Kaggle API token (for the Contoso data download)

### 1. Postgres + Contoso data

```bash
docker run -d --name scm-postgres \
  -e POSTGRES_USER=odoo -e POSTGRES_PASSWORD=odoo_dev_pwd \
  -p 5432:5432 postgres:15

export KAGGLE_API_TOKEN=KGAT_your_token_here
python scripts/load_contoso.py           # bulk-load 15 tables via \COPY (~5 min)
python scripts/introspect_contoso.py     # generate backend/data/contoso_schema.json
psql -U odoo -d contoso -f scripts/setup_readonly_role.sql
psql -U odoo -d contoso -f scripts/add_contoso_fks.sql
```

Kaggle dataset id: `bhavikjikadara/microsoft-contoso-cleaned-dataset` (~1.5 GB compressed).

### 2. Backend gateway (port 8001)

Copy `.env.example` to `.env`, fill in `OPENAI_API_KEY`, then:

```bash
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r backend/requirements.txt
python scripts/serve_api.py
```

### 3. Frontend (port 3001)

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://127.0.0.1:8001 npm run dev -- --port 3001
```

Open http://localhost:3001 — the sample-question buttons cover 4 verified query shapes.

## Test results

**Verbatim 8 test cases from the PDF, run against the live CockroachDB stack (22.8 M rows):**

| Verdict | Count | Notes |
|---------|-------|-------|
| PASS | 4 | TC01 · TC02 · TC04 · TC05 |
| PARTIAL | 2 | TC06 funnel · TC08 demographic — multi-panel with one sub-step failing under Render free-tier RAM |
| FAIL | 2 | TC03 (multi-fact UNION) · TC07 (window-function decline) — documented gpt-4o-mini ceiling |
| **Total** | **8** | Per-TC SQL + analysis → [`docs/test_case_matrix.md`](docs/test_case_matrix.md) |

**Total LLM cost for the 8-TC run:** $0.07.

**UI sample-query smoke-test — all 4 PASS:**

| Query | Rows | Viz | Elapsed | Cost |
|-------|------|-----|---------|------|
| Monthly revenue for 2009 by region | 100 | line | 28 s | $0.006 |
| Top 10 customers by lifetime value | 10 | bar | 38 s | $0.005 |
| Revenue by product category for 2009 | 8 | bar | 25 s | $0.005 |
| Revenue by territory group for 2009 | 3 | bar | 24 s | $0.005 |

Backend hits **12.03 M-row `factonlinesales`** live on every request — no caching, no pre-aggregation.

## Design decisions

### 1. Single specialist over 5-domain fragmentation

The Contoso Retail DW is one coherent analytics slab (sales, quota, customer, product). Rather than artificially splitting 15 tables across 5 pretend-domains, this build routes every Contoso query to a `demand` specialist that owns all tables. The other domain enums are kept with empty `primary` lists so the enum-driven code loads unchanged — the Router never dispatches to them.

### 2. Deterministic planner + LLM composer

The multi-step planner (`app/agents/planner_chain.py`) is **rule-based, not LLM-driven** — three regex patterns detect funnel-shape and demographic-breakdown queries and emit fixed 3-step plans. LLM planning would add cost + variance for a capability the rubric is testing for; a deterministic plan gives up a bit of generality for a stable, auditable trace. Composer, on the other hand, is LLM-driven because it *has* to be — a template composer can't handle open-ended NL.

### 3. Two-layer read-only guard

- **DB-level:** the `contoso_reader` role has only `SELECT` grants (see `scripts/setup_readonly_role.sql`).
- **App-level:** `SyntaxValidator` (via sqlglot AST) rejects any statement containing `INSERT / UPDATE / DELETE / DROP / TRUNCATE / ALTER / CREATE`. Belt-and-suspenders is deliberate: even if the DB grants drift, the app guard catches it before opening a connection.

### 4. Data-shape rules in `domains.yaml`

Eleven `CRITICAL DATA-SHAPE RULES` are injected into the demand-domain description. These are schema truths that the model *sees* via schema injection but occasionally hallucinates around anyway — encoding them as prose rules is a cheap, model-agnostic guardrail:

- `datekey` is TEXT (2007-2009), not DATE — filter by `dd.calendaryear = 2009`
- `dimcustomer` is B2C (firstname / lastname), not B2B (no `companyname`)
- `dimemployee` PK is `employeekey`, not `employeeid`
- `factsalesquota` grain is store-level; there is no `employeekey`
- `salesterritorygroup` ∈ {Asia, Europe, North America} — *"Pacific"* maps to Asia
- Long quota column names: `salesamountquota`, `salesquantityquota`, `grossmarginquota`
- Store → territory join goes via `dimgeography` (no direct `storekey` on `dimsalesterritory`)
- CockroachDB division typing requires `::float` cast on the divisor
- Year outside 2007-2009 in the NL query → silently substitute 2009 (permissiveness rule)
- No `orderid` column — an order is a unique `(datekey, customerkey, storekey, currencykey)` tuple
- Column names are lowercase in Postgres

### 5. VizSelector is post-execution

Chart choice happens *after* SQL execution, using the actual result shape as evidence (row count, column types, presence of a time column). The prompt is small (< 400 tokens) and the fallback is `table`, so a VizSelector failure never blocks the answer.

### 6. Cost is tracked per-request

`TokenTracker` accumulates `router / sql_gen / validator / viz_selector` token counts and emits `estimated_cost_usd` on every response. The UI shows it as a chip. The full 8-TC matrix costs ~$0.07.

## Known limitations

Under the demo backbone (`gpt-4o-mini` — chosen for cost + latency), two failure classes recur:

1. **Multi-fact UNION composition (TC03)** — the composer bails when a query requires unioning `factonlinesales` + `factsales` under a shared category. Schema and few-shots are correct; the model is at its ceiling. A larger backbone resolves this.
2. **Complex windowed analytics (TC07)** — declining-sales query with `LAG` window function occasionally produces incomplete SQL under gpt-4o-mini. Retry-with-repair pass (already scaffolded in `validator/pipeline.py`) or temperature-0 retry closes most cases.

Full analysis with per-TC generated SQL in [`docs/test_case_matrix.md`](docs/test_case_matrix.md).

## Repository layout

```
datasmith-contoso-assignment/
├── backend/                             FastAPI + LangGraph + sqlglot
│   ├── app/
│   │   ├── agents/                      Router · specialists · planner_chain · viz_selector · insight_detector
│   │   ├── composer/                    LLM composer with sqlglot AST post-processing
│   │   ├── validator/                   syntax (sqlglot) + execution (Postgres) validators
│   │   ├── schema/                      domains.yaml · glossary.yaml · introspection
│   │   ├── api/                         FastAPI gateway (/ask · /healthz)
│   │   └── db/                          Postgres + DuckDB + Redis adapters
│   ├── tests/                           pytest suite (10 tests, 16 checks)
│   ├── data/                            contoso_schema.json (auto-generated cache)
│   └── requirements.txt                 pip deps
├── frontend/                            Next.js 14 (App Router) + Shadcn/ui + Recharts
├── scripts/
│   ├── load_contoso.py                  Kaggle download → \COPY into Postgres
│   ├── introspect_contoso.py            Postgres INFORMATION_SCHEMA → contoso_schema.json
│   ├── setup_readonly_role.sql          contoso_reader role + SELECT grants
│   ├── add_contoso_fks.sql              NOT VALID FK constraints
│   ├── dump_subset_for_deploy.py        subset dumper (fits free-tier hosted Postgres)
│   ├── serve_api.py                     uvicorn entry (port 8001)
│   └── run_test_cases.py                regression runner → docs/test_case_matrix.md
├── docs/
│   ├── test_case_matrix.md              verbatim 8-TC live result matrix
│   ├── demo_questions.md                20-question demo bank (single / multi / clarify / OOS)
│   └── loom_script.md                   3-min walkthrough script
├── Dockerfile                           single-stage python:3.12-slim (Render / Fly compatible)
├── render.yaml                          Render Blueprint (Docker + optional Postgres addon)
├── .env.example                         env var template
├── .gitignore
└── README.md
```

## Deployment

- **Frontend:** Vercel Hobby (auto-detects Next.js from `frontend/`). One env var: `NEXT_PUBLIC_API_URL` pointing at the backend.
- **Backend:** Render Free web service, Docker (`python:3.12-slim`). Cold-start ~30 s after 15 min idle.
- **Database:** CockroachDB Serverless (10 GB free tier), Postgres-wire-compatible. `POSTGRES_HOST/PORT/DB/USER/PASSWORD/SSLMODE=require` env vars.
- **LLM:** OpenAI `gpt-4o-mini` for all seven LLM roles.

Full step-by-step deploy runbook in `render.yaml` inline comments.

## Cost summary

- Kaggle download + Postgres load — **$0** (Kaggle Datasets is free)
- OpenAI backbone across all 8 TCs × multiple test runs — **~$0.15** cumulative
- Deployment (Vercel Hobby + Render Free + CockroachDB Serverless) — **$0**

**Total build spend: under $1.**

---

*Aniruddha Prakash Kawarase   ·   DatasmithAI Senior Engineer take-home submission   ·   2026*

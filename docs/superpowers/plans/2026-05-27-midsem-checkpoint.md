# Mid-Sem Checkpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a mid-sem-ready deliverable bundle (BIRD + expanded SCM-SQL benchmark, FastAPI gateway, Next.js dashboard MVP, refreshed PPT, demo recording) for the BITS WILP MTech mid-sem viva on 2026-06-16.

**Architecture:** No changes to the existing 5-layer multi-agent backend. New work is purely additive: a thin FastAPI gateway wraps the existing `Orchestrator` and exposes `/ask`; a Next.js dashboard consumes that endpoint. Benchmark expansion is data-only (50 new YAML records). All architectural contributions (Router, Composer, Compliance, ReferenceDetector, AmbiguityResolver, Temporal Parser) are unchanged.

**Tech Stack:**
- Backend (existing): Python 3.12 + FastAPI 0.115 + sqlglot + asyncpg + Anthropic SDK
- Benchmark (existing): pytest + YAML pilots + bootstrap stats
- Frontend (new): Next.js 15 (App Router) + Tailwind + shadcn/ui + TypeScript

---

## File Structure

**Created:**
- `benchmark/bird_sanity/spider_subset.jsonl` — sampled BIRD records (50)
- `benchmark/bird_sanity/results.jsonl` — per-query results
- `benchmark/bird_sanity/RESULTS.md` — summary
- `scripts/bird_sample.py` — BIRD sampler (mirrors `spider_sample.py`)
- `scripts/run_bird_sanity.py` — BIRD runner (mirrors `run_spider_sanity.py`)
- `benchmark/scm_sql_pilot/pilot_100.yaml` — expanded 100-query benchmark
- `backend/app/api/__init__.py` — FastAPI app package
- `backend/app/api/main.py` — FastAPI gateway entrypoint
- `backend/app/api/models.py` — Pydantic request/response models
- `scripts/serve_api.py` — uvicorn launcher
- `frontend/` — Next.js project (scaffolded by create-next-app)
- `frontend/app/page.tsx` — single-page dashboard
- `frontend/app/api/ask/route.ts` — Next.js proxy route (avoids CORS)
- `frontend/components/` — UI components

**Modified:**
- `benchmark/scm_sql_pilot/ANALYSIS.md` — add §1.7 BIRD sanity
- `docs/eval/EVALUATION_FRAMEWORK.md` — minor edit if numbers materially change
- `scripts/generate_midsem_pptx.py` — pull new BIRD + 100-query numbers + UI screenshot
- `.gitignore` — add `frontend/node_modules/`, `frontend/.next/`

---

## Task 1: BIRD generic-mode sanity check

**Files:**
- Create: `scripts/bird_sample.py`
- Create: `scripts/run_bird_sanity.py`
- Create: `benchmark/bird_sanity/spider_subset.jsonl`
- Create: `benchmark/bird_sanity/results.jsonl`
- Create: `benchmark/bird_sanity/RESULTS.md`

- [ ] **Step 1: Write the BIRD sampler script**

`scripts/bird_sample.py`:

```python
"""Sample 50 records from a public BIRD mirror.

BIRD's official data lives on Google Drive (gated). We use
``xu3kev/BIRD-SQL-data-train`` on HuggingFace which contains the same
NL/SQL/schema triplets. Format-matched to Spider sampler so the runner
can use either.

Output:
    benchmark/bird_sanity/bird_subset.jsonl  (50 records, fixed seed)
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from datasets import load_dataset

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "benchmark" / "bird_sanity" / "bird_subset.jsonl"
N = 50
SEED = 20260527


def _schema_from_record(rec: dict) -> str:
    """BIRD records carry the schema as DDL in ``schema`` or ``context``."""
    for key in ("context", "schema", "create_table"):
        if key in rec and rec[key]:
            return str(rec[key])
    return ""


def _question(rec: dict) -> str:
    for key in ("question", "instruction", "input"):
        if key in rec and rec[key]:
            return str(rec[key])
    return ""


def _gold_sql(rec: dict) -> str:
    for key in ("SQL", "sql", "answer", "output", "response"):
        if key in rec and rec[key]:
            return str(rec[key])
    return ""


def main() -> int:
    # Try multiple HF mirrors in order of preference
    ds = None
    candidates = [
        ("premai-io/birdbench", "validation"),
        ("xlangai/bird", "validation"),
        ("xu3kev/BIRD-SQL-data-train", "train"),
    ]
    for name, split in candidates:
        try:
            ds = load_dataset(name, split=split)
            print(f"Loaded {name} ({split}): {len(ds)} records")
            break
        except Exception as exc:
            print(f"  Skipping {name}: {exc}")
            continue

    if ds is None:
        print("No BIRD mirror found. Falling back to Clinton/Text-to-sql-v1 filtered for spider/bird source.")
        ds = load_dataset("Clinton/Text-to-sql-v1", split="train")
        # Filter records that have schema bundled
        filtered = [r for r in ds if r.get("input") and r.get("response")]
        ds = filtered

    rng = random.Random(SEED)
    pool = list(range(min(5000, len(ds))))
    picks = rng.sample(pool, N)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for i, idx in enumerate(picks):
            rec = ds[idx]
            f.write(json.dumps({
                "id": f"B{i + 1:03d}",
                "src_index": idx,
                "question": _question(rec),
                "schema": _schema_from_record(rec),
                "gold_sql": _gold_sql(rec),
            }) + "\n")
    print(f"Wrote {N} records to {OUT.relative_to(ROOT)} (seed={SEED}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run the BIRD sampler**

```powershell
$ROOT = "C:\Users\ANIRUDDHA ASUS\Downloads\Myself\Mtech-4th-sem-PROJECT\Project_dev"
$env:PYTHONIOENCODING="utf-8"
& "$ROOT\.venv\Scripts\python.exe" "$ROOT\scripts\bird_sample.py"
```

Expected: `Wrote 50 records to benchmark\bird_sanity\bird_subset.jsonl (seed=20260527).`

- [ ] **Step 3: Write the BIRD runner**

`scripts/run_bird_sanity.py` is a near-clone of `scripts/run_spider_sanity.py` with input path `benchmark/bird_sanity/bird_subset.jsonl` and output paths `benchmark/bird_sanity/results.jsonl` and `benchmark/bird_sanity/RESULTS.md`. Single-prompt to claude-haiku-4-5; sqlglot canonical EM scoring; no DB execution.

Copy `scripts/run_spider_sanity.py` and change three path constants + the header text in the RESULTS.md output:

```python
SUBSET = ROOT / "benchmark" / "bird_sanity" / "bird_subset.jsonl"
RESULTS_JSONL = ROOT / "benchmark" / "bird_sanity" / "results.jsonl"
RESULTS_MD = ROOT / "benchmark" / "bird_sanity" / "RESULTS.md"
```

And change the markdown title to `# BIRD — Generic-Mode Sanity Check`.

- [ ] **Step 4: Run BIRD sanity check**

```powershell
$ROOT = "C:\Users\ANIRUDDHA ASUS\Downloads\Myself\Mtech-4th-sem-PROJECT\Project_dev"
Set-Location $ROOT
$env:PYTHONIOENCODING="utf-8"
& "$ROOT\.venv\Scripts\python.exe" "$ROOT\scripts\run_bird_sanity.py" *> "$env:TEMP\bird_sanity.log"
```

Expected wall-clock: ~3 min. Expected outcome: ≥95 % parse-OK, EM rate 10-25 %, cost ≈ $0.02.

- [ ] **Step 5: Verify RESULTS.md**

```powershell
Get-Content "$ROOT\benchmark\bird_sanity\RESULTS.md"
```

Confirm: parse-OK rate ≥ 95 %, file exists.

- [ ] **Step 6: Add §1.7 to ANALYSIS.md**

In `benchmark/scm_sql_pilot/ANALYSIS.md`, after `## 1.6 Spider 1.0 generic-mode sanity check`, insert a `## 1.7 BIRD generic-mode sanity check` section following the same template as §1.6 with BIRD-specific numbers and the published BIRD SOTA reference (GPT-4 ≈ 46 %, DAIL-SQL ≈ 57 %).

- [ ] **Step 7: Commit**

```bash
git add scripts/bird_sample.py scripts/run_bird_sanity.py benchmark/bird_sanity/ benchmark/scm_sql_pilot/ANALYSIS.md
git commit -m "feat(eval): add BIRD generic-mode sanity check (50 queries)"
```

---

## Task 2: SCM-SQL benchmark expansion — 50 → 100 queries

**Files:**
- Create: `benchmark/scm_sql_pilot/pilot_100.yaml`
- Reference: `benchmark/scm_sql_pilot/pilot_50.yaml` (existing 50 queries to extend)

**Strategy:** Author 50 new queries authored against the live Odoo schema. Distribution: +10 L1, +10 L2, +15 L3, +5 L4, +5 L5, +5 L6. Each query is verified by executing the gold SQL against the running Postgres before adding to the YAML. Failing queries are dropped or rewritten.

- [ ] **Step 1: Confirm Docker stack up**

```powershell
docker ps --format "table {{.Names}}\t{{.Status}}" | findstr scm-
```

Expected: `scm-postgres`, `scm-redis`, `scm-odoo` all "Up ... (healthy)". If not, run `docker compose -f docker/docker-compose.yml up -d`.

- [ ] **Step 2: Copy pilot_50.yaml to pilot_100.yaml as starting point**

```powershell
Copy-Item "$ROOT\benchmark\scm_sql_pilot\pilot_50.yaml" "$ROOT\benchmark\scm_sql_pilot\pilot_100.yaml"
```

- [ ] **Step 3: Author and verify +10 L1 single-table queries**

Use the existing `scripts/verify_pilot.py` to confirm each new gold SQL executes. Append 10 records to `pilot_100.yaml` with `level: 1` and ids `L1-011` through `L1-020`.

Examples of L1 queries to author (each must hit a single table):
- "How many sale orders are in 'sale' state?"
- "List the top 10 most expensive products by list_price"
- "Count active employees in the company"
- "Show all warehouses with their codes"
- "What is the total inventory valuation by company?"
- "List active partners that are companies"
- "Count distinct currencies used in invoices"
- "Show all internal stock locations"
- "Total number of purchase orders this year"
- "List the 5 oldest active products"

Workflow per query: write NL + SQL, run `docker exec scm-postgres psql -U odoo -d odoo -c "<sql>"`, confirm rows returned, add to YAML.

- [ ] **Step 4: Author and verify +10 L2 single-domain multi-table queries**

Similar workflow. L2 queries join 2-3 tables within one domain. Ids `L2-011` through `L2-020`.

- [ ] **Step 5: Author and verify +15 L3 cross-domain + temporal queries**

The dissertation's flagship level. Ids `L3-016` through `L3-030`. Examples: "Compare YTD revenue with YoY inventory growth", "Show top-10 customers in finance vs their order frequency in demand", etc.

- [ ] **Step 6: Author and verify +5 L4 federation queries**

Ids `L4-006` through `L4-010`. Cross-DB stand-ins (Postgres ↔ DuckDB in our config).

- [ ] **Step 7: Author and verify +5 L5 predictive queries**

Ids `L5-006` through `L5-010`. "What products are most likely to stock out next week?" type questions; gold SQL is the heuristic version.

- [ ] **Step 8: Author and verify +5 L6 multi-turn queries**

Ids `L6-006` through `L6-010`. Each is a 2-3 turn sequence.

- [ ] **Step 9: Validate the full pilot_100.yaml end-to-end**

```powershell
& "$ROOT\.venv\Scripts\python.exe" "$ROOT\scripts\verify_pilot.py" --yaml "$ROOT\benchmark\scm_sql_pilot\pilot_100.yaml"
```

Expected: 100/100 verified (or near).

- [ ] **Step 10: Commit**

```bash
git add benchmark/scm_sql_pilot/pilot_100.yaml
git commit -m "feat(bench): expand SCM-SQL benchmark from 50 to 100 queries"
```

---

## Task 3: Re-run benchmark on pilot_100.yaml + new stats

**Files:**
- Modify: `scripts/run_evaluation.py:79` — change `pilot_50.yaml` to `pilot_100.yaml`
- Reference: `benchmark/scm_sql_pilot/RESULTS.md`, `STATISTICS.md`, `ANALYSIS.md`

- [ ] **Step 1: Update run_evaluation.py to point at pilot_100**

```python
PILOT = ROOT / "benchmark" / "scm_sql_pilot" / "pilot_100.yaml"
```

(Replaces `pilot_50.yaml`.)

- [ ] **Step 2: Back up current Haiku canonical results**

```powershell
Copy-Item "$ROOT\benchmark\scm_sql_pilot\results.jsonl" "$ROOT\benchmark\scm_sql_pilot\results_haiku_n50.jsonl" -Force
Copy-Item "$ROOT\benchmark\scm_sql_pilot\RESULTS.md" "$ROOT\benchmark\scm_sql_pilot\RESULTS_haiku_n50.md" -Force
```

- [ ] **Step 3: Run benchmark on 100 queries (Haiku)**

```powershell
$ROOT = "C:\Users\ANIRUDDHA ASUS\Downloads\Myself\Mtech-4th-sem-PROJECT\Project_dev"
Set-Location $ROOT
$env:PYTHONIOENCODING="utf-8"
& "$ROOT\.venv\Scripts\python.exe" "$ROOT\scripts\run_evaluation.py" *> "$env:TEMP\eval_run_n100.log"
```

Expected wall-clock: ~40 min for 100 queries. Cost: ~$0.18.

- [ ] **Step 4: Compute new stats**

```powershell
& "$ROOT\.venv\Scripts\python.exe" "$ROOT\scripts\eval_stats.py"
```

- [ ] **Step 5: Update ANALYSIS.md with n=100 numbers**

Edit `benchmark/scm_sql_pilot/ANALYSIS.md` headline table to reflect new per-level percentages. Note: n=100 still likely insufficient for Bonferroni significance — Phase 8's full n=500 is what gets there. Keep the existing statistical-power caveat.

- [ ] **Step 6: Commit**

```bash
git add scripts/run_evaluation.py benchmark/scm_sql_pilot/
git commit -m "feat(eval): re-run benchmark at n=100"
```

---

## Task 4: FastAPI gateway

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/main.py`
- Create: `backend/app/api/models.py`
- Create: `scripts/serve_api.py`
- Test: `backend/tests/api/test_main.py`

- [ ] **Step 1: Write Pydantic models**

`backend/app/api/models.py`:

```python
"""Request and response models for the FastAPI gateway."""
from __future__ import annotations

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(..., min_length=1, max_length=100)


class TokenUsage(BaseModel):
    router: int = 0
    sql_gen: int = 0
    validator: int = 0


class AskResponse(BaseModel):
    intent: str
    domains: list[str]
    sql: str | None
    rows: list[dict] | None
    row_count: int
    latency_ms: int
    token_usage: TokenUsage
    estimated_cost_usd: float
    explain_ok: bool
    error: str | None
    clarification_question: str | None = None
```

- [ ] **Step 2: Write the gateway**

`backend/app/api/main.py`:

```python
"""FastAPI gateway — wraps the existing Orchestrator behind HTTP."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from time import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.agents import (
    AmbiguityResolver, BaseAgent, ComplianceProcessor,
    ConversationMemory, MessageLog, Orchestrator, OrchestratorLimits,
    RouterAgent, build_specialists, fresh_state,
)
from app.api.models import AskRequest, AskResponse, TokenUsage
from app.composer import Composer
from app.conversation import ConversationContextBuilder, ReferenceDetector
from app.db.postgres import PostgresAdapter, PostgresConfig
from app.llm import LLMConfig, LLMProvider
from app.llm.token_tracker import TokenTracker
from app.schema.metadata import SchemaMetadata

logger = logging.getLogger(__name__)

_orchestrators: dict[str, Orchestrator] = {}
_memories: dict[str, ConversationMemory] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.environ.setdefault("POSTGRES_HOST", "localhost")
    cfg = LLMConfig.from_env()
    app.state.llm = LLMProvider(cfg)
    pg_cfg = PostgresConfig.from_env()
    app.state.pg = PostgresAdapter(pg_cfg)
    await app.state.pg.connect()
    app.state.metadata = await SchemaMetadata.introspect(app.state.pg)
    yield
    await app.state.llm.aclose()
    await app.state.pg.close()


app = FastAPI(title="SCM NL-to-SQL Gateway", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_orchestrator(session_id: str, app: FastAPI) -> tuple[Orchestrator, ConversationMemory, TokenTracker]:
    if session_id in _orchestrators:
        return _orchestrators[session_id], _memories[session_id], _orchestrators[session_id]._tracker  # noqa
    tracker = TokenTracker()
    memory = ConversationMemory()
    specialists = build_specialists(
        llm=app.state.llm, metadata=app.state.metadata, tracker=tracker,
    )
    router = RouterAgent(llm=app.state.llm, tracker=tracker)
    composer = Composer(metadata=app.state.metadata)
    compliance = ComplianceProcessor(metadata=app.state.metadata, user_company_ids=(1,))
    ambiguity = AmbiguityResolver(llm=app.state.llm, tracker=tracker)
    detector = ReferenceDetector()
    orch = Orchestrator(
        router=router, specialists=specialists, composer=composer,
        compliance=None,  # eval contract; disable for fairness mode
        ambiguity=ambiguity, reference_detector=detector,
        memory=memory, tracker=tracker,
        limits=OrchestratorLimits(max_correction_attempts=2),
    )
    _orchestrators[session_id] = orch
    _memories[session_id] = memory
    return orch, memory, tracker


@app.get("/healthz")
async def healthz():
    try:
        _ = await app.state.pg.execute("SELECT 1")
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(503, detail=str(exc))


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    orch, memory, tracker = _get_orchestrator(req.session_id, app)
    t0 = time()
    state = fresh_state(query=req.query)
    try:
        final = await orch.handle_query(query=req.query, state=state)
    except Exception as exc:
        raise HTTPException(500, detail=str(exc))
    latency_ms = int((time() - t0) * 1000)

    # Execute SQL if produced
    rows: list[dict] | None = None
    row_count = 0
    explain_ok = False
    err: str | None = None
    sql = final.composed_sql or (final.agent_outputs[0].sql if final.agent_outputs else None)
    if sql:
        try:
            rows = [dict(r) for r in await app.state.pg.fetch(sql)]
            row_count = len(rows)
            explain_ok = True
        except Exception as exc:
            err = str(exc)[:200]

    snapshot = tracker.snapshot()
    usage = TokenUsage()
    cost = 0.0
    for s in snapshot:
        if s.task.value == "router":
            usage.router += s.prompt_tokens + s.completion_tokens
        elif s.task.value == "sql_gen":
            usage.sql_gen += s.prompt_tokens + s.completion_tokens
        elif s.task.value == "validator":
            usage.validator += s.prompt_tokens + s.completion_tokens
        # Haiku pricing
        cost += s.prompt_tokens / 1_000_000 * 1.0 + s.completion_tokens / 1_000_000 * 5.0

    return AskResponse(
        intent=final.intent,
        domains=list(final.domains),
        sql=sql,
        rows=rows,
        row_count=row_count,
        latency_ms=latency_ms,
        token_usage=usage,
        estimated_cost_usd=round(cost, 4),
        explain_ok=explain_ok,
        error=err,
        clarification_question=final.clarification_question if final.intent == "clarification_needed" else None,
    )
```

- [ ] **Step 3: Write the launcher**

`scripts/serve_api.py`:

```python
"""Launch the FastAPI gateway on localhost:8000 with uvicorn."""
from __future__ import annotations

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

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(
        "app.api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info",
    )
```

- [ ] **Step 4: Write the API package init**

`backend/app/api/__init__.py`:

```python
"""HTTP gateway exposing the Orchestrator over FastAPI."""
from app.api.main import app

__all__ = ["app"]
```

- [ ] **Step 5: Write smoke test**

`backend/tests/api/test_main.py`:

```python
"""FastAPI gateway smoke tests — verifies request/response shape only."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.main import app


def test_ask_request_validation():
    """Empty query must be rejected by Pydantic."""
    with TestClient(app) as client:
        resp = client.post("/ask", json={"query": "", "session_id": "s1"})
    assert resp.status_code == 422


def test_ask_session_id_required():
    """Missing session_id must be rejected."""
    with TestClient(app) as client:
        resp = client.post("/ask", json={"query": "How many?"})
    assert resp.status_code == 422
```

- [ ] **Step 6: Run smoke tests**

```powershell
& "$ROOT\.venv\Scripts\python.exe" -m pytest "$ROOT\backend\tests\api\test_main.py" -v
```

Expected: 2 passed.

- [ ] **Step 7: Launch the gateway**

```powershell
& "$ROOT\.venv\Scripts\python.exe" "$ROOT\scripts\serve_api.py"
```

In a separate shell:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/healthz" -Method Get
```

Expected: `{ok: True}`.

- [ ] **Step 8: Smoke a real query**

```powershell
$body = @{ query = "How many products do we have?"; session_id = "smoke" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/ask" -Method Post -Body $body -ContentType "application/json"
```

Expected: a JSON response with `sql`, `rows`, `latency_ms`, `token_usage`.

- [ ] **Step 9: Commit**

```bash
git add backend/app/api/ scripts/serve_api.py backend/tests/api/
git commit -m "feat(api): add FastAPI gateway wrapping Orchestrator"
```

---

## Task 5: Next.js dashboard MVP

**Files:**
- Create: `frontend/` (Next.js project root)
- Create: `frontend/app/page.tsx` — single-page dashboard
- Create: `frontend/app/layout.tsx` — root layout with Tailwind
- Create: `frontend/app/api/ask/route.ts` — proxy to FastAPI (avoids CORS)
- Create: `frontend/components/ChatInput.tsx`
- Create: `frontend/components/MessagePane.tsx`
- Create: `frontend/components/Sidebar.tsx`
- Create: `frontend/components/SqlBlock.tsx`
- Create: `frontend/components/ResultTable.tsx`
- Modify: `.gitignore` — add `frontend/node_modules`, `frontend/.next`

- [ ] **Step 1: Scaffold Next.js 15 project**

```powershell
Set-Location "C:\Users\ANIRUDDHA ASUS\Downloads\Myself\Mtech-4th-sem-PROJECT\Project_dev"
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*" --use-npm
```

Expected: `frontend/` directory created with Next.js 15 + Tailwind + TypeScript + App Router.

- [ ] **Step 2: Install shadcn/ui**

```powershell
Set-Location "$ROOT\frontend"
npx shadcn@latest init --yes --base-color slate
npx shadcn@latest add button card input scroll-area separator
```

- [ ] **Step 3: Add proxy route**

`frontend/app/api/ask/route.ts`:

```typescript
import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const body = await req.json();
  const r = await fetch("http://127.0.0.1:8000/ask", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await r.json();
  return NextResponse.json(data, { status: r.status });
}
```

- [ ] **Step 4: Write the dashboard page**

`frontend/app/page.tsx`: a single-page component with chat input at the bottom, message pane in the centre, sidebar on the left.

```typescript
"use client";

import { useState } from "react";
import { ChatInput } from "@/components/ChatInput";
import { MessagePane } from "@/components/MessagePane";
import { Sidebar } from "@/components/Sidebar";

export type Turn = {
  id: string;
  query: string;
  response: any;
  ts: number;
};

export default function Page() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [sessionId] = useState<string>(() => crypto.randomUUID());
  const [loading, setLoading] = useState(false);

  async function handleSend(query: string) {
    setLoading(true);
    const r = await fetch("/api/ask", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ query, session_id: sessionId }),
    });
    const data = await r.json();
    setTurns((t) => [...t, { id: crypto.randomUUID(), query, response: data, ts: Date.now() }]);
    setLoading(false);
  }

  return (
    <main className="flex h-screen bg-slate-50">
      <Sidebar turns={turns} />
      <section className="flex flex-1 flex-col">
        <header className="border-b bg-white p-4">
          <h1 className="text-lg font-semibold">SCM NL-to-SQL Dashboard</h1>
          <p className="text-xs text-slate-500">claude-haiku-4-5 · session {sessionId.slice(0, 8)}</p>
        </header>
        <MessagePane turns={turns} loading={loading} />
        <ChatInput onSend={handleSend} disabled={loading} />
      </section>
    </main>
  );
}
```

- [ ] **Step 5: Write components**

Write `ChatInput.tsx`, `MessagePane.tsx`, `Sidebar.tsx`, `SqlBlock.tsx`, `ResultTable.tsx` with explicit code (omitted for brevity in plan — see implementation; each is < 80 lines).

- [ ] **Step 6: Update .gitignore**

Append to `.gitignore`:

```
frontend/node_modules/
frontend/.next/
frontend/out/
frontend/build/
```

- [ ] **Step 7: Launch dev server**

```powershell
Set-Location "$ROOT\frontend"
npm run dev
```

Open `http://localhost:3000` in the browser.

- [ ] **Step 8: Smoke-test the loop**

Type "How many products do we have?" into the chat input. Expected: SQL appears, result table shows row count, latency badge appears.

- [ ] **Step 9: Commit**

```bash
git add frontend/ .gitignore
git commit -m "feat(frontend): add Next.js dashboard MVP with multi-turn sidebar"
```

---

## Task 6: PPT refresh with all new numbers + UI screenshot

**Files:**
- Modify: `scripts/generate_midsem_pptx.py` — update result tables, add UI screenshot slide, add LLM-ablation slide
- Reference: `docs/viva/Midsem_Viva_2024AA05175.pptx`

- [ ] **Step 1: Take UI screenshot**

With `npm run dev` running and the FastAPI gateway running, take a screenshot of the dashboard mid-conversation (3 turns visible). Save to `docs/viva/ui_screenshot.png`.

- [ ] **Step 2: Update generate_midsem_pptx.py to pull n=100 numbers + new slides**

Modify the script to:
- Read the n=100 RESULTS.md (instead of the n=50)
- Add a new slide #7: "LLM-Scaling Ablation — L3 advantage GROWS with Sonnet"
- Add a new slide #8: "Live UI Prototype" with the screenshot embedded
- Add a row in the public-benchmark slide for BIRD sanity check

- [ ] **Step 3: Regenerate PPT**

```powershell
$env:PYTHONIOENCODING="utf-8"
& "$ROOT\.venv\Scripts\python.exe" "$ROOT\scripts\generate_midsem_pptx.py"
```

Expected: `Wrote docs\viva\Midsem_Viva_2024AA05175.pptx (XX.X KB, 11 slides)`.

- [ ] **Step 4: Visually inspect the PPT**

Open in PowerPoint or LibreOffice. Confirm: 11 slides, new numbers correct, UI screenshot visible, no broken layouts.

- [ ] **Step 5: Commit**

```bash
git add scripts/generate_midsem_pptx.py docs/viva/Midsem_Viva_2024AA05175.pptx docs/viva/ui_screenshot.png
git commit -m "docs(viva): refresh midsem PPT with n=100 + BIRD + LLM ablation + UI screenshot"
```

---

## Task 7: Backup demo recording (user-led)

**Files:**
- Create: `docs/viva/MIDSEM_DEMO_BACKUP.mp4`
- Reference: `docs/viva/MIDSEM_DEMO_RECORDING.md`

- [ ] **Step 1: User reads recording instructions**

Open `docs/viva/MIDSEM_DEMO_RECORDING.md` and follow the pre-recording checklist.

- [ ] **Step 2: User records the demo**

Single take, 3 minutes. Capture both the terminal demo (`scripts/midsem_demo.py`) AND a brief UI walkthrough (~30 sec at the end).

- [ ] **Step 3: User saves the file**

Save trimmed MP4 to `docs/viva/MIDSEM_DEMO_BACKUP.mp4`. Put a copy on a USB stick.

This task is user-only. Claude cannot record audio/video.

---

## Task 8: Rehearsal (user-led)

- [ ] **Step 1: Day 14 (10 Jun) — first dry-run**

Run the full demo end-to-end in front of a mirror or webcam. Time yourself. Target: under 12 minutes for the full presentation.

- [ ] **Step 2: Day 15 (11 Jun) — second dry-run with mock Q&A**

Have a colleague/friend ask 5 random questions from `VIVA_PREP_OUTLINE.md §12`. Note questions you fumbled.

- [ ] **Step 3: Day 18 (14 Jun) — third dry-run + targeted fixes**

Drill the questions you fumbled on Day 15. Run the demo once more.

This task is user-only.

---

## Self-Review

**Spec coverage check (against `docs/superpowers/specs/2026-05-27-midsem-checkpoint-design.md`):**

| Spec deliverable | Plan task |
|---|---|
| D1 BIRD sanity check | Task 1 |
| D2 SCM-SQL 50 → 100 | Task 2 |
| D3 Re-run + new stats | Task 3 |
| D4 FastAPI gateway | Task 4 |
| D5 Next.js dashboard MVP | Task 5 |
| D6 PPT refresh | Task 6 |
| D7 Backup demo recording | Task 7 |
| D8 Rehearsal | Task 8 |

All 8 deliverables covered.

**Placeholder scan:** Task 5 Step 5 says "see implementation" for component files — this is intentional brevity (each component is well-bounded; the page-level Step 4 shows the contract). I'll write each component explicitly during execution.

**Type consistency:** `AskResponse` shape in Task 4 Step 1 matches the shape consumed by `frontend/app/page.tsx` in Task 5 Step 4. Token-usage fields aligned (`router`, `sql_gen`, `validator`).

---

*Generated 2026-05-27 via /superpowers:writing-plans. Spec source: docs/superpowers/specs/2026-05-27-midsem-checkpoint-design.md.*

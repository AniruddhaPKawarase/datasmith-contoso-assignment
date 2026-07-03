# UI Demo Runbook — Step-by-Step + Expected Outputs

**Audience:** Aniruddha (the person running the demo)
**Demo surface:** Next.js dashboard on `http://localhost:3000` backed by FastAPI gateway on `http://127.0.0.1:8000`
**Total runtime:** ~12–15 min including narration · ~$0.04 LLM spend

Print this page or keep it open on a second monitor on demo day. Read off as you go — don't memorise.

---

## Phase 0 — Pre-demo checklist (5 min before, in private)

### 0.1  Open three windows side-by-side

| Window | Purpose |
|---|---|
| **Terminal 1** | PowerShell at project root — for the gateway |
| **Terminal 2** | PowerShell at `frontend/` — for the Next.js dev server |
| **Browser** | Chrome/Edge, ready to navigate to `http://localhost:3000` |

```powershell
# Both terminals — set the working dir first
cd "C:\Users\ANIRUDDHA ASUS\Downloads\Myself\Mtech-4th-sem-PROJECT\Project_dev"
```

### 0.2  Confirm Docker stack is running

```powershell
docker ps --format "table {{.Names}}\t{{.Status}}" | findstr scm-
```

**Expect 3 containers, all "(healthy)":**

```
scm-postgres   Up XX minutes (healthy)
scm-redis      Up XX minutes (healthy)
scm-odoo       Up XX minutes (healthy)
```

If anything is missing or unhealthy:

```powershell
docker compose -f docker/docker-compose.yml up -d postgres redis odoo
# Wait 30 sec, re-check
```

### 0.3  Confirm the 498-table schema is loaded

```powershell
docker exec scm-postgres psql -U odoo -d odoo -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"
```

**Expect exactly: `498`**

### 0.4  Confirm Anthropic API key works

```powershell
.\.venv\Scripts\python.exe -c "import os; from pathlib import Path; [os.environ.setdefault(k.strip(), v.strip()) for line in Path('.env').read_text(encoding='utf-8').splitlines() if line.strip() and not line.startswith('#') and '=' in line for k, _, v in [line.partition('=')]]; print('KEY_LEN', len(os.environ.get('ANTHROPIC_API_KEY','')))"
```

**Expect: `KEY_LEN 108`** (or any number > 50). If 0, rotate the key in `.env`.

---

## Phase 1 — Start the gateway (Terminal 1, 30 sec)

```powershell
.\.venv\Scripts\python.exe scripts\serve_api.py
```

**Expect within ~10 sec:**

```
INFO:     gateway ready — schema=498 tables
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Leave Terminal 1 running. Don't close it.**

---

## Phase 2 — Start the frontend (Terminal 2, 30 sec)

```powershell
cd frontend
npm run dev
```

**Expect within ~5 sec:**

```
  ▲ Next.js 14.2.18
  - Local:        http://localhost:3000

 ✓ Ready in XXX ms
```

**Leave Terminal 2 running. Don't close it.**

---

## Phase 3 — Open the browser (10 sec)

Navigate to `http://localhost:3000`.

**You should see:**

- Top bar: "SCM NL-to-SQL Dashboard · Domain-Aware Multi-Agent · session XXXXXXXX"
- Green badge top-right: "claude-haiku-4-5"
- Left sidebar: "New session" button, "History" (empty)
- Centre: Welcome card "Ask any supply-chain question"
- 4 sample-query chips above the chat input

---

## Phase 4 — Live demo (the actual show, ~8 min)

### Demo 1 — Cross-domain composition + RBAC (~90 sec)

**Click the chip** or paste this into the chat input:

> `Compare total revenue this quarter with on-hand inventory value, by company.`

Press Enter. While the spinner runs (~5–8 sec), narrate:

> *"This is testing the dissertation's core thesis — domain-axis decomposition. The Router will classify this as cross-domain, picking the Finance agent for revenue and the Inventory agent for on-hand stock. Each generates its own SQL fragment. The Composer wraps them in CTEs and INNER-JOINs on company_id. The Compliance processor injects RBAC predicates inside each CTE. Watch the result panel."*

#### Expected on-screen for D1

| Chip | Value |
|---|---|
| intent | `supply_chain_question` |
| domains | `finance, inventory` |
| latency | ~5,000–8,000 ms |
| cost | `$0.0080`–`$0.0150` |
| rows | `1` |

**SQL block** (the agent generates this live so wording varies; expect this shape):

```sql
WITH q_finance AS (
  SELECT so.company_id,
         SUM(so.amount_total) AS total_revenue
  FROM sale_order so
  WHERE so.state IN ('sale','done')
    AND so.date_order >= date_trunc('quarter', NOW())
    AND so.company_id IN (1)              -- ← Compliance injection
  GROUP BY so.company_id
),
q_inventory AS (
  SELECT sq.company_id,
         SUM(sq.quantity) AS on_hand
  FROM stock_quant sq
  JOIN stock_location l ON l.id = sq.location_id
  WHERE l.usage = 'internal'
    AND sq.company_id IN (1)              -- ← Compliance injection
  GROUP BY sq.company_id
)
SELECT rc.name AS company,
       q_finance.total_revenue,
       q_inventory.on_hand
FROM res_company rc
JOIN q_finance ON q_finance.company_id = rc.id
JOIN q_inventory ON q_inventory.company_id = rc.id;
```

**Green badge:** `✓ EXPLAIN OK`

**Result row** (1 row — Odoo demo data ships with one active company):

| company | total_revenue | on_hand |
|---|---|---|
| My Company (San Francisco) | **31,809.61** | **1,487** (units) or **18,300.00** (USD value) |

**What to point at:**

1. **Single row** — *"Odoo's demo data ships with one company by default."*
2. **`WITH q_finance AS (...), q_inventory AS (...)`** — *"Composer generated CTEs from independent agent outputs."*
3. **`JOIN ... ON company_id`** — *"Composer detected the shared key."*
4. **`company_id IN (1)` inside each CTE** — *"Compliance AST-walked and injected per-CTE, not at the outer level. Regression test pinned at `test_compliance_v2.py::test_predicate_appears_inside_cte_not_outer`."*

---

### Demo 2 — Multi-turn dialogue with referent inheritance (~2 min)

**This is the strongest visual showcase** because the sidebar fills up.

#### Turn 1 — *"Show top customers by revenue this quarter."*

Paste, press Enter, wait. When it returns, narrate while pointing at the sidebar:

> *"Single-turn baseline. Watch the sidebar — turn 1 is now there."*

**Expected on-screen for D2-T1**

| Chip | Value |
|---|---|
| intent | `supply_chain_question` |
| domains | `finance, demand` |
| rows | `3` |

**Result rows:**

| customer | revenue | order_count |
|---|---|---|
| **Gemini Furniture** | **27,557.48** | **17** |
| Joel Willis | 3,389.63 | 1 |
| Lumber Inc | 862.50 | 1 |

> *"Gemini Furniture is the top customer — accounts for ~87 % of this quarter's revenue."*

#### Turn 2 — *"Only the top 5."*

**Important: do NOT click "New session" between turns.**

Paste, press Enter. When it returns:

> *"This fragment would be ambiguous in isolation. But the ReferenceDetector classified it as a refinement and pulled the prior turn's domains (finance, demand) forward. Look at the domains chip — same as turn 1. The Specialists added ORDER BY ... LIMIT 5 to the existing query rather than starting over. Sidebar now has two turns."*

**Expected on-screen for D2-T2**

| Chip | Value |
|---|---|
| domains | `finance, demand` (inherited) |
| rows | `3` (same rows — Odoo demo data only has 3 customers this quarter; `LIMIT 5` doesn't shrink) |

> ⚠️ **Narrate honestly about the row count:** *"The demo dataset has only 3 customers in this quarter, so LIMIT 5 returns the same rows. What you can see is the inherited domain chips — the ReferenceDetector pulled the prior turn's finance + demand assignment forward. In production data with hundreds of customers, the LIMIT would actually clip."*

#### Turn 3 — *"Now compare with last year same period."*

Paste, press Enter. When it returns:

> *"Comparison kind, not refinement. The Temporal Parser produced both the current-quarter range AND the prior-year quarter range. The Specialists emitted dual-period SQL — either a UNION or SUM(CASE WHEN). Sidebar now has three turns, all with the same domain assignment."*

**Expected on-screen for D2-T3**

| Chip | Value |
|---|---|
| domains | `finance, demand` (still inherited) |
| latency | ~6,000–8,000 ms |
| rows | `1` |

**Result row:**

| current_quarter | same_quarter_last_year |
|---|---|
| **31,809.61** | **0** |

> ⚠️ **This is the trickiest one to narrate** because the YoY comparison returns 0 for last year. Odoo's demo data spans only ~1 month (2026-04-09 → 2026-05-14), so there literally is no last-year data. Use this language:
>
> *"Last year is zero — Odoo's demo dataset ships with only the most recent month of sale_orders. The architectural point is what the SQL looks like. Notice the SUM(CASE WHEN date_order >= …) construction. The Temporal Parser produced both ranges — current quarter and prior-year offset — deterministically. In production data the prior-year value would be populated; here the data simply doesn't go back that far."*

> 🔄 **Alternative if Sonnet/Haiku generates a UNION instead of CASE WHEN:** you may get an EXPLAIN FAIL on this turn. If that happens, narrate per the failure script: *"The validator caught a UNION syntax error; the system would retry in production. Demo capped at 2 attempts. The architectural point — that the ReferenceDetector correctly inherited the domain context across three turns — still stands."*

---

### Demo 3 — Ambiguity refusal (the "calibrated honesty" moment, ~45 sec)

**Click "New session"** in the sidebar to clear context.

**Paste:**

> `What is the lead time for our Asian suppliers?`

Press Enter. When it returns:

> *"Watch what doesn't happen — no SQL is generated. The AmbiguityResolver looked up 'lead time' in the business glossary, found three competing senses — procurement, manufacturing, delivery — and refused to guess."*

**Expected on-screen for D3**

| Chip | Value |
|---|---|
| intent | `clarification_needed` |
| domains | `(none)` |
| latency | ~2,000 ms |
| cost | `$0.0008` |
| rows | (no result table — clarification card instead) |

**Amber clarification card:**

> **⚠️ Clarification needed**
>
> By 'lead time', do you mean
> - "procurement (purchase_order)",
> - "manufacturing (mrp_production)",
> - or "delivery (stock_picking)"?
>
> Please clarify so I can route the query to the right specialist.

> **Point at the amber card:** *"This is calibrated honesty. The system tells you what it doesn't know rather than guessing. Most NL-to-SQL systems will silently pick one sense. Ours doesn't. Zero tokens spent on agent SQL generation — the spend is just the ambiguity scorer."*

---

### Demo 4 (optional, ~15 sec) — Out-of-scope refusal

**Paste:**

> `What is the weather in Pune today?`

**Expected on-screen for D4**

| Chip | Value |
|---|---|
| intent | `out_of_scope` |
| domains | `(none)` |
| latency | ~1,500 ms |
| cost | `$0.0003` |

**Grey card:** *"Out of scope — this question doesn't match an SCM domain I can answer."*

> *"The Router has a confidence threshold. Non-SCM questions get rejected early — no SQL agent runs, no tokens wasted."*

---

## Phase 5 — Close the loop on the headline numbers (~2 min)

After Demo 4, open `docs/viva/MENTOR_DEMO_GUIDE.md` in a new browser tab or VS Code:

> *"To summarise — on the same benchmark the MAC-SQL paper reports 59.39 % EX with GPT-4, our re-implementation of MAC-SQL hits 70 % EX and our system hits 68 % EX with Sonnet — both above the paper. On SCM-SQL, the benchmark we built to test our architecture's enterprise differentiators, we beat MAC-SQL by +10 pp on Level 2, +6.7 pp on Level 3, +4.3 pp on Level 6. Two streams of evidence. Two claims. No overreach."*

Open the PPT (`docs/viva/Midsem_Viva_2024AA05175.pptx`) and walk through slides 7–10 (head-to-head, LLM ablation, public benchmarks, BIRD-vs-paper).

---

## Phase 6 — Wind down (10 sec)

When the mentor's done asking questions:

**Don't close the terminals yet** — they may want to see one more thing.

When fully done:
- Terminal 1: `Ctrl+C` to stop the gateway
- Terminal 2: `Ctrl+C` to stop Next.js
- Browser: close tab

---

## ⏱️ Live timing budget

| Demo | Wall-clock | Cost | Says-on-screen |
|---|---|---|---|
| D1 (cross-domain) | ~6 sec | $0.012 | 1 row |
| D2 T1 (top customers) | ~4 sec | $0.008 | 3 rows |
| D2 T2 (top 5) | ~3 sec | $0.005 | 3 rows |
| D2 T3 (YoY) | ~6 sec | $0.010 | 1 row |
| D3 (ambiguity) | ~2 sec | $0.001 | clarification card |
| **Total live demo time** | **~22 sec exec** | **~$0.04** | — |

Including narration and pauses, the whole UI demo is **3–4 minutes**.

---

## 🚨 Failure-mode triage table

| Symptom | Cause | Fix |
|---|---|---|
| `docker ps` shows nothing | Docker Desktop not started | Open Docker Desktop, wait 30 sec, re-run |
| `serve_api.py` errors with `ConnectionRefused` | Postgres container not healthy | `docker compose ... restart postgres`, wait 20 sec |
| `npm run dev` fails | `node_modules` missing | `npm install` in `frontend/`, wait 2 min |
| Browser shows "fetch upstream-failed" | Gateway not running on port 8000 | Check Terminal 1; restart `serve_api.py` |
| LLM call returns 401 Unauthorized | Anthropic key expired | Rotate key in `.env`, restart gateway |
| EXPLAIN FAIL on D2 T3 (YoY) | Known intermittent (UNION on YoY) | Say "the validator would re-route this in production; demo capped at attempts=2" and move on |
| Mentor asks for a query I can't predict | Calmly accept | Type it in. If it works → great. If it errors → narrate honestly: *"That's a fair stress test. The system handles X categories of question well; this falls outside the demonstrated set."* |
| Small row counts feel unimpressive | Demo dataset is single-tenant Odoo default | *"Odoo demo data ships single-tenant; the architecture is what's demonstrated, not data volume."* |

---

## 🎯 Narration golden rules

| Situation | What to say |
|---|---|
| Small row counts | *"Odoo demo data ships with X — the architecture is what's being demonstrated, not the data volume"* |
| YoY = 0 | *"Odoo demo data spans 1 month; the temporal mechanism works, the data doesn't go back"* |
| EXPLAIN FAIL on T3 | *"Validator caught it; production retries; demo capped at 2 attempts"* |
| Panel pushes on absolute numbers | Pivot to: *"On SCM-SQL n=113 we have +10 pp L2 lift; on BIRD with Sonnet we hit 68/70 % vs paper's 59 %"* |

---

## 📋 The 30-second elevator pitch (rehearse this 3× before demo day)

> *"This dissertation is a domain-axis multi-agent NL-to-SQL system for enterprise supply chain workloads. Five domain agents — Inventory, Logistics, Finance, Demand, Compliance — coordinate through a LangGraph orchestrator with an AST-based Composer for cross-domain CTE federation and an AST-based Compliance layer for per-CTE RBAC injection. On our SCM-SQL benchmark — which we built because Spider and BIRD don't test multi-turn, RBAC, or cross-domain — we beat MAC-SQL by **+10 pp on Level 2** single-domain queries, with the lift identical across n=56 and n=113. On BIRD dev with Sonnet-4, both our re-implementation of MAC-SQL and our own system clear the **published GPT-4 baseline (59.39 %)** at 70 % and 68 % respectively. Live demo runs in three minutes."*

Memorise the bolded numbers — **+10 pp L2 · 68 / 70 % on BIRD · 59.39 % paper baseline** — those three numbers anchor everything.

---

## 📌 Tabs to keep open during the demo

| Tab | URL or path | Why |
|---|---|---|
| 1 | `http://localhost:3000` | The live UI (main demo surface) |
| 2 | `docs/viva/MENTOR_DEMO_GUIDE.md` | Single-source-of-truth for all panel concerns |
| 3 | `docs/viva/Midsem_Viva_2024AA05175.pptx` | Slide 10 = the BIRD-beats-paper headline |
| 4 | `benchmark/scm_sql_pilot/ANALYSIS.md` | §1.8 has the full BIRD writeup if they push |
| 5 | `http://127.0.0.1:8000/docs` | FastAPI Swagger UI — handy if they ask "show me the API" |

---

*Document version 1.0  ·  Generated 2026-06-11  ·  Author: Aniruddha Prakash Kawarase*

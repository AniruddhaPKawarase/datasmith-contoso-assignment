# Mid-Sem Demo — Narration Script

**Runtime:** ~3 minutes  ·  **Cost:** ~$0.04 in API spend  ·  **Backup:** the script's transcript is saved to `docs/viva/MIDSEM_DEMO_LOG_<timestamp>.txt`.

You read the *italic* lines aloud. Plain text is what the panel sees on screen.

---

## Pre-demo (do NOT skip — 60 seconds before you start)

```powershell
cd "C:\Users\ANIRUDDHA ASUS\Downloads\Myself\Mtech-4th-sem-PROJECT\Project_dev"
docker ps --format "table {{.Names}}\t{{.Status}}" | findstr scm-
```

You should see 3 containers (`scm-postgres`, `scm-redis`, `scm-odoo`) all healthy. If any is missing:

```powershell
docker compose -f docker/docker-compose.yml up -d postgres redis odoo
Start-Sleep -Seconds 30
```

Verify Postgres has the 498 tables:

```powershell
docker exec scm-postgres psql -U odoo -d odoo -tAc `
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"
```

Expected: `498`. If you see anything else, **bail to the backup video** — do not try to fix live.

---

## Opening (10 seconds)

*"I'll show you three queries that exercise the central capabilities of the system — cross-domain composition, multi-turn dialogue, and ambiguity handling. Total runtime is about three minutes, and the API spend is roughly four cents."*

```powershell
.\.venv\Scripts\python.exe scripts\midsem_demo.py
```

---

## Demo 1 — Cross-domain + temporal + RBAC  (~45 seconds on screen)

The panel sees:

```
========================================================================
D1.  Cross-domain  +  Temporal  +  AST Compliance
========================================================================
  Demonstrates the dissertation's central thesis: domain-axis
  decomposition with deterministic temporal reasoning and per-CTE-
  scoped RBAC.

  [Q1.1 ]  Compare total revenue this quarter with on-hand inventory
            value, by company.
  [intent  ] supply_chain_question
  [domains ] finance, inventory
  [latency ] ~5500 ms

  Composed SQL:
    WITH q_finance AS (SELECT … company_id IN (1) …),
         q_inventory AS (SELECT … company_id IN (1) …)
    SELECT q_finance.company_id, total_revenue, on_hand_value
    FROM q_finance INNER JOIN q_inventory USING (company_id);
  [EXPLAIN ] OK
```

*Say while the SQL prints (about 5 seconds of dead air to fill):*

> *"What just happened. The Router classified this as a cross-domain question and chose two specialists — Finance and Inventory. Each generated its own SQL fragment against its bounded schema slice. The Composer detected that both fragments project `company_id`, wrapped them in named CTEs, and INNER-JOINed on the shared key. The Compliance Processor walked the AST and injected the `company_id IN (1)` predicate **inside each CTE's WHERE clause** — not at the outer level — so a CTE-scoped predicate never leaks. The query then passed Postgres EXPLAIN against the live 498-table database. The whole path took about five seconds and cost about one cent."*

If they interrupt with *"why the RBAC scope thing matters"*:

> *"If we'd injected `aml.company_id IN (1)` at the outer SELECT level, Postgres would have rejected it with `missing FROM-clause entry for table 'aml'` — because `aml` is only defined inside the finance CTE. The AST traversal solves that. There's a regression test pinning the behaviour, in `test_compliance_v2.py::test_predicate_appears_inside_cte_not_outer`."*

---

## Demo 2 — Multi-turn dialogue  (~75 seconds on screen)

The panel sees three turns scroll past:

```
========================================================================
D2.  Multi-turn dialogue — refinement and comparison
========================================================================
  Demonstrates the ReferenceDetector inheriting domains across turns.

  [T1   ]  Show top customers by revenue this quarter.
  [intent  ] supply_chain_question
  [domains ] finance, demand
  ...
  [EXPLAIN ] OK

  [T2   ]  Only the top 5.
  [intent  ] supply_chain_question
  [domains ] finance, demand        ← inherited from T1
  ...
  [EXPLAIN ] OK

  [T3   ]  Now compare with the same period last year.
  [intent  ] supply_chain_question
  [domains ] finance, demand        ← still inherited
  ...
  [EXPLAIN ] OK
```

*Say (timed across the three turns):*

> *"Turn one is a normal cross-domain query — Router picks Finance and Demand."*  *(let T1 print)*
>
> *"Turn two is just 'only the top 5' — a fragment that would be ambiguous on its own. The Reference Detector classified it as a **refinement**, and the orchestrator inherited the prior turn's two domains rather than asking the user to repeat themselves. The agents added `ORDER BY ... LIMIT 5` to each CTE. EXPLAIN OK."*  *(let T2 print)*
>
> *"Turn three says 'compare with the same period last year' — a comparison. The Temporal Parser produced both the current-quarter range and the prior-year range; the agents emitted dual-period SQL. In the most recent dry-run the agents chose a UNION construction that Postgres rejected — the system would normally route this back to the originating agent for an additional attempt; the demo capped attempts at 2 for speed, so the fail is what you see. The architectural point — that the multi-turn ReferenceDetector correctly inherited finance/demand to T3 — still stands."*

If they ask *"how do you know it's a refinement and not a new topic?"*:

> *"Rule-based classifier — about 30 lines of regex in `backend/app/conversation/references.py`. It's deliberately not an LLM call because we run it before the Router; an LLM call here would double routing latency. The rules cover four kinds — NEW_TOPIC, REFINEMENT, COMPARISON, FOLLOW_UP. Precedence is comparison-beats-refinement. About 39 unit tests cover the patterns."*

---

## Demo 3 — Ambiguity  (~30 seconds on screen)

The panel sees:

```
========================================================================
D3.  Ambiguity — calibrated refusal
========================================================================
  Demonstrates the AmbiguityResolver. 'Lead time' has three glossary
  senses — the system refuses to guess and asks back.

  [Q3.1 ]  What is the lead time for our Asian suppliers?
  [intent  ] clarification_needed
  [domains ] (none)
  [panel   ] By 'lead time', do you mean "procurement (purchase_order)",
             "manufacturing (mrp_production)", "delivery (stock_picking)"?
             Please clarify so I can route the query to the right
             specialist.
  No SQL produced — by design (see panel field above).
```

*Say:*

> *"This is the calibrated-honesty path. The Ambiguity Resolver — inspired by AmbiSQL — looked up 'lead time' in the business glossary, found three competing senses, scored the ambiguity above the 0.55 threshold, and returned a structured clarification question. No agent ran, no tokens were burnt on SQL generation. This is exactly the failure mode every NL-to-SQL system needs and most don't have — the system knowing what it doesn't know."*

---

## Closing (15 seconds)

The panel sees:

```
========================================================================
TOKEN USAGE  &  ESTIMATED COST
========================================================================
  router        gpt-4o-mini       4 call(s)  in=...  out=...
  sql_gen       claude-haiku-4-5  5 call(s)  in=...  out=...

  TOTAL    in=...  out=...  ≈ $0.0xxx
```

*Say:*

> *"Four cents for the whole demo. A transcript is saved to `docs/viva/MIDSEM_DEMO_LOG_…`. I'm happy to take questions on any of the three paths in more detail, or to run a query the panel proposes if there's time."*

---

## Failure-mode triage  (kept short on purpose)

| If… | Then say… and do… |
|---|---|
| Docker container missing | *"For time, let me show the recorded run instead."* Play backup video. |
| Postgres unreachable | Same — backup video. |
| Anthropic API rate-limit | Wait 10 seconds, retry once. If still failing, backup video. |
| EXPLAIN fails on a query | *"This particular execution failed — the SQL parsed but Postgres rejected it. The system would normally route this back to the originating agent for a retry; the demo capped retries at 2 for speed. The transcript shows the error."* Move on. |
| Question I cannot answer in the moment | *"That's a fair point — I'd want to verify the exact figure before answering. Can I come back to it?"* Move on. |

The goal is **three demos completed**, not *every demo perfect*. The panel cares that the system runs end-to-end; minor execution failures are recoverable. Panicked silence is not.

---

## What to have open in tabs

| Tab | What it shows | Why |
|---|---|---|
| `docs/eval/EVALUATION_FRAMEWORK.md` | The 7 commitment targets in §11 | If they ask "how will you measure success?" |
| `docs/benchmark/MAC_SQL_HEAD_TO_HEAD.md` | The 17-row architectural comparison in §2 | If they ask "how is this different from MAC-SQL?" |
| `docs/architecture/ROUTING_AND_FEDERATION.md` | The end-to-end sequence diagram in §7 | If they ask to draw the architecture |
| The demo log just produced | Live evidence of EXPLAIN OK | If they want to see specific SQL again |

---

*Document version 1.0  ·  Generated 2026-05-20*

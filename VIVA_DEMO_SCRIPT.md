# LIVE DEMO SCRIPT — Outline Viva, 2026-05-26

> **Purpose:** if the panel asks *"show me the system"*, this is the 90-second demo you run. It demonstrates 5 of the 6 dissertation objectives in one shot. Every command is copy-paste-ready.

> **Backup plan:** record yourself doing this on Day 4 of prep. If anything fails live, play the video.

---

## Pre-flight checklist (the morning of the viva)

```powershell
# 1. Confirm Docker stack is up
docker ps --format "table {{.Names}}\t{{.Status}}" | findstr scm-

# Expected: 3 containers — scm-postgres (healthy), scm-redis (healthy), scm-odoo (Up)
# If any is missing:
docker compose -f docker/docker-compose.yml up -d postgres redis odoo
# Wait 30 s for Odoo to start.

# 2. Confirm Postgres has the 498 tables
docker exec scm-postgres psql -U odoo -d odoo -tAc `
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"

# Expected: 498

# 3. Confirm OpenAI + Anthropic keys are reachable
.\.venv\Scripts\python.exe scripts\smoke_llm.py | findstr "OK"
```

If all three checks pass, you're ready. If any fails, see §[Failure modes](#failure-modes) below.

---

## The 90-second demo (the version you actually run live)

### Opening line (you say, panel listens)

> "Let me show you what the system does end-to-end. I'll run a 3-turn dialogue against the live Odoo database. It exercises five of the six dissertation objectives in under two minutes."

### Run the command

```powershell
cd "C:\Users\ANIRUDDHA ASUS\Downloads\Myself\Mtech-4th-sem-PROJECT\Project_dev"
.\.venv\Scripts\python.exe scripts\smoke_phase7.py
```

### What you narrate while it runs

The script prints three turns sequentially. For each turn, **pause for the panel to read** and say one sentence.

**Turn 1** — *"Show me total revenue by customer this quarter."*
> "Turn one. New topic. The Router picks two domains — finance and demand — and the temporal parser converts 'this quarter' to the exact ISO date range. The Composer builds two CTEs and CROSS-JOINs them because they don't share a join key in their output. The Compliance layer injects `company_id IN (1)` predicates **inside each CTE's WHERE clause** — not at the outer level. The result passes Postgres EXPLAIN against the live 498-table Odoo database."

**Turn 2** — *"Only the top 5."*
> "Turn two — a refinement. The ReferenceDetector classifies this as REFINEMENT. The orchestrator inherits the prior turn's two domains rather than asking the user to clarify a self-evident follow-up. Each CTE now ends with `ORDER BY ... LIMIT 5`. Same EXPLAIN result — clean."

**Turn 3** — *"Now compare with the same period last year."*
> "Turn three — a comparison. The temporal parser produces TWO date ranges — the current period and the prior-year window. The agents combine them into `SUM(CASE WHEN ... 2026 ... ELSE 0 END) AS current, SUM(CASE WHEN ... 2025 ... ELSE 0 END) AS prior`. This is the YoY pattern the VLDB 2025 NL2SQL survey lists as an open problem. EXPLAIN OK."

### Closing line

> "Total token cost for that 3-turn dialogue: about four cents. The Phase 10 evaluation will exercise this same pipeline across the 500+ SCM-SQL queries I'm building for the benchmark."

---

## Failure modes (in priority order — bail to whichever step succeeds)

### A. Docker is down / Postgres won't connect
```powershell
# Try to restart everything in 30 seconds
docker compose -f docker/docker-compose.yml restart postgres redis odoo
# wait
Start-Sleep -Seconds 20
# retry
docker exec scm-postgres pg_isready -U odoo
```
**If that fails:** play your backup video. **Do not panic-explain.** "Let me show you the recorded run from yesterday" is a confident move, not a weak one.

### B. OpenAI or Anthropic API is rate-limited
The script will fall back to the configured fallback model (`openai/gpt-4o-mini`). If that also fails:
**Bail to the video.**

### C. The script hangs on a specific turn
Ctrl-C, then run **only** the YoY query (Turn 3) — it's the most impressive single-turn output:
```powershell
.\.venv\Scripts\python.exe -c @"
import asyncio, sys
sys.path.insert(0, 'backend')
# minimal harness ...
"@
```
**Practical alternative:** show the saved log file from Phase 7 testing instead:
```powershell
Get-Content scripts\last_phase7_run.log | Select-Object -First 50
```
(Save the log file during Day 4 prep so it exists on viva day.)

### D. Everything is broken and you cannot recover
**The 30-second sentence that saves you:** *"For time, let me skip the live demo and walk you through the architecture on the whiteboard."*  Then deliver the [VIVA_WHITEBOARD.md](VIVA_WHITEBOARD.md) §1 diagram. **The viva is not about live demos — it's about command of the work.** A broken Docker doesn't lose marks; a flustered student does.

---

## The 30-second condensed demo (if the panel says "just one query, briefly")

```powershell
.\.venv\Scripts\python.exe -c @"
import asyncio
asyncio.run(__import__('scripts.smoke_phase7', fromlist=['main']).main())
"@
```

…or paste the YoY SQL output directly from your saved Day-4 log. The agents produce a query along the lines of:

```sql
WITH q_finance AS (
  SELECT rp.name AS customer,
         SUM(CASE WHEN am.date >= DATE '2026-01-01' AND am.date < DATE '2027-01-01'
              THEN aml.credit - aml.debit ELSE 0 END) AS revenue_current,
         SUM(CASE WHEN am.date >= DATE '2025-01-01' AND am.date < DATE '2026-01-01'
              THEN aml.credit - aml.debit ELSE 0 END) AS revenue_prior
  FROM account_move_line aml
  JOIN account_account aa ON aa.id = aml.account_id
  JOIN account_move am ON am.id = aml.move_id
  JOIN res_partner rp ON rp.id = am.partner_id
  WHERE aa.account_type = 'income'
    AND am.state = 'posted'
    AND aml.company_id IN (1)   -- Compliance, scoped inside the CTE
    AND aa.company_id IN (1)
    AND am.company_id IN (1)
  GROUP BY rp.name
  ORDER BY revenue_current DESC
  LIMIT 5
)
SELECT * FROM q_finance;
```

Three things to point out:
1. The deterministic ISO date predicates (the temporal module).
2. `company_id IN (1)` injected at the right scope (the AST-based Compliance).
3. It's PostgreSQL that runs against Odoo unchanged — *EXPLAIN OK*.

---

## What you should NOT do during the demo

- **Don't apologise** for the SQL being LLM-generated. It's PEER to SOTA work; act like it.
- **Don't read the SQL line-by-line.** The panel can read.
- **Don't try to explain the LangGraph state machine** unless they ask. It's slow content.
- **Don't say "I think"** when you can say "I verified". You have unit tests. You have EXPLAIN OK. You have measured cost. Use the language of evidence.

---

## What you SHOULD do

- **Stand or sit upright.** You're presenting work, not begging for permission.
- **Use the words "deterministic," "AST-based," "scope-correct," "EXPLAIN OK."** Each of those is doing real work in your defence.
- **Cite the paper for any specific number.** "Spider 2.0 → 10.1 % per Lei et al., ICLR 2025 Oral." That precision distinguishes you from the candidate who just memorised numbers.
- **When the panel pushes, slow down.** A two-second pause before answering is much better than a fast wrong answer.

---

*Save your backup video on Day 4 of the 12-day prep plan. That's your insurance policy.*

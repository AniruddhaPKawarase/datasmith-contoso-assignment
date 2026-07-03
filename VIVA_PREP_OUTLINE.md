# OUTLINE VIVA PREPARATION
## Domain-Aware Multi-Agent NL-to-SQL for Enterprise Supply Chain Intelligence

**Student:** Aniruddha Prakash Kawarase  |  **BITS ID:** 2024AA05175
**Programme:** M.Tech AI & ML (WILP), BITS Pilani
**Course:** AIMLCZG628T — Dissertation
**Project carried out at:** Alta Futuris Solutions, Pune
**Viva date:** 26 May 2026   |  **Mid-sem report:** 16 Jun 2026   |  **Final report:** 28 Jul – 2 Aug 2026

> **Implementation status as of 2026-05-14:** Phases 1-7 of 10 complete. **Working live system** producing validated PostgreSQL against a 498-table Odoo schema, with multi-turn dialogue, deterministic temporal reasoning, AST-based RBAC, ambiguity resolution, and a 3-stage SQL validator. **210 unit tests at 87 % coverage. Total LLM spend so far: ~$0.10.**

> **How to use this document:** Read top-to-bottom once. Then drill into Section 12 (Q&A) until you can answer every question in under 60 seconds without looking. The viva panel will spend ~70 % of their time on the *problem framing* and *novelty* — the architecture comes second. **For the 12-day prep schedule, see [VIVA_PREP_12_DAY_PLAN.md](VIVA_PREP_12_DAY_PLAN.md).**

---

## 1. THE 30-SECOND ELEVATOR PITCH (memorise verbatim)

> "On a real enterprise schema like Odoo's ~500-table ERP, the best public NL-to-SQL systems answer barely 10 % of questions correctly. My dissertation closes that gap for supply-chain workloads. Instead of decomposing by SQL pipeline stage like MAC-SQL or MARS-SQL, I decompose by **business domain** — five specialist agents (Inventory, Logistics, Finance, Demand, Compliance) each owning a slice of the schema, a Composer that stitches their sub-queries into CTEs, and an AST-based Compliance layer that injects row-level security at the right scope. I already have a working pipeline that takes a natural-language question, parses temporal expressions deterministically, generates valid PostgreSQL against a live 498-table Odoo database, and validates it through a sqlglot syntax + execution + business-rule pipeline. The contribution I'll defend includes a new benchmark — **SCM-SQL**, 500+ NL/SQL pairs across six complexity levels — and a published evaluation showing domain-axis decomposition beats pipeline-axis decomposition on enterprise schemas."

**Status note for the panel:** mention casually that "Phases 1–7 of the 10-phase plan are already running live, ~4–5 weeks ahead of the roadmap." This signals delivery confidence without bragging.

---

## 2. THE ONE-MINUTE WHITEBOARD ANSWER

When asked *"explain your project in 60 seconds"*, draw five horizontal bands and speak through them:

```
USER QUERY  ────────────────────────────────────────────────
   ▼
[1] Understanding   →  Intent classifier · Ambiguity detector · Temporal parser
   ▼
[2] Domain Agents   →  Inventory · Logistics · Finance · Demand · Compliance
   ▼
[3] Composition     →  Composer merges via CTEs · Federation across PG/DuckDB/Redis
   ▼
[4] Validation      →  Syntax → Execution → Business-rule → Self-correct (max 3)
   ▼
[5] Response        →  SQL + result + lineage + confidence + audit log
```

Three things you *must* mention:
1. **Domain-aware decomposition** (the novelty)
2. **Cross-database federation** (the engineering depth)
3. **SCM-SQL benchmark** (the publishable artefact)

---

## 3. WHY THIS PROBLEM (Background — 2-minute version)

| Hard fact | Source |
|---|---|
| GPT-4o scores **10.1%** on Spider 2.0 enterprise workflows | Lei et al., ICLR 2025 (Oral) — arXiv 2411.07763 |
| Strongest methods reach only **~39.1%** on BIRD-Ent (4,000+ columns) | OpenReview 2025 |
| **Odoo** alone exposes ~600 PostgreSQL tables | odoo.com |
| Microsoft Research argues NL2SQL is **NOT solved** for enterprise | Floratou et al., CIDR 2024 |
| Multi-agent LLMs are emerging as the right shape for SCM decisions | Klabe et al., Int. J. Production Research 2025 |

**Why supply chain specifically?**
A single executive question — *"compare supplier lead times against defect rates for our Asian vendors in Q1"* — needs **fiscal-calendar arithmetic + 5–10 table joins + cross-domain reasoning** (procurement + quality + partner). Today's systems collapse on this. Walmart, SAP, Microsoft and Google are already piloting agent platforms here — the market is real and the gap is concrete.

---

## 4. THE RESEARCH GAP (the slide examiners will linger on)

| What exists | What's missing — my contribution |
|---|---|
| MAC-SQL / MARS-SQL / SQL-of-Thought / CHASE-SQL decompose by **SQL pipeline stage** (link → generate → validate → refine) | Decomposition by **business domain** is unexplored |
| Spider / BIRD evaluate on **single databases** | Real SCM queries span **multiple heterogeneous DBs** |
| AmbiSQL / Odin handle ambiguity for **single-turn questions** | Supply-chain-specific ambiguity (e.g. "lead time" has 3 meanings) is unaddressed |
| Temporal reasoning is an **open problem** (VLDB 2025 survey) | SCM queries are inherently temporal — no benchmark targets this |
| Spider 2.0 / BIRD-Ent are general enterprise | **No NL-to-SQL benchmark targets supply chain** |

---

## 5. THE 6 OBJECTIVES (memorise the numbering)

1. **Domain-Aware Agent Decomposition** — five specialists split by business domain, not SQL stage.
2. **Cross-Database Composition & Federation** — Composer dispatches sub-queries, merges via CTEs across PostgreSQL/DuckDB/Redis with currency conversion and dialect translation.
3. **Temporal Reasoning Module** — *deterministic, not a prompt trick* — maps "last quarter", "YoY", "rolling 30-day", "fiscal Q3" to exact SQL window functions.
4. **Self-Correction with RL** — MARS-SQL-style execution-feedback rewards + CHASE-SQL-style candidate selection; max 3 attempts before escalation.
5. **SCM-SQL Benchmark** — 500+ NL/SQL pairs, six complexity levels, grounded in Odoo schema and DataCo dataset (180K+ orders).
6. **Evaluation** — vs single-agent baselines and vs MAC-SQL / MARS-SQL / CHASE-SQL on Spider, BIRD, and SCM-SQL, with ablations per component.

---

## 6. SCOPE — THE 8 COMPLEXITY DIMENSIONS

1. ~600-table schema (Odoo ERP on PostgreSQL)
2. Federation across PostgreSQL + DuckDB + Redis
3. Temporal reasoning (fiscal calendars, rolling windows, YoY)
4. Hierarchical aggregation (Company → Region → Country → Warehouse → Zone)
5. Cross-domain joins (5–10 tables per query)
6. Interactive ambiguity resolution
7. Row-level access control + audit logging
8. RL self-correction with 3-attempt budget

## 7. THE 5 DOMAIN AGENTS (know what each owns)

| Agent | Owns | Example tables |
|---|---|---|
| **Inventory** | Stock movement, quants, warehouses, locations | `stock_move`, `stock_quant`, `stock_warehouse`, `stock_location`, `product_product` |
| **Logistics** | Pickings, carriers, customs, tracking | `stock_picking`, `delivery_carrier`, `purchase_order`, `res_partner` |
| **Finance** | Account moves, currency, tax, cost centres | `account_move`, `account_move_line`, `res_currency_rate`, `account_tax` |
| **Demand** | Sale orders, forecasts, reorder policies, pricelists | `sale_order`, `sale_order_line`, `stock_warehouse_orderpoint`, `product_pricelist` |
| **Compliance** | Cross-cutting: RBAC, audit logs | `res_users`, `res_groups`, `ir_rule`, `ir_model_access` |

## 8. THE 6 QUERY LEVELS (be ready to give one example per level)

| Lvl | Description | Example | Tables |
|---|---|---|---|
| 1 | Single domain, single table | *"How many units of Product X are in stock?"* | 1–2 |
| 2 | Single domain, multi-table | *"Which warehouses have stock below safety stock?"* | 3–4 |
| 3 | Cross-domain + temporal | *"Compare supplier lead times vs defect rates for Asian vendors in Q1 2026"* | 5–7 |
| 4 | Cross-DB federation | *"Total landed cost for Product X across markets incl. customs, shipping, FX"* | 7–10 / 2 DBs |
| 5 | Predictive / strategic | *"If Supplier X has a 2-week disruption, which products are at risk and revenue impact?"* | 10+ |
| 6 | Multi-turn conversational | *"Show inventory turnover by warehouse last quarter"* → *"Compare with last year"* → *"Which declined most?"* | varies |

---

## 9. ARCHITECTURE — 5 LAYERS (one sentence each)

1. **Query Understanding** — intent classification, ambiguity detection (AmbiSQL-inspired), temporal parsing.
2. **Domain Agents** — five LangGraph-orchestrated specialists, each with private schema slice + glossary + few-shot bank + CSR-RAG schema retrieval.
3. **Composition & Federation** — Composer merges sub-queries via CTEs; federation engine routes per-DB execution and merges results in Python.
4. **Validation & Self-Correction** — 3-stage validator (syntax → execution → business-rule); errors backpropagate to the agent that wrote the broken fragment; max 3 attempts.
5. **Response & Explanation** — SQL + results + NL explanation + confidence + data lineage + audit trail.

---

## 10. TECH STACK (know each choice's *why*)

| Layer | Choice | Why this and not the alternative |
|---|---|---|
| Orchestration | **LangGraph** | State-machine semantics, better than CrewAI for deterministic agent flow + error routing |
| Primary LLM | **OpenRouter** free tier (Qwen 2.5-Coder, DeepSeek-Coder, Llama 3.3) | Open-weights only; no paid API lock-in; Qwen 2.5-Coder hits 82% on Spider |
| Fallback LLM | **Ollama** (local) | Offline reproducibility; demo runs on a laptop |
| Primary DB | **PostgreSQL + Odoo demo data** | Real 600-table enterprise schema, open source |
| Analytics DB | **DuckDB** | Columnar, in-process, no extra container; ideal for federation experiments |
| Cache DB | **Redis** | Realistic live-inventory layer |
| Backend | **FastAPI** | Async, typed, fits ML workloads |
| Frontend | **Next.js 14 + Shadcn/ui + TailwindCSS** | Production-grade; demonstrates production polish for the dissertation |
| Tracking | **MLflow + DeepEval** | Experiment + LLM-eval reproducibility |
| Deploy | **Docker Compose** | One `docker compose up` on examiner's laptop |

---

## 11. PLAN OF WORK — 10 PHASES, 17 WEEKS

| # | Phase | Deadline | Status |
|---|---|---|---|
| 1 | Project setup & infra (monorepo + Docker Compose + LLM abstraction) | 13 Apr | Not started |
| 2 | Database layer & schema intelligence (Odoo introspection, domain mapping, DuckDB, Redis) | 24 Apr | Not started |
| 3 | Core agent framework (LangGraph, Router, conversation memory) | 5 May | Not started |
| 4 | Five domain-specialist agents + CSR-RAG schema retrieval | 19 May | Not started |
| 5 | **MIDTERM** — Composer + federation + self-correction loop | 2 Jun | Not started |
| 6 | Temporal reasoning + ambiguity resolution + hierarchical aggregation | 13 Jun | Not started |
| 7 | Multi-turn conversational engine | 24 Jun | Not started |
| 8 | SCM-SQL benchmark — 500+ queries, 6 levels | 5 Jul | Not started |
| 9 | Next.js + Shadcn/ui frontend | 16 Jul | Not started |
| 10 | **FINAL** — full evaluation, ablations, paper draft, dissertation, demo | 1 Aug | Not started |

> **Viva framing for the timeline:** Outline-viva panel asks *"is the schedule realistic?"* — answer with the *midterm checkpoint at Phase 5* (full end-to-end pipeline, even if narrow) which de-risks the back half.

---

## 12. ANTICIPATED VIVA QUESTIONS — DRILL THESE

### A. Problem & Motivation

**Q1. Why is NL-to-SQL hard at enterprise scale?**
*Three reasons:* (1) schema complexity — 600+ tables exceed any prompt window; (2) ambiguous business vocabulary — "cost", "sales", "lead time" each have multiple table-level meanings; (3) cross-database federation — a single business question spans transactional, analytical and real-time stores. Spider 2.0 scores GPT-4o at 10.1% — that single number anchors the gap.

**Q2. Why supply chain and not finance / healthcare / retail?**
Supply chain combines all the hard primitives in one domain: deep temporal reasoning (fiscal calendars, rolling windows), hierarchical aggregation (warehouse → country → company), multi-currency, and 5–10-table joins per KPI. Healthcare has EHRSQL but the schema is narrower; finance benchmarks exist but lack the cross-domain pressure. SCM has *no* dedicated benchmark today.

**Q3. Why not just fine-tune a single big SQL model?**
SQLCoder-70B hits 93% on Spider but collapses on BIRD-Ent (39.1%). Fine-tuning a single model on enterprise schemas means re-training every time the schema changes. Multi-agent decomposition lets each agent stay small, fast, and *swappable*. It is also publishable — single-model fine-tuning isn't novel anymore.

### B. Novelty & Differentiation

**Q4. How is this different from MAC-SQL or MARS-SQL?**
Both decompose by SQL pipeline stage (Selector → Decomposer → Refiner, or Grounding → Generation → Validation). Mine decomposes by **business domain** — Inventory vs Finance vs Logistics. The two axes are orthogonal: I could combine them, but the domain split is the unexplored one and the one that maps cleanly to a 600-table enterprise schema.

**Q5. Isn't this just routing? What is the research contribution?**
Routing is the *mechanism*. The contribution is (1) showing that domain-aware decomposition outperforms pipeline-stage decomposition on enterprise schemas, (2) a Composer that merges sub-queries across heterogeneous DBs with auto FX conversion, (3) the SCM-SQL benchmark, and (4) the error-backpropagation loop where execution failures route to the *originating agent* rather than a global retry. None of those four exist in published work today.

**Q6. Why decompose by domain — won't an agent miss a cross-domain join?**
That's exactly what the Composer is for. Each domain agent generates its slice of SQL with placeholder join keys; the Composer resolves cross-domain joins (e.g. `product_id` links Inventory ↔ Finance) and merges via CTEs. The Router decides *which* agents to invoke per query — for genuinely cross-domain questions it invokes multiple agents in parallel.

### C. Architecture & Implementation

**Q7. Why LangGraph and not CrewAI or AutoGen?**
LangGraph gives explicit state-machine semantics: I need conditional edges for self-correction (validator → back to source agent, max 3 loops) and deterministic flow control. CrewAI is role-based and less suited to error-routing. AutoGen is conversational and harder to reason about for evaluation.

**Q8. Why three databases — isn't that over-engineering?**
Real SCM data lives in three places: transactional (ERP → PostgreSQL), analytical history (warehouse → DuckDB), and live state (cache → Redis). A landed-cost query for Product X needs current price (PG) + historical FX rate (DuckDB) + on-hand stock (Redis). Federation is the realistic challenge — single-DB is the toy version.

**Q9. How do you handle the 600-table prompt-window problem?**
**CSR-RAG schema retrieval** (Jan 2026, arXiv 2601.06564): contextual retrieval matches NL terms to table descriptions, structural retrieval follows FK relationships, relational retrieval finds join paths. Each agent prompt stays under 4,000 tokens — only the relevant schema slice goes in.

**Q10. What is your self-correction loop, exactly?**
Three-stage validator: (1) syntax — parse SQL AST; (2) execution — run on DB, catch errors, 30s timeout; (3) business-rule — row-count and value-range sanity checks. On failure, the validator returns `{error_type, location, suggestion}` and the orchestrator re-prompts the **agent that produced the broken fragment** (not a global retry). Max 3 attempts. Successful corrections are added to that agent's few-shot bank for online learning.

### D. Evaluation & Benchmark

**Q11. How will you evaluate?**
Three benchmarks: **Spider** (sanity check), **BIRD** (cross-domain), **SCM-SQL** (mine). Metrics: Execution Accuracy (EX), Valid Efficiency Score (VES), Exact Match (EM). Baselines: zero-shot Qwen 2.5-Coder, SQLCoder, MAC-SQL, MARS-SQL, CHASE-SQL. Ablations: ±domain decomposition, ±self-correction, ±CSR-RAG, ±temporal module, ±ambiguity resolution.

**Q12. How will you build SCM-SQL — won't 500 hand-written queries take forever?**
Three-pass pipeline: (1) LLM-assisted NL/SQL generation seeded from real Odoo + DataCo data; (2) human verification — execute every gold SQL and check non-empty correct result; (3) difficulty calibration — measure baseline-model accuracy per query to label level 1–6. Six levels × ~85 queries = 510. About 4 weeks (Phase 8).

**Q13. What's your target accuracy?**
On Spider — match SOTA (~85% EX) to prove I haven't regressed. On BIRD — within 5pp of CHASE-SQL. On SCM-SQL — show my system beats MAC-SQL and MARS-SQL by ≥10pp at Levels 3–6, where domain decomposition should pay off most. Levels 1–2 should be a tie (no decomposition benefit on simple queries).

### E. Risks, Limits, Scope

**Q14. What's out of scope?**
(1) Cloud production deployment, (2) paid model APIs (OpenAI, Anthropic, Google), (3) proprietary connectors (SAP HANA, Salesforce), (4) fine-tuning 70B-class models. Everything runs in local Docker on commodity hardware with open-weights LLMs.

**Q15. What's your biggest risk and your mitigation?**
**Risk:** the Composer fails to resolve cross-DB joins reliably at Level 4+. **Mitigation:** Phase 5 is *deliberately* the midterm checkpoint — full end-to-end pipeline on a *narrow* version (one query per level) before scaling to 500. If federation breaks, I fall back to PostgreSQL-only with Odoo's full schema and still have a publishable single-DB multi-agent result.

**Q16. What if open-weights models aren't good enough?**
Qwen 2.5-Coder-7B already hits 82% on Spider — strong enough for the domain agents. The Composer and Validator use stronger reasoning models (DeepSeek-Coder or Llama 3.3 70B via OpenRouter). If a specific sub-task underperforms, the LLM abstraction layer makes swapping a config change, not a rewrite.

**Q17. Is your benchmark really publishable?**
Yes — SCM-SQL fills a documented gap (VLDB 2025 NL2SQL survey explicitly lists supply chain as missing). Target venues: ACL / EMNLP / COLING / VLDB. Closest precedent is EHRSQL (healthcare-specific) which was accepted at NAACL — same playbook.

### F. Personal & Process

**Q18. Why this project and not Option 1 (the simpler one)?**
The original option was a single-agent, single-DB NL-to-SQL — engineering, not research. This version targets four real open problems documented in 2024–2025 literature (CIDR, VLDB, ICLR) and produces a publishable benchmark. A dissertation should defend a thesis; "domain-aware decomposition beats pipeline-stage decomposition on enterprise schemas" is a defensible thesis.

**Q19. How does your work setting at Alta Futuris Solutions help?**
Direct access to real enterprise users (the "finance manager" example in the abstract is a real internal use case). This grounds the SCM-SQL benchmark in queries people actually ask, not synthetic ones. It also gives me a deployment context after the dissertation.

**Q20. What's your contribution if everything in the stack already exists?**
The stack is open-source; the **composition** is novel. Specifically: (a) domain-axis decomposition, (b) cross-DB Composer with auto FX/dialect handling, (c) source-agent error backpropagation, (d) the SCM-SQL benchmark, (e) empirical evidence that domain decomposition outperforms pipeline decomposition on enterprise schemas. Five concrete artefacts.

---

### G. NEW questions you should also rehearse (you have evidence for these now)

**Q21. Walk me through what your system actually does for one query — pick any.**
*Use* the cross-domain query from Phase 5: *"Total revenue vs total on-hand inventory value."* Narrate the path through Router → Finance + Inventory agents → Composer (CTE merge) → Compliance (RBAC scoping inside each CTE) → Validator (sqlglot syntax + Postgres EXPLAIN). Mention: 4 tables, $0.005 cost, EXPLAIN OK against the live DB.

**Q22. Your abstract says temporal reasoning is "deterministic, not a prompt trick." Show me what that means.**
"My `TemporalParser` is pure Python — 20+ regex patterns for `YoY`, `Q1 2026`, `fiscal Q3`, `rolling 30-day`, `past 6 months`, `this/last year-quarter-month-week`, `today`, `yesterday`, `YTD`, `MTD`. It produces concrete `DateRange` objects with ISO dates, plus optional window-function hints for rolling expressions. The agents *receive* these as prompt context — they don't invent date arithmetic. 30+ unit tests cover the patterns, and a live YoY query produces `SUM(CASE WHEN ... 2026 ... ELSE 0 END) AS current, SUM(CASE WHEN ... 2025 ... ELSE 0 END) AS prior` SQL that passes EXPLAIN."

**Q23. How do you handle compliance / RBAC?**
"`ComplianceProcessor` runs *after* the Composer, parses the composed SQL with sqlglot, and walks the AST to inject `company_id IN (1,2)` / `warehouse_id IN (3)` predicates into the `WHERE` clause of *each enclosing SELECT*. The critical correctness property is that a predicate added for a table inside a CTE stays inside that CTE — it never leaks to the outer query. I wrote this with regex first (Phase 4), it had a scope-leak bug on cross-domain queries, and Phase 5 replaced it with AST traversal. The fix is visible in commit history and I have a dedicated regression test that pins the behaviour."

**Q24. Show me multi-turn working.**
"A real 3-turn dialogue I tested live: Turn 1 — *'Show total revenue by customer this quarter'* — Router picks finance + demand, Composer builds two CTEs. Turn 2 — *'Only the top 5'* — `ReferenceDetector` classifies as REFINEMENT, the orchestrator inherits the prior turn's domains (the Router on its own would clarify on this fragment), agents emit new SQL with `LIMIT 5`. Turn 3 — *'Now compare with the same period last year'* — REFINEMENT detected, temporal parser supplies both date ranges, agents produce two-period `CASE WHEN` SQL. All three turns pass EXPLAIN against the live DB. Total cost: $0.04."

**Q25. What surprised you in the implementation?**
*Pick one honest answer.* Suggested: "The hardest bug was in the Compliance layer — Phase 4's regex approach injected `aml.company_id IN (1)` at the outer SELECT even when `aml` was only defined inside a CTE. Postgres rejected it with *missing FROM-clause entry for table 'aml'*. The fix in Phase 5 used sqlglot's AST and per-SELECT scope traversal. The lesson is general: regex on SQL is fine until it isn't, and the failure mode is silent-then-catastrophic on cross-scope references."

**Q26. What's currently NOT working?**
*Be honest, calibrated.* "Two phases are deliberately deferred. (1) Cross-database federation — DuckDB and Redis adapters exist but I haven't wired parallel execution + result merging; PG-only suffices for the midterm. (2) The Next.js frontend — backend API is ready, the UI is on the roadmap for July. Both are scoped and timeline-able; neither blocks the research contribution."

**Q27. What does your test coverage actually mean?**
"210 tests, 87 % branch coverage. Important caveat: most tests use mocked LLM responses to keep them deterministic and free. The *integration* layer is covered by 4 live smoke scripts (`smoke_llm.py`, `smoke_orchestrator.py`, `smoke_phase4.py`, `smoke_phase6.py`, `smoke_phase7.py`) which I've run end-to-end and verified each produces SQL that passes Postgres EXPLAIN. The benchmark evaluation in Phase 10 will provide the published accuracy numbers."

**Q28. Why 4 active specialists, not 5? Where's Compliance as an agent?**
"Compliance is cross-cutting, not domain-specific (Objective #7 in the abstract). It doesn't generate SQL from scratch — it post-processes the Composer's output and injects RLS predicates based on the calling user's role/company/warehouse. Treating it as a regular agent would have meant the Router had to pick it, which doesn't match how RLS works in practice — every query gets RLS applied automatically, not on request."

---

## 13. KEY PAPERS — ONE-LINER PER PAPER (memorise top 6)

| # | Paper | One-line why it matters |
|---|---|---|
| 1 | **MAC-SQL** (Wang et al., COLING 2025) | The decomposition baseline I beat — Selector/Decomposer/Refiner pipeline stages |
| 2 | **MARS-SQL** (Chen et al., Nov 2025) | I borrow the RL execution-feedback loop, adapt it to domain specialists |
| 3 | **CHASE-SQL** (Pourreza et al., ICLR 2025) | Multi-path reasoning + preference selection — I use the candidate-selection idea |
| 4 | **Spider 2.0** (Lei et al., ICLR 2025 Oral) | The 10.1% number — proves enterprise NL2SQL is unsolved |
| 5 | **NL2SQL is Solved... Not!** (Floratou et al., CIDR 2024) | Microsoft Research explicitly names temporal reasoning + ambiguity as open |
| 6 | **AmbiSQL** (Liu et al., 2025) | Interactive ambiguity resolution; I extend to supply-chain-specific terms |
| 7 | NL2SQL Survey (Luo et al., VLDB 2025) | Names temporal reasoning + enterprise benchmarks as open problems |
| 8 | Agentic LLMs in SCM (Klabe et al., IJPR 2025) | Industry case for multi-agent in supply chain |
| 9 | BIRD (Li et al., NeurIPS 2023) | The cross-domain benchmark; I evaluate on it |
| 10 | Qwen 2.5-Coder (Hui et al., 2024) | My primary model; 82% Spider EX justifies open-weights choice |

---

## 14. SUPERVISOR'S REMARK (already in your favour — quote it if pushed)

> *"The student has picked an open and active problem... The research gap, domain-aware multi-agent decomposition for supply chain, is genuine and well argued... The scope is ambitious but bounded... Evaluation against MAC-SQL, MARS-SQL, and CHASE-SQL is rigorous. The schedule fits the available time. I recommend the project proceed as proposed."*

---

## 15. THE FINAL 10 — RAPID-FIRE FACTS

1. **Problem:** GPT-4o → 10.1 % on Spider 2.0; SOTA → 39.1 % on BIRD-Ent.
2. **Gap:** No system decomposes by business domain; no benchmark targets SCM; temporal reasoning is open (VLDB 2025).
3. **Idea:** Five domain agents + AST-based Composer + AST-based Compliance + 3-attempt self-correction.
4. **Stack:** LangGraph + Anthropic Haiku 4.5 (SQL gen) + OpenAI gpt-4o-mini (router) + PostgreSQL 16 + DuckDB + Redis + FastAPI + sqlglot — all run via Docker Compose.
5. **Schema:** Odoo 17 ERP, **498 PostgreSQL tables loaded with demo data** (verified live); DataCo (180 K orders) reserved for Phase 8 benchmark.
6. **Benchmark:** SCM-SQL — 500+ NL/SQL pairs, 6 complexity levels (Phase 8).
7. **Baselines:** Single-agent zero-shot · MAC-SQL · MARS-SQL · CHASE-SQL.
8. **Metrics:** EX (Execution Accuracy) · VES (Valid Efficiency Score) · EM (Exact Match) + ablations.
9. **Timeline:** Apr 7 – Aug 1, 2026 · 10 phases. **Status today: Phases 1–7 done, ~5 weeks ahead of midterm target.**
10. **Publication target:** ACL / EMNLP / COLING / VLDB.

### The five hard numbers (memorise these — the panel loves a precise number)

| Claim | Number | Source |
|---|---|---|
| GPT-4o on Spider 2.0 enterprise | **10.1 %** | Lei et al., ICLR 2025 Oral |
| Strongest on BIRD-Ent (4000+ cols) | **~39.1 %** | OpenReview 2025 |
| Qwen 2.5-Coder-7B on Spider | **82.0 %** | Hui et al. 2024 (Tech Report) |
| Odoo tables in my live DB | **498** | my own `introspect_odoo.py` output |
| Cumulative LLM spend to date | **~$0.10** | sum of smoke-test token tracker outputs |

---

## 16. STUDY PLAN — 12 DAYS TO VIVA

| Day | Focus |
|---|---|
| Day 1–2 (today + tomorrow) | Read this doc end-to-end. Highlight gaps. Read the abstract docx once. |
| Day 3 | Re-read Sections 4, 5, 12.A, 12.B. Practise the 30-sec pitch (Section 1) aloud × 10. |
| Day 4 | Read MAC-SQL + MARS-SQL abstracts. Be able to explain pipeline-stage decomposition. |
| Day 5 | Read CHASE-SQL + Spider 2.0 abstracts. Practise Q4, Q5, Q11. |
| Day 6 | Whiteboard the 5-layer architecture without looking. Practise the 1-min answer (Section 2). |
| Day 7 | Read AmbiSQL + CSR-RAG abstracts. Practise Q9, Q10. |
| Day 8 | Read Floratou (CIDR 2024) + VLDB 2025 survey introductions. Anchor the *why*. |
| Day 9 | Mock viva — record yourself answering Q1–Q20. Listen back. |
| Day 10 | Practice the 6 query-level examples (Section 8). Be ready to write one on the whiteboard. |
| Day 11 | Re-read OPTION_2_ELEVATED_RESEARCH.md and the abstract docx once more. |
| Day 12 (viva day) | Read Sections 1, 2, 15 only. Show up. |

---

*Prepared: 2026-05-14  |  Sources: 2024AA05175.docx · PROJECT_DECISIONS_AND_CLARIFICATIONS.md · DEVELOPMENT_ROADMAP.md · OPTION_2_ELEVATED_RESEARCH.md*

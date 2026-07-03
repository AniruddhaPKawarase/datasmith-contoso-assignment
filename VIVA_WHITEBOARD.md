# WHITEBOARD DRAWINGS — Outline Viva, 2026-05-26

> **Purpose.** Five diagrams the panel is most likely to ask you to draw, with the exact sequence of strokes for each one. Drill on Day 3. Goal: start drawing within 5 seconds of the question, finish in 60–90 seconds, narrate while drawing.

> **Pen discipline.** Use **one colour** unless you have a specific reason to add a second. Two colours is fine for *call-outs* (e.g. circle the novelty), never for *aesthetics*.

---

## Drawing 1 — The 5-layer architecture (THE MOST LIKELY QUESTION)

When asked *"draw me your system":*

```
   ┌────────────────────────────────────────────────────┐
   │  USER QUERY                                        │
   └─────────────────────┬──────────────────────────────┘
                         ▼
   ┌────────────────────────────────────────────────────┐
   │  LAYER 1 — Query Understanding                     │
   │   • Router (LLM, classifies into 1-4 domains)      │
   │   • Temporal Parser (deterministic, 20+ patterns)  │
   │   • Ambiguity Resolver (AmbiSQL-style)             │
   │   • Reference Detector (multi-turn carry-over)     │
   └─────────────────────┬──────────────────────────────┘
                         ▼
   ┌────────────────────────────────────────────────────┐
   │  LAYER 2 — Five Domain Specialists                 │
   │   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
   │   │INVENTORY│ │LOGISTICS│ │ FINANCE │ │ DEMAND  │  │
   │   └─────────┘ └─────────┘ └─────────┘ └─────────┘  │
   │       (each: schema-slice, glossary, few-shots)    │
   └─────────────────────┬──────────────────────────────┘
                         ▼
   ┌────────────────────────────────────────────────────┐
   │  LAYER 3 — Composer (sqlglot AST)                  │
   │   • Wraps each fragment in a named CTE             │
   │   • INNER JOIN on shared FK key if projected       │
   │   • CROSS JOIN fallback otherwise                  │
   └─────────────────────┬──────────────────────────────┘
                         ▼
   ┌────────────────────────────────────────────────────┐
   │  LAYER 4 — Compliance (AST-based RBAC)             │
   │   • Per-SELECT scope traversal                     │
   │   • `company_id` / `warehouse_id` predicates       │
   │   • Audit-log emission                             │
   └─────────────────────┬──────────────────────────────┘
                         ▼
   ┌────────────────────────────────────────────────────┐
   │  LAYER 5 — Validator (3-stage pipeline)            │
   │   • Syntax: sqlglot parse + allow-list             │
   │   • Execution: PG EXPLAIN (30 s timeout)           │
   │   • Business rules: row sanity checks              │
   │     ─── on failure → back to GENERATE (max 3) ──┐  │
   └─────────────────────┬──────────────────────────────┘
                         ▼                              │
   ┌────────────────────────────────────────────────────┐
   │  RESPONSE                                          │
   │   • Composed SQL + result rows + confidence + log  │
   └────────────────────────────────────────────────────┘
```

### Stroke order for the whiteboard

1. **Five horizontal boxes** top to bottom, equal height. Label each on the left side: `1. Understanding`, `2. Specialists`, `3. Composer`, `4. Compliance`, `5. Validator`. ← 15 s
2. **Arrows down** between them. ← 5 s
3. **A retry arrow** from Validator (bottom-right of box 5) curving back up to the LEFT side of box 2. Label it *"max 3 self-correction"*. ← 10 s
4. **In box 2**, draw four small boxes for the four specialists. (You can skip Compliance here — it's its own box 4.) ← 15 s
5. **Bracket the "Composer + Compliance" pair** on the right with a label *"sqlglot AST"*. ← 5 s
6. **Top arrow in** (from "user query") and **bottom arrow out** (to "response"). ← 5 s

### What you say while drawing

> "Five layers. Layer 1 is query understanding — the Router classifies into domains, the Temporal parser converts NL temporal expressions to ISO dates deterministically, an Ambiguity resolver may pause for clarification, and a Reference detector handles multi-turn carry-over. Layer 2 is the four domain specialists — each restricted to its own schema slice, with curated few-shot examples. Layer 3 is the Composer — it wraps each agent's SQL in a named CTE and INNER-JOINs on a shared key if both project it, otherwise CROSS-JOINs. Layer 4 is Compliance — sqlglot AST traversal injects row-level security into each enclosing SELECT separately, so a CTE-scoped predicate never leaks. Layer 5 is the 3-stage validator — syntax via sqlglot, execution via Postgres EXPLAIN with timeout, business-rule sanity checks. If validation fails, the orchestrator routes back to the originating agent, up to 3 attempts total. On success, the response goes back to the user with the SQL, results, and audit log."

That paragraph is ~80 seconds. With the drawing, you'll come in at 90–100 s. **Practise until 90 s flat.**

---

## Drawing 2 — The research gap table

When asked *"what's the gap you're filling?":*

```
                                     │  GAP I AM FILLING
   ────────────────────────────────  │  ──────────────────────────────
   MAC-SQL / MARS-SQL / SoT          │  Decompose by SQL PIPELINE STAGE
   "schema-link → generate → refine" │  → I decompose by BUSINESS DOMAIN

   Spider, BIRD                      │  Single-DB benchmarks
                                     │  → I federate across PG+DuckDB+Redis

   AmbiSQL, Odin                     │  Single-turn ambiguity
                                     │  → I handle multi-turn carry-over

   NL2SQL Survey (VLDB 2025)         │  Temporal reasoning is OPEN
                                     │  → My TemporalParser is deterministic

   No SCM benchmark exists           │  → I'll release SCM-SQL (500+ Qs)
```

### Stroke order

1. Vertical line down the middle of the board. ← 3 s
2. Left column header: **"WHAT EXISTS"**. Right column header: **"WHAT I CONTRIBUTE"**. ← 10 s
3. Five row pairs, top to bottom — write the left side first, then immediately the right. Move row by row, not column by column. ← 60 s
4. **Circle the bottom-right cell** (the SCM-SQL benchmark). That's the deliverable that distinguishes you. ← 3 s

### What you say while drawing

> "Five things exist; five gaps remain. MAC-SQL and MARS-SQL decompose by pipeline stage — schema-link, generate, refine — but no one decomposes by business domain. Spider and BIRD evaluate on single DBs; real supply-chain queries span transactional ERP, analytical warehouse, and a live cache. AmbiSQL handles single-turn ambiguity; I extend that to multi-turn carry-over. The VLDB 2025 NL2SQL survey explicitly names temporal reasoning as an open problem — my parser is deterministic Python, not a prompt trick. And no NL-to-SQL benchmark currently targets supply chain — the SCM-SQL benchmark is my fifth contribution."

---

## Drawing 3 — The self-correction loop (THE NOVELTY DRILL-DOWN)

When asked *"how is your self-correction different from MARS-SQL?":*

```
                             ┌──────────────┐
              ┌──────────────┤  Validator   │◄────┐
              │              └──────┬───────┘     │
              │ validation error    │ pass        │
              │                     ▼             │
              │              ┌──────────────┐     │
              │              │   Response   │     │
              │              └──────────────┘     │
              ▼                                   │
       ┌─────────────┐                            │
       │  Diagnoser  │  ─── identifies            │
       │             │     WHICH agent's          │
       │             │     fragment failed        │
       └──────┬──────┘                            │
              │                                   │
              ▼                                   │
   ┌──────────────────────┐                       │
   │  Originating Agent   │ ── prior-error context│
   │  (re-prompt only)    │    fed back           │
   └──────────┬───────────┘                       │
              │                                   │
              ▼                                   │
   ┌──────────────────────┐                       │
   │   Composer (re-run)  │ ───────────────────► ─┘
   └──────────────────────┘
   attempt += 1, capped at 3
```

### What you say

> "MARS-SQL retries with a global pass. I retry the **originating agent only** — the Validator's diagnostic identifies which CTE produced the broken fragment, the prior-error string is fed back into that one agent's prompt, and the Composer re-runs. The attempt counter is in the LangGraph state, capped at 3. After 3 failures the system escalates to the user with the most-specific error message. This is what backpropagation means in my context — error blame routes to the source agent, not to a global retry."

---

## Drawing 4 — The 6 query complexity levels

When asked *"give me a hard example query":*

```
   L1 │ Single domain, single table         │ "How much stock for Product X?"
   L2 │ Single domain, multi-table          │ "Warehouses below safety stock?"
   L3 │ Cross-domain + temporal             │ "Supplier lead time vs defect rate, Q1"
   L4 │ Cross-DB federation                 │ "Total landed cost across markets"
   L5 │ Predictive / strategic              │ "If Supplier X disrupts, revenue impact?"
   L6 │ Multi-turn conversational           │ Turn 1→2→3 with carry-over
```

### What you say

> "Six levels of difficulty, mapped to the SCM-SQL benchmark. Level 1 is a single-table lookup. Level 2 needs a JOIN inside one domain. Level 3 is cross-domain — Q1's lead time vs defect rate spans procurement and quality. Level 4 needs federation across the ERP, analytics warehouse, and FX rate cache. Level 5 is strategic — a supplier-disruption scenario requires BOM traversal plus demand forecasting. Level 6 is multi-turn — I demonstrated that working end-to-end live. My Phase 5 midterm checkpoint hits L4 cleanly; the rest are the Phase 10 evaluation target."

---

## Drawing 5 — The 4-stack tech diagram (only if pushed on infra)

When asked *"what's the runtime stack?":*

```
         ┌─────────────────────────────────────────┐
         │       FastAPI (Python 3.12, async)      │
         │       + LangGraph orchestrator          │
         └────────┬──────────────────┬─────────────┘
                  │                  │
        ┌─────────▼───────┐     ┌────▼──────────────┐
        │  Anthropic API  │     │   OpenAI API      │
        │  claude-haiku-  │     │   gpt-4o-mini     │
        │  4-5 (SQL gen)  │     │   (Router, etc.)  │
        └─────────────────┘     └───────────────────┘

         ┌─────────────────────────────────────────┐
         │           Docker Compose                │
         │  ┌──────────┐ ┌─────────┐ ┌──────────┐  │
         │  │ Postgres │ │  Redis  │ │   Odoo   │  │
         │  │   16     │ │    7    │ │    17    │  │
         │  └──────────┘ └─────────┘ └──────────┘  │
         │  + DuckDB (embedded, file-based)        │
         └─────────────────────────────────────────┘
```

### What you say

> "FastAPI service is the single entry point; LangGraph runs the state machine. LLM calls hit two providers: Anthropic Haiku 4.5 for SQL generation, OpenAI gpt-4o-mini for the cheaper classification tasks. Data lives in three places — Postgres 16 holds the Odoo 17 ERP with 498 tables and demo data, Redis 7 holds the live-inventory cache, DuckDB is the embedded analytics warehouse. All three plus Odoo run via Docker Compose. The whole demo fits on one laptop — that's the reproducibility claim from the abstract."

---

## Practice protocol

1. **Day 3 of prep:** Draw each of the 5 diagrams from memory 3 times. Watch one of them back on video.
2. **Day 5:** Pick 2 at random; draw them while answering an unrelated question simultaneously (split-attention practice).
3. **Day 9 mock viva:** ask your friend to request 2 diagrams.
4. **Day 11:** Skim this doc once. Don't re-draw.

The 5-second rule: start drawing within 5 seconds of the question. **Pause-before-drawing is a tell that you don't know the answer.** Even if you start with an arrow that's wrong, redraw the arrow — the panel reads body confidence, not perfect lines.

---

*Source artefacts: VIVA_PREP_OUTLINE.md §§9, 10, 11, 12 · DEVELOPMENT_ROADMAP.md.*

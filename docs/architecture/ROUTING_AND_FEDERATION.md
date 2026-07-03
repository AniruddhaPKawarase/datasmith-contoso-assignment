# Architecture Deep-Dive — Routing, Composition, Federation, Compliance

**Dissertation:** Domain-Aware Multi-Agent NL-to-SQL for Enterprise Supply Chain Intelligence
**Closes outline-viva feedback:** V3 *"Mention proper architecture in details — how to classify the NL to decompose, how the LLM understands what domain it should be, and gather accurate data from cross-DB and cross-domain."*

This document walks through the four mechanisms the panel asked about, each grounded in the actual code path that runs today.

---

## 1.  How a query is classified into a domain  (the Router)

### 1.1  Inputs

The Router receives:

| Input | Where it comes from |
|---|---|
| `query: str` | The user's NL question, verbatim |
| `history_summary: str` | A compressed one-line per prior turn (older turns folded by `ConversationMemory`) |

### 1.2  The decision is a single LLM call

Implementation: `backend/app/agents/router.py` → `RouterAgent.route()`.

The Router calls `claude-haiku-4-5` (configured via `LLM_MODEL_ROUTER` in `.env`, currently OpenAI `gpt-4o-mini` for cost) with a deterministic system prompt — reproduced verbatim from the code below:

```
You are the Router for an enterprise supply-chain NL-to-SQL system.

Available business-domain specialists:
  inventory:  stock levels, warehouses, locations, traceability, lots, MRP, scrap
  logistics:  procurement, shipping, carriers, lead times, deliveries, customs
  finance:    accounting, cost, revenue, currency, tax, payments, P&L
  demand:     sales orders, pricing, customer demand, CRM, forecasts
  compliance: NEVER returned alone — added cross-cutting later when needed

Your job:
  1. Classify the query's INTENT (exactly one of):
       "supply_chain_question" — answerable from supply-chain data
       "out_of_scope"           — unrelated (e.g. "what's the weather?")
       "clarification_needed"   — too vague or ambiguous to answer
  2. Pick the minimal set of DOMAINS required (1–4).
  3. For each chosen domain, write a sub-question phrased in that
     specialist's vocabulary.

Reply with ONLY valid JSON: { intent, domains, sub_queries, reasoning }
```

The user-message payload is the query plus the history summary plus (if the query mentions a known ambiguous term from the glossary) an ambiguity warning hint.

The LLM returns a strict JSON object. We `json.loads` it and validate every field; unknown enum values are dropped silently.

### 1.3  When the LLM call fails: keyword fallback

`RouterAgent._keyword_fallback()` runs whenever the LLM raises or returns malformed JSON. It scores each domain by counting domain-keyword occurrences in the lowercased query (the keywords live in `backend/app/schema/domains.yaml`). The top-scoring domains win; ties break to the alphabetically-first.

This fallback exists so the pipeline survives without an LLM provider at all — useful for offline tests and CI.

### 1.4  Worked example A — single-domain, clean

**Query:** *"How many units of Product X are in stock right now?"*

| Step | Output |
|---|---|
| Router LLM call | `intent="supply_chain_question"`, `domains=["inventory"]`, `sub_queries=[{domain:"inventory", natural_language:"current stock count for Product X"}]` |
| Decision time | ~600 ms, ~70 input tokens, ~25 output tokens |
| Downstream effect | Only the Inventory agent is invoked; the other three never run |

### 1.5  Worked example B — cross-domain, harder

**Query:** *"Compare total revenue this quarter with on-hand inventory value, by company."*

| Step | Output |
|---|---|
| Router LLM call | `intent="supply_chain_question"`, `domains=["finance","inventory"]`, two sub-queries each rewritten in that domain's vocabulary |
| Downstream effect | Both Finance and Inventory agents run; their outputs flow to the Composer |

### 1.6  Worked example C — ambiguity short-circuit

**Query:** *"What is the lead time for our Asian suppliers?"*

| Step | Output |
|---|---|
| Glossary check | `lead time` is flagged ambiguous (procurement / manufacturing / delivery senses) |
| Ambiguity Resolver score | 0.7 (above 0.55 threshold) |
| Decision | `intent="clarification_needed"`; orchestrator emits a structured clarification question — *"By 'lead time' do you mean procurement, manufacturing, or delivery?"* |
| Downstream effect | No agent is invoked; the system asks the user and waits |

---

## 2.  How each agent knows its tables  (visible-tables set)

The Router has decided *which* agents run. Now each agent needs to know *what subset of the 498-table schema it owns*.

### 2.1  Domain-to-table mapping

`backend/app/schema/domains.yaml` is the single source of truth. Excerpt:

```yaml
domains:
  inventory:
    description: "Stock movement, quants, warehouses, locations, lots."
    primary_tables:
      - stock_quant
      - stock_move
      - stock_warehouse
      - stock_location
      - stock_picking
      - product_product
      - product_template
      ...
    keywords: [stock, inventory, warehouse, location, quant, ...]
```

Each domain has between 40 and 100 primary tables. `DomainMapping.visible_to(domain)` returns the frozen set of tables that domain's agent may touch.

### 2.2  The hard contract

When an agent generates SQL, the SQL extractor regex-parses table references after `FROM` / `JOIN`. Any table not in the agent's visible-tables set causes the agent to return `sql=""` with `out_of_scope` rationale — **the LLM cannot smuggle a finance table into the inventory agent's answer**.

Reference: `backend/app/agents/specialists.py` → `LLMDomainAgent.generate_sql` → the `out_of_scope = [t for t in tables if t not in self._visible]` check at the end.

### 2.3  Schema slice in the prompt

The agent does *not* see all 498 tables in its prompt — only the top-k most relevant **inside its visible set**, retrieved by `SchemaSearch`. This keeps every agent prompt ≤ 4 000 tokens regardless of how big the schema grows.

`SchemaSearch` is BM25 over column descriptions extracted from Odoo's `ir_model_fields` table (8 391 semantic field descriptions are cached in `backend/data/odoo_schema.json`). The agent's user prompt includes the top 8 tables ranked by NL-question relevance.

---

## 3.  How a cross-domain query is composed  (the Composer)

Once the per-domain agents have each produced their SQL fragment, the Composer assembles them into one statement that Postgres can execute. This is **the dissertation's central engineering contribution**.

### 3.1  The three composition strategies

Implementation: `backend/app/composer/composer.py` → `Composer.compose()`.

| # fragments | Strategy | When chosen |
|---|---|---|
| 0 | `noop` (return empty SQL) | All agents refused (out-of-domain) |
| 1 | `passthrough` | Single-domain query; emit the fragment unchanged with a wrapper |
| 2+ with shared FK | `inner_join:<key>` | A common foreign-key column (e.g. `company_id`, `product_id`) is projected by **every** fragment |
| 2+ no shared FK | `cross_join` | Per-domain single-row summaries CROSS JOINed into one row |

### 3.2  Worked walk-through of `inner_join`

**Query:** *"Compare revenue and on-hand stock for each company."*

The Finance agent produces:
```sql
SELECT am.company_id, SUM(aml.credit - aml.debit) AS revenue
FROM account_move_line aml
JOIN account_move am ON am.id = aml.move_id
WHERE ...
GROUP BY am.company_id
```

The Inventory agent produces:
```sql
SELECT sq.company_id, SUM(sq.quantity) AS on_hand
FROM stock_quant sq
WHERE ...
GROUP BY sq.company_id
```

**Both fragments project `company_id`.** The Composer's `_detect_shared_key()` walks the `JoinGraph` (built in Phase 2 from the FK graph), finds `company_id` as a shared foreign-key column, and confirms both inner-SELECTs include it in their output. It then emits:

```sql
WITH
  q_finance   AS ( SELECT am.company_id, SUM(aml.credit - aml.debit) AS revenue
                   FROM account_move_line aml
                   JOIN account_move am ON am.id = aml.move_id
                   WHERE ... GROUP BY am.company_id ),
  q_inventory AS ( SELECT sq.company_id, SUM(sq.quantity) AS on_hand
                   FROM stock_quant sq
                   WHERE ... GROUP BY sq.company_id )
SELECT q_finance.company_id, revenue, on_hand
FROM q_finance INNER JOIN q_inventory USING (company_id);
```

The key correctness rule, added in Phase 7 to fix a Phase 5 bug: **the INNER JOIN is emitted only if both CTEs actually project the shared key in their SELECT list**; otherwise the Composer falls back to CROSS JOIN. This rule is enforced in `composer.py` lines 96-103 with a unit test pinning it.

### 3.3  Why this matters for the panel's question

The panel asked *"how does the LLM gather accurate data from cross-DB and cross-domain?"* The answer is: **the LLM does not.** Each LLM call sees only one domain's slice. The cross-domain accuracy comes from the deterministic AST-level merge, not from a larger prompt. **This is exactly why our prompt budget stays bounded while MAC-SQL's grows with schema size** (per `MAC_SQL_HEAD_TO_HEAD.md` §3.1).

---

## 4.  How RBAC stays scoped to the right SELECT  (the Compliance Processor)

`backend/app/agents/compliance.py` → `ComplianceProcessor.apply()` runs after the Composer.

### 4.1  The construction

At build time, the processor scans `SchemaMetadata` and computes two frozen sets:

| Set | Built once | Used at runtime |
|---|---|---|
| `_has_company`  | All tables that carry a `company_id` column | Inject `<alias>.company_id IN (…)` predicate |
| `_has_warehouse` | All tables that carry a `warehouse_id` column | Inject `<alias>.warehouse_id IN (…)` predicate |

### 4.2  The traversal

For an incoming composed SQL:

1. Parse to AST with `sqlglot.parse_one(sql, read="postgres")`.
2. `for select_node in tree.find_all(exp.Select)`:  — visit every SELECT scope, top-level and CTE-internal.
3. For each SELECT, collect the *directly-referenced* tables (excluding ones nested in deeper SELECTs).
4. For each table that carries `company_id` or `warehouse_id`, add an `AND <alias>.<col> IN (…)` predicate to that SELECT's WHERE clause.

### 4.3  Why per-SELECT scope matters — the Phase 5 regression

If we naïvely string-injected `aml.company_id IN (1)` at the *outer* level of a query whose `aml` alias is only defined inside a CTE, Postgres rejects with `missing FROM-clause entry for table "aml"`. Phase 4's regex approach hit this bug; Phase 5's AST traversal fixes it.

Regression test pinning this is in `backend/tests/test_compliance_v2.py::test_predicate_appears_inside_cte_not_outer`.

---

## 5.  Cross-database federation  (Phase 8 — current status: scaffolded)

The dissertation scope (abstract §2) includes federation across PostgreSQL, DuckDB, and Redis. **As of midsem the adapter layer is built but the orchestration of cross-DB execution is Phase 8 work.** Honest disclosure.

### 5.1  The three back-ends

| Store | Purpose | Adapter |
|---|---|---|
| PostgreSQL 16 | Operational ERP — Odoo schema, transactional data | `backend/app/db/postgres.py` |
| DuckDB 1.5 | Analytical warehouse — DataCo orders, derived aggregates | `backend/app/db/duckdb.py` |
| Redis 7 | Live state — current stock levels, real-time inventory positions | `backend/app/db/redis_adapter.py` |

All three adapters exist today and have basic CRUD + execute methods. They are not yet wired into the Composer's federation path.

### 5.2  The planned federation strategy  (Phase 8)

For a Level-4 query that requires data from two back-ends, the Composer will:

1. Identify per-fragment which back-end each fragment targets (the domain mapping carries `default_backend` per domain — e.g. *demand → Postgres*, *analytics → DuckDB*, *live_inventory → Redis*).
2. Execute each fragment on its own back-end independently and in parallel.
3. Merge results in Python by joining on the shared key (`company_id`, `product_id`, etc.) in pandas / Polars.
4. Return the merged result through the same response envelope as a single-DB query.

This is implementation work, not research work — the architectural pattern is settled, the back-end adapters exist, the merge logic is straightforward Python. Phase 8 lands it.

### 5.3  Why we defer federation to Phase 8

The midsem-checkpoint contract from the roadmap requires a full end-to-end pipeline running on **one** back-end. We hit that with Phase 5 (Postgres). Federation is bonus complexity that the dissertation can defend as scoped-but-deferred without weakening the core thesis (domain-axis vs pipeline-axis decomposition).

---

## 6.  Self-correction — where the error actually goes

When the Validator fails a query, the error is not retried globally — it is sent back to the *originating agent*.

### 6.1  Identification

The Composer annotates each CTE in the composed SQL with a `-- domain=finance` comment. The `ExecutionValidator._guess_location()` parses the Postgres error message, finds the most-recent domain comment above the cited table/column, and emits a `ValidationIssue` with `location="finance"`.

### 6.2  Routing back

The Orchestrator's `_after_validate` predicate returns `"retry"`; the LangGraph state machine re-enters the `generate` node with the validation error stuffed into `prior_error`. **Only the agent named in `location` re-runs**; the others' outputs are cached.

### 6.3  Cap

3 attempts. After that the system returns the most-specific error message to the user and stops burning tokens.

This is the **source-routed self-correction** distinction from MARS-SQL's global retry — documented in `MAC_SQL_HEAD_TO_HEAD.md` §2 and in the abstract Objective #4.

---

## 7.  End-to-end sequence diagram  (single query, single domain — the simplest path)

```
User → Orchestrator
              ↓
         classify_node
              ├─ Router.route(query)                → LLM (claude-haiku-4-5)
              ├─ TemporalParser.parse(query)        → deterministic Python
              └─ AmbiguityResolver.resolve(query)   → glossary lookup
              ↓
         [intent != supply_chain_question?] → respond_node → END
              ↓
         route_node                               → assemble SubQueries
              ↓
         generate_node
              └─ for each domain in state.domains:
                     LLMDomainAgent[domain].generate_sql(...)  → LLM
              ↓
         compose_node                             → Composer.compose()
              ↓
         compliance_node                          → ComplianceProcessor.apply()
              ↓
         validate_node                            → ValidationPipeline.run()
              │     syntax   (sqlglot.parse)
              │     execution (Postgres EXPLAIN, 30 s timeout)
              │     business (row count, value ranges)
              ↓
         [issues AND attempt < 3?] → generate_node  (loop)
              ↓ no
         respond_node                             → assemble final response
              ↓
         memory.record_turn()                     → persist for multi-turn carry-over
              ↓
         User ← composed SQL + results + confidence + audit log
```

The diagram is the architecture, top to bottom, in the order a query actually traverses the system.

---

## 8.  Summary — three sentences for the viva

> The Router is one LLM call returning structured JSON (intent + domains + per-domain sub-questions); each chosen domain agent runs against its own bounded schema slice, with table-allow-list enforcement so it cannot smuggle out-of-domain tables into its answer. The Composer assembles per-domain SQL fragments into one statement via sqlglot-AST CTE wrapping — INNER JOIN on a shared FK if both CTEs project it, CROSS JOIN otherwise — and the Compliance Processor walks every SELECT scope (top-level + each CTE separately) to inject RBAC predicates at the correct scope. Cross-DB federation is scaffolded but deferred to Phase 8 — the three adapters exist today; the parallel-execution-then-merge orchestration ships before the final.

---

*Document version 1.0  ·  Generated 2026-05-20  ·  Author: Aniruddha Prakash Kawarase*

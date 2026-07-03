# MAC-SQL Head-to-Head Comparison

**Dissertation:** Domain-Aware Multi-Agent NL-to-SQL for Enterprise Supply Chain Intelligence
**Closes outline-viva feedback:** V2 *"Show the comparison of the current dataset used in the research paper (MAC-SQL Wang et al. 2025) and what we are building on, and how is it better."*
**Reference paper:** Wang, B. et al. *MAC-SQL: A Multi-Agent Collaborative Framework for Text-to-SQL*. Proceedings of COLING 2025. arXiv 2312.11242. PDF cached at `docs/paper/01_MAC-SQL_Wang_COLING2025.pdf`.

---

## 1.  Why MAC-SQL is the right baseline to single out

Among the four multi-agent NL-to-SQL systems published in 2024–2025 (MAC-SQL, MARS-SQL, SQL-of-Thought, CHASE-SQL), **MAC-SQL is the closest architectural analogue to this dissertation**:

- Both use multiple LLM-driven agents (not a single end-to-end model).
- Both target real database schemas (BIRD-scale rather than Spider-tiny).
- Both ship an open implementation that we can re-run with our preferred LLM backbone.
- Both are evaluated on field-standard benchmarks (Spider, BIRD).

The dissertation argument is that **MAC-SQL's decomposition axis is wrong for enterprise SCM workloads**, and our domain-axis decomposition closes the gap. This head-to-head exists to substantiate that claim.

---

## 2.  Side-by-side architectural comparison

| Dimension | MAC-SQL (Wang et al., 2025) | This dissertation |
|---|---|---|
| **Number of agents** | 3 | 4 specialists + 1 cross-cutting (Compliance) + Router |
| **Decomposition axis** | **Pipeline stage** — Selector, Decomposer, Refiner | **Business domain** — Inventory, Logistics, Finance, Demand |
| **Selector / Router role** | Schema-linker — narrows tables for the prompt | Domain-classifier — picks which specialist(s) to invoke |
| **Decomposer / Composer role** | Decomposes the NL question into sub-questions; same agent answers all sub-questions | Composer merges *already-generated* SQL fragments from independent specialists via sqlglot AST CTE wrapping |
| **Refiner / Validator role** | Iterates on the SQL with execution feedback | 3-stage validator (syntax via sqlglot → execution via Postgres EXPLAIN → business rules) + source-routed retry |
| **Schema retrieval** | Top-k tables in the prompt; selection is the Selector's main job | CSR-RAG retrieval *per agent*, bounded to that agent's domain slice (4 K tokens) |
| **Cross-domain handling** | Implicit — the LLM holds the whole query in one prompt | Explicit — Composer joins per-domain CTEs on FK keys discovered from the JoinGraph |
| **Cross-database federation** | Not addressed (single DB target per question) | Adapter layer for PostgreSQL · DuckDB · Redis (federation engine in Phase 8) |
| **Temporal reasoning** | LLM handles dates inside the prompt | Deterministic Python `TemporalParser` — 20+ patterns including fiscal calendars, rolling N, YoY |
| **Ambiguity resolution** | None published | AmbiSQL-inspired `AmbiguityResolver` with structured clarification questions |
| **Compliance / RBAC** | None published | `ComplianceProcessor` — sqlglot AST traversal injects per-SELECT row-level-security predicates |
| **Multi-turn dialogue** | None published | `ReferenceDetector` + `ConversationContextBuilder` + domain carry-over on REFINEMENT / COMPARISON / FOLLOW_UP turns |
| **Self-correction loop** | Refiner retries with error message — global retry | Source-routed retry — error is sent back to the *originating agent only*, max 3 attempts |
| **Backbone LLM (their headline)** | GPT-4 (closed) and SQL-LLaMA-7B (open-weights, fine-tuned by them) | claude-haiku-4-5 for SQL generation, gpt-4o-mini for routing |
| **Backbone we will use for head-to-head** | claude-haiku-4-5 (same as ours — fairness contract per `EVALUATION_FRAMEWORK.md` §5) | claude-haiku-4-5 |
| **Evaluation benchmarks reported in the paper** | Spider, BIRD | Spider, BIRD, SCM-SQL (ours) |
| **Headline EX in the paper** | Spider: ~86 % (GPT-4)  ·  BIRD-dev: ~59 % (GPT-4)  *(numbers to be re-verified from §4 of the paper)* | Targets in `EVALUATION_FRAMEWORK.md` §11 |

---

## 3.  Where MAC-SQL leaves gaps for enterprise SCM

Three concrete gaps justify a new architecture:

### 3.1  Cross-domain query degradation

A pipeline-axis decomposition processes the *whole* query in each stage. For a cross-domain SCM query like

> *"Compare total revenue with on-hand inventory value this quarter, by company."*

— MAC-SQL's Selector must surface *all* the relevant tables across finance + inventory in one prompt (10+ tables), and the Decomposer must hold the whole picture in its working memory. The prompt-window stress is concentrated.

In our architecture the same query splits cleanly: the Finance agent sees its 83-table slice only, the Inventory agent sees its 66-table slice only, and the Composer joins their *outputs*. Each prompt is bounded; the cross-domain merge is deterministic AST work, not an LLM call.

### 3.2  Fiscal calendar handling

MAC-SQL relies on the LLM to map phrases like *"fiscal Q3"* to date predicates. The LLM does not know the tenant's fiscal-year start month. Our deterministic `TemporalParser` (`backend/app/temporal/parser.py`) reads the configured `FiscalConfig` and emits exact ISO date ranges — no prompt trick.

### 3.3  Row-level security

MAC-SQL has no notion of compliance — it generates SQL that returns whatever the database has. For an enterprise tenant where users can only see their own company / warehouse, this is a non-starter. Our `ComplianceProcessor` injects `company_id IN (…)` and `warehouse_id IN (…)` predicates **at the correct AST scope** (per SELECT, never leaking across CTE boundaries — the Phase-5 commit `13bc4b7` includes the regression test that pins this behaviour).

---

## 4.  Head-to-head measurement plan

The numbers below are the plan, not yet the measurements. Numbers are filled in during Phase 8 (pilot, ~50 queries) and Phase 10 (full, ~500 queries).

### 4.1  Setup

| Constant | Value |
|---|---|
| LLM backbone (both systems) | `claude-haiku-4-5`, temperature 0 |
| Postgres instance | Same Docker `scm-postgres` container |
| Schema cache | Same `backend/data/odoo_schema.json` |
| Prompt token budget per agent | 4 000 |
| Self-correction max attempts | 3 |
| SQL timeout | 30 s |
| Scoring | EX / VES / EM per `EVALUATION_FRAMEWORK.md` |

### 4.2  Adapter we will write

`scripts/baselines/mac_sql_adapter.py` will:

1. Clone MAC-SQL's public repo (`github.com/wbbeyourself/MAC-SQL`) into `external/MAC-SQL/`.
2. Replace their OpenAI/GPT-4 client with our `LLMProvider` configured for Anthropic Haiku 4.5.
3. Expose a callable `mac_sql_predict(question, schema_handle) -> sql_string` that runs Selector → Decomposer → Refiner using their published prompts unchanged.
4. Log every LLM call to the shared `MessageLog` so we can audit token cost parity.

Effort: 1 day. Risk: their prompt strings reference GPT-4-specific quirks (e.g. `{{system}}` placeholders) — those need a light port. We will *not* re-tune their prompts; using their published prompts unchanged is part of the fairness contract.

### 4.3  Result tables (the placeholders)

**Pilot — 50 SCM-SQL questions, midsem deliverable**

| System | L1 EX | L2 EX | L3 EX | L4 EX | L5 EX | L6 EX | Overall EX | Overall VES |
|---|---|---|---|---|---|---|---|---|
| MAC-SQL  (Haiku backbone) | tbd | tbd | tbd | tbd | tbd | tbd | tbd | tbd |
| **Ours**                   | tbd | tbd | tbd | tbd | tbd | tbd | tbd | tbd |
| **Δ ours − MAC-SQL**       | tbd | tbd | tbd | tbd | tbd | tbd | tbd | tbd |

**Full — Spider, BIRD, SCM-SQL  (Phase 10 deliverable)**

| Benchmark | MAC-SQL EX (our re-run, Haiku) | MAC-SQL EX (their paper, GPT-4) | Ours EX | Lift (ours − MAC-SQL-Haiku) |
|---|---|---|---|---|
| Spider    | tbd | ~86 % *(to verify)* | tbd | tbd |
| BIRD-dev  | tbd | ~59 % *(to verify)* | tbd | tbd |
| SCM-SQL   | tbd | n/a (benchmark is ours) | tbd | tbd |

### 4.4  Pre-committed defence positions

| Outcome | What we say |
|---|---|
| Ours beats MAC-SQL on L3–L6 by ≥ 10 pp (target) | Thesis confirmed — domain-axis decomposition is measurably better on cross-domain SCM workloads at the same LLM budget. |
| Ours beats MAC-SQL on L1–L2 by < 5 pp | Expected — simple single-domain queries do not benefit from decomposition; both architectures perform similarly when the prompt fits in one window. |
| Ours beats MAC-SQL on Spider by 0–3 pp | Expected — Spider's schemas are too small for domain decomposition to help; we should not regress significantly either. |
| Ours **loses** to MAC-SQL anywhere | Honest writeup: where exactly, why, and whether the gap is within the 95 % CI from the bootstrap test. We do not paper over losses. |

---

## 5.  Resource and timeline implications

| Item | Cost / time | Decision |
|---|---|---|
| MAC-SQL adapter (port their repo to Haiku backbone) | 1 day | Build during midsem week |
| 50-query pilot run, both systems | ~$2 in API spend  ·  ~30 min | Run during midsem week |
| Full 500-query run, all 5 baselines | ~$15 in API spend  ·  ~3 hrs | Phase 10 |
| GPU requirements | None — we use the Anthropic API, not their open-weights SQL-LLaMA | RTX 3050 not needed for this head-to-head |

The previously asked GPU question (*"can the RTX 3050 run MAC-SQL?"*) is moot for this head-to-head — the API-based same-backbone protocol bypasses local-model concerns entirely. The RTX 3050 is reserved for Phase 8 benchmark seeding (Qwen 2.5-Coder-7B locally) where local inference saves API cost on the throwaway draft pass.

---

## 6.  Summary — one paragraph for the viva

> MAC-SQL (COLING 2025) is the closest published baseline to this dissertation, sharing the multi-agent premise but differing on the decomposition axis — MAC-SQL splits work by SQL-writing stage (Selector → Decomposer → Refiner), while this dissertation splits by business domain (Inventory, Logistics, Finance, Demand). MAC-SQL has no cross-DB federation, no fiscal-calendar reasoning, no row-level-security injection, and no multi-turn dialogue — all of which enterprise supply-chain workloads demand. The head-to-head will run MAC-SQL with the *same* claude-haiku-4-5 backbone as our system on a 50-query pilot for midsem and the full 500-query SCM-SQL benchmark for the final. Target: ≥ 10 percentage points lift on Levels 3–6 with Cliff's δ ≥ 0.33 and Bonferroni-corrected p ≤ 0.05.

---

*Document version 1.0  ·  Generated 2026-05-20  ·  Author: Aniruddha Prakash Kawarase*

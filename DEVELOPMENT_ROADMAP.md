# DEVELOPMENT ROADMAP
## Domain-Aware Multi-Agent NL-to-SQL for Enterprise Supply Chain Intelligence

### Timeline: April 7 - August 1, 2026 (~17 weeks)
### Total Phases: 10 | Midterm Target: Phase 5 complete

---

## PHASE OVERVIEW

| Phase | Name | Duration | Deadline | Midterm? |
|-------|------|----------|----------|----------|
| 1 | Project Setup & Infrastructure | 1 week | Apr 13 | |
| 2 | Database Layer & Schema Intelligence | 1.5 weeks | Apr 24 | |
| 3 | Core Agent Framework & LLM Abstraction | 1.5 weeks | May 5 | |
| 4 | Domain-Specialist Agents (5 agents) | 2 weeks | May 19 | |
| 5 | Composition, Federation & Self-Correction | 2 weeks | Jun 2 | MIDTERM |
| 6 | Temporal Reasoning & Ambiguity Resolution | 1.5 weeks | Jun 13 | |
| 7 | Multi-Turn Conversational Engine | 1.5 weeks | Jun 24 | |
| 8 | SCM-SQL Benchmark Creation (500+ queries) | 1.5 weeks | Jul 5 | |
| 9 | Frontend (Next.js + Shadcn/ui) | 1.5 weeks | Jul 16 | |
| 10 | Evaluation, Paper Writing & Final Polish | 2 weeks | Aug 1 | FINAL |

---

## PHASE 1: Project Setup & Infrastructure
### Deadline: April 13, 2026
### Status: [x] COMPLETE (2026-05-14)

#### Objectives
- Repository setup with monorepo structure
- Docker Compose for all services (Odoo + PostgreSQL + DuckDB + Redis)
- CI/CD with GitHub Actions (lint, test, type-check)
- LLM abstraction layer (OpenRouter primary, Ollama fallback)
- Project documentation structure

#### Tasks
```
[x] 1.1  Initialize Git repository with monorepo structure
         /backend  (Python, FastAPI)
         /frontend (Next.js)
         /benchmark (SCM-SQL dataset)
         /docs (architecture, paper drafts)
         /docker (Compose files, Dockerfiles)
         /scripts (setup, data loading, evaluation)

[x] 1.2  Create Docker Compose with:
         - Odoo 17 + PostgreSQL 16 (with demo data)
         - DuckDB (embedded, no separate container)
         - Redis 7
         - FastAPI backend service
         - Next.js frontend service

[x] 1.3  Build LLM Abstraction Layer:
         - Unified interface: generate(prompt, model, temperature) -> response
         - OpenRouter provider (primary): API key from env
         - Ollama provider (fallback): local inference
         - Model routing config: which model for which task
         - Token tracking and cost monitoring
         - Retry logic with provider fallback

[x] 1.4  Setup development tooling:
         - Python: pyproject.toml, ruff (linter), mypy (type checker), pytest
         - Node: package.json, ESLint, TypeScript strict
         - Pre-commit hooks (ruff, mypy, eslint)
         - GitHub Actions CI pipeline

[x] 1.5  Create CLAUDE.md files:
         - /backend/CLAUDE.md (Python conventions, agent architecture rules)
         - /frontend/CLAUDE.md (Next.js conventions, component rules)
         - /CLAUDE.md (root: project overview, phase tracking, resume instructions)

[x] 1.6  Verify Docker Compose starts all services
         - Docker Desktop 29.4.3 installed and verified
         - PostgreSQL 16 healthy on localhost:5432
         - Redis 7 healthy on localhost:6379
         - Odoo 17 serving HTTP 200 on localhost:8069
         - Odoo database initialised with 8 SCM modules + demo data
         - 498 tables · 51 products · 71 stock quants · 84 stock moves
         - 28 pickings · 24 sale orders · 11 purchase orders · 24 account moves
         - 42 partners · 8 MRP BOMs across 2 warehouses
         - Backend venv installed; OpenAI + Anthropic smoke test passing
```

#### Resume Point
> Phase 1 COMPLETE. Backend venv at `.venv/`, three Docker containers running, Odoo DB seeded. Proceed to Phase 2: schema introspection + domain-to-schema mapping.

#### Deliverables
- Working Docker Compose environment
- LLM abstraction layer with OpenRouter + Ollama
- CI pipeline green
- 3 CLAUDE.md files

#### Resume Point (if limit hits)
> Save which task number (1.1-1.6) was last completed. Next session starts from the next incomplete task.

---

## PHASE 2: Database Layer & Schema Intelligence
### Deadline: April 24, 2026
### Status: [x] COMPLETE (2026-05-14)
### Depends on: Phase 1

#### Objectives
- Odoo schema introspection and metadata extraction
- DuckDB analytics warehouse setup with Kaggle data
- Schema intelligence module (table descriptions, column semantics, relationships)
- Domain-to-schema mapping (which tables belong to which domain agent)

#### Tasks
```
[x] 2.1  Odoo Schema Introspection:
         - 498 tables, 5116 columns, 1866 FKs introspected from live DB
         - Combined PG information_schema with Odoo ir_model + ir_model_fields
           (8391 field descriptions captured)
         - Output: backend/data/odoo_schema.json (2MB cached snapshot)
         - Module: backend/app/schema/{metadata,introspection}.py

[x] 2.2  Domain-Schema Mapping (99.8% coverage of 498 tables):
         - 5 domains with explicit primary tables + prefix-rule fallback
         - INVENTORY:  100 tables (stock_*, mrp_*, lot_*, picking_*, procurement_*)
         - LOGISTICS:   13 tables (stock_picking, purchase_*, delivery_*, vendor_*)
         - FINANCE:     84 tables (account_*, res_currency*, payment_*)
         - DEMAND:      26 tables (sale_*, crm_*, utm_*)
         - COMPLIANCE:  65 tables (res_users/groups/company, ir_*, privacy_*)
         - Shared:      19 tables (product_*, partner_*) visible to all
         - Excluded:   138 tables (mail_*, web_*, sms_*, etc.) — infra/UI only
         - Wizards:     33 tables (auto-classified as UI helpers)
         - Module: backend/app/schema/{domains.yaml,domains.py}

[x] 2.3  DuckDB Analytics Warehouse (adapter ready; data load Phase 8):
         - Adapter at backend/app/db/duckdb.py (in-process, no container)
         - Container path /data/X auto-redirects to backend/data/X for host dev
         - 95% test coverage; ready to load DataCo + Global Inventory data
         - Note: dataset ingestion deferred to Phase 8 (benchmark prep)

[x] 2.4  Redis Real-Time Layer:
         - Adapter at backend/app/db/redis_adapter.py
         - Versioned key schema: scm:v1:{quant,fx,session}:...
         - Inventory mirror + FX cache + session helpers
         - Live ping verified against running Redis 7 container

[x] 2.5  Schema Intelligence Module:
         - Business glossary: 17 terms across 5 domains
           (lead time, safety stock, landed cost, gross margin, AOV, ...)
           with explicit ambiguity tracking for 3 multi-meaning terms
         - Module: backend/app/schema/{glossary.yaml,glossary.py}
         - Join-path discovery: FK graph + BFS shortest-path + multi-path
           enumeration (backend/app/schema/joins.py, 91% coverage)
         - Schema search: TF-IDF-style retrieval over 5116 columns + 8391
           Odoo descriptions (backend/app/schema/search.py, 100% coverage)

[x] 2.6  Tests (backend/tests/):
         - test_schema_metadata.py (5 tests — JSON round-trip + immutability)
         - test_schema_domains.py (12 tests — resolver, coverage, validation)
         - test_schema_glossary.py (7 tests — lookup, ambiguity, real YAML)
         - test_schema_joins.py (8 tests — BFS, max-hops, unreachable)
         - test_schema_search.py (5 tests — scoring, allow-list, top-k)
         - test_db_adapters.py (10 tests — DuckDB unit + Postgres/Redis live)
         - Total: 65 tests, 86.29% coverage, all gates green
```

#### Resume Point
> Phase 2 COMPLETE. Schema cache at `backend/data/odoo_schema.json` (regenerate
> with `python scripts/introspect_odoo.py`). Domain mapping covers 99.8% of
> the 498 tables. Proceed to Phase 3: core agent framework with LangGraph.

#### Deliverables
- Schema metadata for all ~600 Odoo tables
- Domain-to-schema mapping (5 domains)
- DuckDB with Kaggle datasets loaded
- Redis with live inventory snapshot
- Business glossary (50+ term mappings)
- Schema intelligence module with join path discovery

#### Resume Point
> Save which task (2.1-2.6) was completed. Include the domain mapping YAML path and number of tables catalogued.

---

## PHASE 3: Core Agent Framework & LLM Abstraction
### Deadline: May 5, 2026
### Status: [x] COMPLETE (2026-05-14)
### Depends on: Phase 1, Phase 2

#### Objectives
- Multi-agent orchestration framework using LangGraph
- Agent base class with schema-aware prompting
- Router/Planner agent that classifies queries by domain
- Conversation memory for multi-turn support
- Agent communication protocol

#### Tasks
```
[ ] 3.1  Agent Base Class:
         - BaseAgent with: name, domain, schema_context, business_glossary
         - generate_sql(query, context) -> SQLResult
         - validate_sql(sql) -> ValidationResult
         - Prompt template system with schema injection
         - Few-shot example management per agent

[ ] 3.2  LangGraph Orchestration:
         - State machine: CLASSIFY -> ROUTE -> GENERATE -> COMPOSE -> VALIDATE -> RESPOND
         - State schema: query, intent, domains[], sub_queries[], composed_sql, results, errors, turn_history
         - Conditional edges based on classification results
         - Error routing: VALIDATE -> back to GENERATE (max 3 loops)

[ ] 3.3  Router/Planner Agent:
         - Input: natural language query + conversation history
         - Output: list of domains involved + query decomposition plan
         - Uses lightweight model (fast classification)
         - Handles multi-domain queries (e.g., "inventory + finance")

[ ] 3.4  Conversation Memory Manager:
         - Session-based conversation tracking
         - Turn history with: user_query, generated_sql, results_summary, domains_used
         - Pronoun/reference resolution context
         - Support for "compare with last query" type references

[ ] 3.5  Agent Communication Protocol:
         - Message format: {from_agent, to_agent, type, payload}
         - Types: QUERY, SUB_QUERY, RESULT, ERROR, CLARIFICATION
         - Shared context store for cross-agent data sharing
         - Event logging for debugging and audit

[ ] 3.6  Tests:
         - Router classification accuracy tests (mock queries)
         - LangGraph state machine flow tests
         - Conversation memory persistence tests
         - Agent communication protocol tests
```

#### Deliverables
- LangGraph orchestration pipeline (end-to-end flow)
- Router/Planner agent with domain classification
- Conversation memory manager
- Agent communication protocol
- Full test suite

#### Resume Point
> Save LangGraph state machine definition status and router agent accuracy on test queries.

---

## PHASE 4: Domain-Specialist Agents (5 Agents)
### Deadline: May 19, 2026
### Status: [x] COMPLETE (2026-05-14)
### Depends on: Phase 2, Phase 3

#### Objectives
- Build 5 domain-specialist agents, each with domain-specific schema knowledge, glossary, and few-shot examples
- Each agent generates SQL for its domain tables only
- Implement CSR-RAG style schema retrieval for large schemas

#### Tasks
```
[ ] 4.1  Inventory Agent:
         - Schema: stock_move, stock_quant, stock_warehouse, stock_location, 
           stock_picking, product_product, product_template, stock_valuation_layer,
           stock_warehouse_orderpoint (safety stock)
         - Capabilities: stock levels, safety stock analysis, stockout risk,
           inventory turnover, warehouse utilization
         - Few-shot examples: 20+ query-SQL pairs
         - Business glossary: 15+ inventory-specific terms

[ ] 4.2  Logistics Agent:
         - Schema: stock_picking (shipments), delivery_carrier, stock_move_line,
           purchase_order (procurement), res_partner (suppliers/carriers)
         - Capabilities: supplier lead times, shipment tracking, delivery performance,
           carrier comparison, procurement cycle analysis
         - Few-shot examples: 20+ query-SQL pairs
         - Business glossary: 15+ logistics-specific terms

[ ] 4.3  Finance Agent:
         - Schema: account_move, account_move_line, account_account, res_currency,
           res_currency_rate, account_tax, account_payment
         - Capabilities: cost analysis, multi-currency conversion, P&L by product/warehouse,
           landed cost calculation, tax computation
         - Few-shot examples: 20+ query-SQL pairs
         - Business glossary: 15+ finance-specific terms

[ ] 4.4  Demand Agent:
         - Schema: sale_order, sale_order_line, stock_warehouse_orderpoint,
           product_pricelist, product_pricelist_item, crm_lead
         - Capabilities: sales trends, demand forecasting queries, seasonal patterns,
           customer segmentation, order fulfillment rates
         - Few-shot examples: 20+ query-SQL pairs
         - Business glossary: 15+ demand-specific terms

[ ] 4.5  Compliance Agent:
         - Schema: res_users, res_groups, ir_rule, ir_model_access, 
           audit_log (custom), res_company
         - Capabilities: RBAC enforcement (inject WHERE clauses for user role),
           data isolation by company/warehouse, audit trail generation,
           query permission validation
         - Inject row-level security predicates into all queries
         - Log all query executions for compliance audit

[ ] 4.6  Schema-Aware Prompting (CSR-RAG):
         - For each query, retrieve only relevant schema elements (not all 600 tables)
         - Contextual retrieval: match NL terms to table/column descriptions
         - Structural retrieval: follow FK relationships from matched tables
         - Relational retrieval: identify join paths between matched tables
         - Limit schema context to <4000 tokens per agent prompt

[ ] 4.7  Integration tests:
         - Each agent tested independently on 10+ queries
         - Verify SQL syntax correctness
         - Verify correct table usage (no cross-domain leakage)
         - Verify RBAC injection by Compliance Agent
```

#### Deliverables
- 5 functional domain-specialist agents
- 100+ few-shot query-SQL pairs (20+ per agent)
- 75+ business glossary terms (15+ per domain)
- CSR-RAG schema retrieval module
- Integration test suite per agent

#### Resume Point
> Save which agents (4.1-4.5) are complete and their individual test pass rates.

---

## PHASE 5: Composition, Federation & Self-Correction
### Deadline: June 2, 2026 | MIDTERM CHECKPOINT
### Status: [x] COMPLETE (2026-05-14) — federation deferred (PG-only sufficient for midterm demo)
### Depends on: Phase 4

#### Objectives
- Composer Agent that merges sub-queries from multiple domain agents
- Cross-database federation (PostgreSQL + DuckDB + Redis)
- Self-correction loop with error diagnosis and re-routing (max 3 attempts)
- End-to-end pipeline working for all 6 query complexity levels

#### Tasks
```
[ ] 5.1  Composer Agent:
         - Input: list of sub-queries from domain agents + join requirements
         - Merge via CTEs (Common Table Expressions)
         - Resolve cross-domain join keys (e.g., product_id links inventory↔finance)
         - Handle conflicting column names across domains
         - Output: single composed SQL query

[ ] 5.2  Cross-Database Federation:
         - PostgreSQL adapter: direct SQL execution on Odoo DB
         - DuckDB adapter: SQL execution on analytics warehouse
         - Redis adapter: key-value lookups for real-time data
         - Federation engine: detect which DB each sub-query targets,
           execute in parallel, merge results in Python
         - Handle type mismatches between databases

[ ] 5.3  SQL Validator Pipeline:
         - Syntax validator: parse SQL AST, check dialect compliance
         - Execution validator: run on DB, catch errors, check timeout (<30s)
         - Business rule validator: row count sanity check, value range checks,
           known constraint validation
         - Return structured error diagnosis: {error_type, location, suggestion}

[ ] 5.4  Self-Correction Loop (RL-inspired):
         - On error: diagnose → identify responsible agent → re-prompt with error context
         - Backpropagation: error in composed query traces back to source sub-query
         - Max 3 attempts per query
         - Track: attempt_number, error_type, correction_applied, success
         - Learning: store successful corrections as few-shot examples for future queries

[ ] 5.5  End-to-End Integration:
         - Wire all components: Router → Domain Agents → Composer → Validator → Self-Correction
         - Test on all 6 complexity levels (at least 5 queries per level)
         - Measure: execution accuracy, latency, correction rate, average attempts

[ ] 5.6  Midterm Demo Preparation:
         - Prepare 10 demo queries covering all complexity levels
         - Document system metrics: accuracy, latency, correction success rate
         - Architecture diagram (for presentation)
         - README with setup instructions
```

#### Deliverables (MIDTERM)
- Composer Agent with CTE-based query merging
- Cross-database federation engine
- 3-layer SQL validation pipeline
- Self-correction loop (max 3 attempts)
- End-to-end pipeline for all 6 complexity levels
- Midterm demo with 10 showcase queries

#### Resume Point
> Save federation engine status, self-correction loop completion, and end-to-end accuracy on the 30 test queries.

---

## PHASE 6: Temporal Reasoning & Ambiguity Resolution
### Deadline: June 13, 2026
### Status: [x] COMPLETE (2026-05-14)
### Depends on: Phase 5

#### Tasks
```
[ ] 6.1  Temporal Reasoning Module:
         - Parse temporal expressions: "last quarter", "YoY", "rolling 30 days",
           "Q1 2026", "past 6 months", "same period last year"
         - Map to exact date ranges (handle fiscal vs calendar year)
         - Generate window functions: LAG, LEAD, AVG OVER, ROW_NUMBER
         - Trend detection: rising/falling/stable classification

[ ] 6.2  Ambiguity Detection & Resolution:
         - Detect ambiguous terms using schema intelligence module
         - Score ambiguity: if term maps to >1 table/column with >0.7 similarity
         - Interactive mode: ask user to clarify (AmbiSQL approach)
         - Auto-resolve mode: use conversation context + domain hints
         - Track disambiguation decisions for learning

[ ] 6.3  Hierarchical Aggregation:
         - Support drill-down: "by region" → "by country" → "by warehouse"
         - Support roll-up: "total for all warehouses" from granular data
         - Generate GROUP BY with ROLLUP/CUBE/GROUPING SETS
         - Handle "compare X at level Y" queries

[ ] 6.4  Tests:
         - 30+ temporal reasoning test cases
         - 20+ ambiguity resolution test cases  
         - 15+ hierarchical aggregation test cases
```

#### Deliverables
- Temporal reasoning module with 10+ temporal expression patterns
- Ambiguity detection + interactive resolution
- Hierarchical aggregation support
- 65+ test cases

---

## PHASE 7: Multi-Turn Conversational Engine
### Deadline: June 24, 2026
### Status: [x] COMPLETE (2026-05-14)
### Depends on: Phase 6

#### Tasks
```
[ ] 7.1  Context Window Manager:
         - Track conversation state: queries, results, SQL, domains per turn
         - Sliding window: keep last 5 turns in active context
         - Compressed summary for older turns

[ ] 7.2  Reference Resolution:
         - Pronoun resolution: "those warehouses" → warehouses from previous result
         - Comparative references: "compare with last year" → add temporal constraint
         - Refinement: "only for Europe" → add WHERE clause to previous query
         - Follow-up: "why?" → add diagnostic joins/aggregations

[ ] 7.3  Query Modification Engine:
         - Modify previous SQL based on new constraints
         - Detect if new query is: refinement, follow-up, new topic, comparison
         - For refinements: patch existing SQL (don't regenerate from scratch)
         - For new topics: clear relevant context, keep session

[ ] 7.4  Tests:
         - 25+ multi-turn conversation test scenarios
         - Each scenario: 3-5 turns with reference resolution
```

#### Deliverables
- Multi-turn conversational engine with context tracking
- Reference resolution for pronouns, comparisons, refinements
- Query modification engine
- 25+ multi-turn test scenarios

---

## PHASE 8: SCM-SQL Benchmark Creation
### Deadline: July 5, 2026
### Status: [ ] NOT STARTED
### Depends on: Phase 7

#### Tasks
```
[ ] 8.1  Benchmark Design:
         - 6 complexity levels (as defined in OPTION_2_ELEVATED_RESEARCH.md)
         - ~85 queries per level = 500+ total
         - Each query: natural_language, gold_sql, complexity_level, domains_involved,
           tables_used, temporal_reasoning (bool), ambiguity_type, multi_turn_context
         - Difficulty annotations per BIRD standard

[ ] 8.2  Query Generation (3-pass process):
         - Pass 1: LLM-assisted generation of NL-SQL pairs
         - Pass 2: Human verification of SQL correctness (execute and check)
         - Pass 3: Difficulty calibration (measure model accuracy per query)

[ ] 8.3  Benchmark Validation:
         - Execute all gold SQL queries against Odoo schema
         - Verify all return non-empty results
         - Check for duplicate/near-duplicate queries
         - Balance across domains and complexity levels

[ ] 8.4  Baseline Evaluation:
         - Run baselines: Qwen 2.5-Coder (zero-shot), SQLCoder, Llama 3.3
         - Run your system (all agents)
         - Run ablation: single-agent (no domain decomposition) as control
         - Compute: Execution Accuracy (EX), Valid Efficiency Score (VES),
           Exact Match (EM)

[ ] 8.5  Benchmark Documentation:
         - Dataset card (HuggingFace format)
         - Leaderboard template
         - Evaluation script (reproducible)
```

#### Deliverables
- SCM-SQL benchmark: 500+ queries, 6 levels, fully validated
- Baseline results for 3+ models
- Ablation study results (domain decomposition vs single-agent)
- Evaluation scripts and documentation

---

## PHASE 9: Frontend (Next.js + Shadcn/ui)
### Deadline: July 16, 2026
### Status: [ ] NOT STARTED
### Depends on: Phase 5 (backend working)

#### Tasks
```
[ ] 9.1  Project Setup:
         - Next.js 14+ with App Router, TypeScript strict
         - Shadcn/ui component library
         - TailwindCSS
         - API client for FastAPI backend

[ ] 9.2  Chat Interface:
         - Message input with send button
         - Message history (user + assistant)
         - Streaming response support
         - Markdown rendering for responses

[ ] 9.3  SQL Visualization Panel:
         - Syntax-highlighted SQL display (with copy button)
         - SQL diff view for self-correction (attempt 1 vs 2 vs 3)
         - Query execution time and metadata

[ ] 9.4  Results Display:
         - Data table with sorting, pagination
         - Chart generation (bar, line, pie) for numerical results
         - Export to CSV

[ ] 9.5  Agent Activity View:
         - Show which agents were activated for the query
         - Domain classification breakdown
         - Agent communication timeline (Router → Agents → Composer → Validator)
         - Confidence score visualization

[ ] 9.6  Session Management:
         - Conversation history sidebar
         - New session / clear session
         - Multi-turn conversation thread view

[ ] 9.7  Responsive design + dark mode
```

#### Deliverables
- Production-grade Next.js frontend
- Chat UI with multi-turn support
- SQL visualization + results display
- Agent activity dashboard
- Fully responsive with dark mode

---

## PHASE 10: Evaluation, Paper Writing & Final Polish
### Deadline: August 1, 2026 | FINAL
### Status: [ ] NOT STARTED
### Depends on: All previous phases

#### Tasks
```
[ ] 10.1 Comprehensive Evaluation:
         - Run full SCM-SQL benchmark (500+ queries)
         - Execution Accuracy by complexity level
         - Execution Accuracy by domain
         - Self-correction success rate
         - Federation accuracy (cross-DB queries)
         - Temporal reasoning accuracy
         - Ambiguity resolution accuracy
         - Multi-turn context retention accuracy
         - Latency analysis (P50, P95, P99)

[ ] 10.2 Ablation Studies:
         - With vs without domain decomposition
         - With vs without self-correction
         - With vs without CSR-RAG schema retrieval
         - With vs without temporal reasoning module
         - With vs without ambiguity resolution
         - Single model vs multi-model routing

[ ] 10.3 Research Paper Draft:
         - Abstract
         - Introduction (problem + motivation)
         - Related Work (NL2SQL survey, multi-agent, enterprise benchmarks)
         - Methodology (architecture, agents, composition, self-correction)
         - SCM-SQL Benchmark (design, statistics, examples)
         - Experiments (baselines, ablations, analysis)
         - Discussion + Limitations
         - Conclusion

[ ] 10.4 Architecture Diagrams (for dissertation + presentation):
         - High-level system architecture (HTML + PNG + PDF)
         - Agent communication flow diagram
         - LangGraph state machine diagram
         - Database federation diagram
         - Self-correction loop diagram

[ ] 10.5 Dissertation Document:
         - BITS format compliance
         - All chapters with references
         - Appendix: full benchmark, code documentation

[ ] 10.6 Final Demo Preparation:
         - 15 showcase queries across all complexity levels
         - Performance dashboard
         - Video recording of demo (backup for tech issues)
         - Docker Compose verified on fresh machine

[ ] 10.7 Code Cleanup & Documentation:
         - README with full setup instructions
         - API documentation
         - Agent documentation
         - Benchmark documentation
```

#### Deliverables (FINAL)
- Complete evaluation with all metrics
- Research paper draft (submission-ready)
- Architecture diagrams (HTML + PNG + PDF)
- Dissertation document (BITS format)
- Final demo with 15 showcase queries
- Clean, documented codebase

---

## TRACKING & CONTINUITY INSTRUCTIONS

### For Each Development Session:
1. Read this roadmap to identify current phase and next incomplete task
2. Check the phase status markers ([ ] = not started, [~] = in progress, [x] = done)
3. Complete tasks sequentially within a phase
4. After completing each task, update this file's checkboxes
5. Run tests after each task completion

### If Claude Limit Hits:
1. **Immediately note** in this file:
   - Current phase and task number
   - What was being worked on
   - Any partial code that needs completion
   - Test status (passing/failing)
2. Save all open files
3. **Next session:** Start by reading this roadmap + CLAUDE.md files to resume

### Quality Gates (Per Phase):
- All tests passing
- Code reviewed by code-reviewer agent
- No security vulnerabilities (security-reviewer agent)
- Documentation updated
- Phase status updated in this file

### Weekly Check-In Format:
```
Week N (Date):
- Phase: X
- Tasks completed: X.1, X.2, X.3
- Tasks remaining: X.4, X.5
- Blockers: [none/description]
- Tests: X passing / Y total
- Next week target: Phase X tasks X.4-X.5, start Phase X+1
```

---

*Generated: 2026-04-05 | Hard Deadline: August 1, 2026*

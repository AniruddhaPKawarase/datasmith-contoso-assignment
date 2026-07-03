# ELEVATED Option 2: Enterprise-Scale Multi-Agent NL-to-SQL for International Supply Chain Intelligence

## Document Version: 1.0 | Date: 2026-04-05

---

## WHY THE ORIGINAL OPTION WAS TOO LINEAR

A basic multi-agent NL-to-SQL system that queries a single database is an **engineering project, not a research dissertation**. Real enterprises like Amazon, Walmart, and Alibaba operate across:

- **600+ database tables** across multiple schemas (Odoo ERP has ~600 tables)
- **Polyglot databases** (PostgreSQL + MongoDB + Redis + Elasticsearch)
- **Multi-region** data with currency conversion, tax rules, compliance
- **Temporal reasoning** (YoY, rolling averages, trend detection, forecasting)
- **5-10 table joins** for a single KPI query
- **Cross-database federation** (finance DB + inventory DB + logistics DB)

**The gap:** GPT-4o achieves only **10.1%** accuracy on Spider 2.0 (enterprise-scale). SOTA drops to **39.1%** on BIRD-Ent (4,000+ column schemas). No existing system handles domain-aware multi-agent decomposition for supply chain NL-to-SQL.

---

## THE ELEVATED PROJECT

### Title Options (Pick One for BITS Submission)

1. **"Domain-Aware Multi-Agent Natural Language to SQL Framework for Enterprise Supply Chain Intelligence"**

2. **"Multi-Agent Federated NL-to-SQL with Domain-Specific Specialists for International Supply Chain Analytics"**

3. **"Towards Enterprise-Scale Natural Language Database Querying: A Multi-Agent Approach with Domain Decomposition and Self-Correction for Supply Chain Management"**

### One-Line Summary
A multi-agent system where **domain-specialist agents** (Inventory, Logistics, Finance, Demand, Compliance) collaboratively generate, compose, validate, and self-correct complex SQL queries across **federated enterprise databases** (600+ tables, multi-schema, multi-dialect), evaluated on real supply chain scenarios with temporal reasoning, cross-database joins, and ambiguity resolution.

---

## WHAT MAKES THIS RESEARCH-WORTHY (Not Just Engineering)

### The Research Gap (Backed by Papers)

| What Exists | What's Missing (Your Contribution) |
|-------------|-------------------------------------|
| MAC-SQL, MARS-SQL decompose by **SQL structure** (schema linking → generation → validation) | Decomposition by **business domain** (inventory vs finance vs logistics) is **unexplored** |
| Spider, BIRD benchmarks use **single databases** | Real supply chain queries span **multiple databases** (finance + inventory + logistics) |
| Ambiguity resolution works for **single questions** (AmbiSQL, Odin) | Ambiguity in **supply chain domain** ("lead time" = procurement vs manufacturing vs delivery) is unaddressed |
| Temporal reasoning is a **known open problem** (NL2SQL survey 2025) | Supply chain queries are **inherently temporal** (YoY, rolling averages, forecasts) -- no benchmark targets this |
| Enterprise benchmarks (Spider 2.0, BIRD-Ent) exist | **No NL-to-SQL benchmark targets supply chain specifically** |

### Novel Research Contributions

1. **Domain-Aware Agent Decomposition**: First system to decompose NL queries by business domain rather than SQL structure
2. **Cross-Database Composition**: Agents generate sub-queries for different databases, a Composer merges them
3. **Supply Chain NL-to-SQL Benchmark**: First benchmark with realistic supply chain queries over enterprise-scale schemas
4. **Temporal Reasoning Module**: Specialized handling of YoY, rolling averages, fiscal calendars, trend detection
5. **Self-Correcting RL Loop**: Reinforcement learning from execution feedback (MARS-SQL inspired)

---

## ARCHITECTURE: Multi-Agent Supply Chain NL-to-SQL

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                                │
│            (Natural Language Query + Context + Role)                 │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 1: QUERY UNDERSTANDING                      │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐        │
│  │ Intent       │  │ Ambiguity    │  │ Temporal           │        │
│  │ Classifier   │  │ Detector     │  │ Reasoning Module   │        │
│  │              │  │ (AmbiSQL)    │  │                    │        │
│  │ Classifies   │  │ Detects      │  │ Maps "last quarter"│        │
│  │ domain(s):   │  │ ambiguous    │  │ → exact dates,     │        │
│  │ inventory,   │  │ terms, asks  │  │ fiscal calendars,  │        │
│  │ logistics,   │  │ user to      │  │ rolling windows    │        │
│  │ finance,     │  │ clarify      │  │                    │        │
│  │ demand,      │  │              │  │                    │        │
│  │ compliance   │  │              │  │                    │        │
│  └──────────────┘  └──────────────┘  └────────────────────┘        │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 LAYER 2: DOMAIN-SPECIFIC AGENTS                      │
│                                                                      │
│  Each agent has:                                                     │
│  - Schema knowledge (only its domain tables)                         │
│  - Business glossary (domain-specific terms)                         │
│  - SQL dialect expertise (for its target database)                   │
│  - Example query pairs (few-shot learning)                           │
│                                                                      │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐       │
│  │ INVENTORY  │ │ LOGISTICS  │ │ FINANCE    │ │ DEMAND     │       │
│  │ AGENT      │ │ AGENT      │ │ AGENT      │ │ AGENT      │       │
│  │            │ │            │ │            │ │            │       │
│  │ Tables:    │ │ Tables:    │ │ Tables:    │ │ Tables:    │       │
│  │ stock_move │ │ shipment   │ │ account_   │ │ forecast   │       │
│  │ stock_quant│ │ transport_ │ │ move_line  │ │ sale_order │       │
│  │ stock_     │ │ lane       │ │ currency_  │ │ time_series│       │
│  │ warehouse  │ │ carrier    │ │ rate       │ │ product_   │       │
│  │ stock_     │ │ tracking   │ │ cost_center│ │ trend      │       │
│  │ location   │ │ customs    │ │ tax_rule   │ │            │       │
│  │ product    │ │            │ │            │ │            │       │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘       │
│        │              │              │              │               │
│  ┌─────┴──────────────┴──────────────┴──────────────┴─────┐        │
│  │                  COMPLIANCE AGENT                       │        │
│  │  (Cross-cutting: RBAC, data isolation, audit logging)   │        │
│  └────────────────────────────────────────────────────────┘        │
└─────────────────────┬───────────────────────────────────────────────┘
                      │ Sub-queries from each domain agent
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│               LAYER 3: COMPOSITION & FEDERATION                      │
│                                                                      │
│  ┌────────────────────────────────────────────────────────┐         │
│  │              COMPOSER AGENT                             │         │
│  │                                                         │         │
│  │  - Merges sub-queries via CTEs/subqueries              │         │
│  │  - Resolves cross-domain join keys                      │         │
│  │  - Handles multi-database federation                    │         │
│  │  - Currency conversion injection                        │         │
│  │  - Dialect translation (PostgreSQL ↔ MySQL ↔ DuckDB)   │         │
│  └────────────────────────────────────────────────────────┘         │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│              LAYER 4: VALIDATION & SELF-CORRECTION                   │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐          │
│  │ SYNTAX       │  │ EXECUTION    │  │ BUSINESS RULE    │          │
│  │ VALIDATOR    │  │ VALIDATOR    │  │ VALIDATOR        │          │
│  │              │  │              │  │                  │          │
│  │ Parse tree   │  │ Run on DB,   │  │ Check: row count │          │
│  │ validation,  │  │ check errors,│  │ reasonable?      │          │
│  │ dialect      │  │ timeout,     │  │ Totals add up?   │          │
│  │ compliance   │  │ result shape │  │ Known constraints│          │
│  └──────────────┘  └──────────────┘  └──────────────────┘          │
│                                                                      │
│  ┌────────────────────────────────────────────────────────┐         │
│  │              SELF-CORRECTION LOOP (RL)                   │         │
│  │                                                         │         │
│  │  Error detected → Diagnose → Route back to             │         │
│  │  responsible agent → Re-generate → Re-validate          │         │
│  │  Max 3 attempts (backpropagation)                       │         │
│  │  RL reward = execution success + result quality          │         │
│  └────────────────────────────────────────────────────────┘         │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│             LAYER 5: RESPONSE & EXPLANATION                          │
│                                                                      │
│  - Generated SQL (formatted, commented)                              │
│  - Query execution results (table/chart)                             │
│  - Natural language explanation of what the query does               │
│  - Confidence score                                                  │
│  - Data lineage: which databases/tables were queried                 │
│  - Audit trail for compliance                                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## COMPLEXITY DIMENSIONS (Amazon/Enterprise Scale)

### Dimension 1: Enterprise Schema Scale (600+ Tables)
- Use **Odoo ERP** open-source database (~600 tables in PostgreSQL)
- Realistic stock, purchasing, sales, accounting, manufacturing modules
- Domain-specific abbreviated column names (real-world challenge)

### Dimension 2: Multi-Database Federation
- **PostgreSQL** (Odoo ERP: inventory, purchasing, sales, accounting)
- **DuckDB** (analytics warehouse: historical aggregations, TPC-DS style)
- **Redis** (real-time: live inventory levels, cache)
- Queries that span all three databases

### Dimension 3: Temporal Reasoning
- Year-over-year comparisons
- Rolling 30/60/90-day averages
- Fiscal vs calendar year handling
- Trend detection (rising/falling demand)
- Forecasting queries (next 2 weeks stockout risk)

### Dimension 4: Hierarchical Aggregation
- Company → Region → Country → Warehouse → Zone → Shelf
- Drill-down and roll-up in natural language
- "Show me inventory by region" vs "Show me inventory for Warehouse X, Shelf 3"

### Dimension 5: Cross-Domain Joins (5-10 Tables)
- Total landed cost = product cost + shipping + customs + warehousing + currency conversion
- Supplier performance = lead time + defect rate + cost + delivery reliability
- Inventory health = current stock + safety stock policy + demand forecast + inbound orders

### Dimension 6: Ambiguity Resolution
- "Lead time" = procurement (vendor → warehouse) vs manufacturing (raw → finished) vs delivery (warehouse → customer)
- "Sales" = sale_order vs account_move_line vs pos_order
- "Cost" = product cost vs landed cost vs total cost of ownership
- Interactive disambiguation when context is insufficient

### Dimension 7: Access Control & Multi-Tenancy
- Row-level security based on user role (warehouse manager sees only their warehouse)
- Generated SQL includes appropriate WHERE clauses for data isolation
- Audit logging of all queries for compliance

### Dimension 8: Self-Correction with RL
- MARS-SQL style reinforcement learning from execution feedback
- Error diagnosis → route to responsible agent → re-generate → re-validate
- Max 3 attempts with backpropagation
- RL reward = execution success + result quality + query efficiency

---

## REAL-WORLD QUERY EXAMPLES (Increasing Complexity)

### Level 1: Single Domain, Single Table (Easy)
**Query:** "How many units of Product X are in stock?"
**SQL:** Simple SELECT with WHERE on stock_quant
**Tables:** 1-2

### Level 2: Single Domain, Multi-Table (Medium)
**Query:** "Which warehouses have stock levels below safety stock for any product?"
**SQL:** JOIN stock_quant + stock_warehouse + product + inv_policy, WITH HAVING clause
**Tables:** 3-4

### Level 3: Cross-Domain, Multi-Table (Hard)
**Query:** "Compare supplier lead times vs defect rates across all Asian suppliers for Q1 2026"
**SQL:** JOIN purchase_order + res_partner (suppliers) + stock_picking + quality tables + res_country, with temporal filtering and aggregation
**Tables:** 5-7
**Challenges:** Temporal reasoning (Q1 dates), geographic filtering, cross-domain (procurement + quality)

### Level 4: Cross-Database Federation (Very Hard)
**Query:** "What's the total landed cost for Product X across all markets including customs, shipping, and warehousing?"
**SQL:** Sub-queries across PostgreSQL (product cost, warehousing) + DuckDB (historical shipping rates) + currency conversion
**Tables:** 7-10 across 2 databases
**Challenges:** Multi-database, multi-currency, aggregation across hierarchies

### Level 5: Predictive/Strategic (Expert)
**Query:** "If Supplier X has a 2-week disruption, which products are at risk and what's the estimated revenue impact?"
**SQL:** Recursive BOM traversal + inventory analysis + demand forecasting + revenue projection
**Tables:** 10+ across multiple databases
**Challenges:** Scenario modeling, graph traversal (BOM), temporal forecasting, cross-database

### Level 6: Conversational Multi-Turn (Research Frontier)
**Turn 1:** "Show me inventory turnover by warehouse for last quarter"
**Turn 2:** "Now compare that with the same quarter last year"
**Turn 3:** "Which warehouses had the biggest decline? Why?"
**Turn 4:** "For those warehouses, show me supplier lead time trends"
**Challenges:** Context tracking across turns, pronoun resolution, progressive query refinement

---

## KEY RESEARCH PAPERS

### Multi-Agent NL-to-SQL
| Paper | Venue | Key Innovation | Link |
|-------|-------|----------------|------|
| MARS-SQL | Nov 2025 | Multi-agent RL with Grounding + Generation + Validation | https://arxiv.org/abs/2511.01008 |
| MAC-SQL | COLING 2025 | Selector + Decomposer + Refiner agents | https://aclanthology.org/2025.coling-main.36.pdf |
| SQL-of-Thought | Sep 2025 | Schema linking → subproblem → query plan → error correction | https://arxiv.org/abs/2509.00581 |
| MTSQL-R1 | Oct 2025 | MDP for multi-turn; propose-execute-verify-refine | https://arxiv.org/abs/2510.12831 |
| SKYRL-SQL | 2026 | Multi-turn SQL via RL (UC Berkeley) | Latest advancement |
| AgentiQL | Oct 2025 | Multi-expert with adaptive router | https://arxiv.org/html/2510.10661 |
| CHASE-SQL | ICLR 2025 | Multi-path reasoning + preference optimization | https://proceedings.iclr.cc |

### Enterprise-Scale Challenges
| Paper | Venue | Key Finding | Link |
|-------|-------|-------------|------|
| NL2SQL is Not Solved | CIDR 2024 (Microsoft) | Enterprise ambiguity, complex schemas unsolved | https://www.cidrdb.org/cidr2024/papers/p74-floratou.pdf |
| Enterprise Benchmarks | OpenReview 2025 | SOTA drops to 39.1% on BIRD-Ent | https://openreview.net/forum?id=gXkIkSN2Ha |
| Spider 2.0 | ICLR 2025 Oral | GPT-4o at 10.1% on enterprise SQL | https://arxiv.org/abs/2411.07763 |
| CSR-RAG | Jan 2026 | Hybrid retrieval for enterprise schemas | https://arxiv.org/abs/2601.06564 |
| TAG (Table Augmented Generation) | CIDR/VLDB 2025 | Text-to-SQL is not enough; need LLM reasoning | https://arxiv.org/abs/2408.14717 |
| NL2SQL Survey | VLDB 2025 | Comprehensive state of art + open problems | https://www.vldb.org/pvldb/vol18/p5466-luo.pdf |

### Ambiguity & Self-Correction
| Paper | Venue | Key Innovation | Link |
|-------|-------|----------------|------|
| AmbiSQL | 2025 | Interactive ambiguity resolution (75% → 100% on ambiguous) | https://arxiv.org/abs/2508.15276 |
| Odin | 2025 | User feedback-based schema disambiguation (1.5-2x improvement) | https://arxiv.org/abs/2505.19302 |
| ReFoRCE | 2025 | Column exploration for complex schemas | https://arxiv.org/abs/2502.00675 |

### Supply Chain + AI
| Paper | Venue | Key Contribution | Link |
|-------|-------|------------------|------|
| Agentic LLMs in Supply Chain | Int. J. Production Research 2025 | Multi-agent consensus for SCM decisions | https://www.tandfonline.com/doi/full/10.1080/00207543.2025.2604311 |
| Hybrid Agentic NL2SQL | Thesis 2025 | Schema-aware agent decomposition | https://cornerstone.lib.mnsu.edu/cgi/viewcontent.cgi?article=2540&context=etds |

---

## OPEN-SOURCE STACK (100% Open Source)

### Core LLMs (No Paid APIs)
| Model | Size | Strength | License |
|-------|------|----------|---------|
| **Qwen 2.5-Coder** | 7B/14B | 81.7% on Spider (best open-source for SQL) | Qwen License (permissive) |
| **DeepSeek-Coder-V2** | 16B/236B | Strong SQL generation | DeepSeek License |
| **Llama 3.3** | 8B/70B | General reasoning + instruction following | Llama 3 Community |
| **Mistral/Mixtral** | 7B/8x7B | Fast inference, good for routing | Apache 2.0 |
| **CodeLlama** | 7B/13B/34B | SQL-specific fine-tuning baseline | Llama 2 Community |
| **SQLCoder** (Defog) | 8B/70B | 93% accuracy (70B), purpose-built for SQL | Apache 2.0 |

### Inference & Fine-Tuning
| Tool | Purpose | License |
|------|---------|---------|
| **vLLM** | Production inference (PagedAttention, continuous batching) | Apache 2.0 |
| **Ollama** | Development/local inference | MIT |
| **Unsloth** | 2x faster LoRA fine-tuning, 60% less memory | Apache 2.0 |
| **PEFT** (HuggingFace) | LoRA/QLoRA parameter-efficient fine-tuning | Apache 2.0 |

### Agent Orchestration
| Tool | Purpose | License |
|------|---------|---------|
| **LangGraph** | Multi-agent orchestration with state machines | MIT |
| **CrewAI** | Agent roles, goals, backstories | MIT |
| **LlamaIndex** | RAG pipeline + tool integration | MIT |

### Databases
| Database | Purpose | License |
|----------|---------|---------|
| **PostgreSQL** | Primary ERP database (Odoo schema) | PostgreSQL License (permissive) |
| **DuckDB** | Analytics warehouse (columnar, in-process) | MIT |
| **Redis** | Real-time cache (live inventory levels) | BSD |
| **Odoo** | Open-source ERP with ~600 table schema | LGPL |

### Evaluation & Monitoring
| Tool | Purpose | License |
|------|---------|---------|
| **RAGAS** | RAG evaluation metrics | Apache 2.0 |
| **MLflow** | Experiment tracking | Apache 2.0 |
| **DeepEval** | LLM evaluation framework | Apache 2.0 |
| **Prometheus + Grafana** | System monitoring | Apache 2.0 |

### Frontend
| Tool | Purpose | License |
|------|---------|---------|
| **Streamlit** | Quick demo UI | Apache 2.0 |
| **Gradio** | Interactive API demo | Apache 2.0 |
| **Next.js** | Production frontend | MIT |
| **Shadcn/ui** | UI components | MIT |

### Deployment
| Tool | Purpose | License |
|------|---------|---------|
| **Docker + Docker Compose** | Containerization | Apache 2.0 |
| **Coolify** | Self-hosted deployment platform (Vercel alternative) | Apache 2.0 |
| **Nginx** | Reverse proxy / API gateway | BSD |
| **GitHub Actions** | CI/CD | Free for open source |

---

## DATASETS & BENCHMARKS

### For Training & Evaluation
| Dataset | Tables | Queries | Domain | Link |
|---------|--------|---------|--------|------|
| **BIRD** | 95 DBs, 37 domains | 12,751 pairs | Cross-domain | https://bird-bench.github.io/ |
| **Spider 2.0** | Cloud-scale | 632 workflows | Enterprise | https://github.com/xlang-ai/Spider2 |
| **BIRD-Ent** | 4,000+ columns | Enterprise-scale | Enterprise | https://openreview.net/forum?id=gXkIkSN2Ha |
| **TPC-DS** | 24 tables (snowflake) | 99 complex queries | Retail/Supply Chain | Standard benchmark |
| **TPC-H** | 8 tables | 22 queries | Wholesale Supply Chain | Standard benchmark |
| **EHRSQL** | Clinical schema | Hospital staff queries | Healthcare | https://github.com/glee4810/EHRSQL |

### Supply Chain Specific Data
| Dataset | Description | Link |
|---------|-------------|------|
| **DataCo Smart Supply Chain** | 180K+ rows, 50+ columns, orders/shipping/fraud | https://www.kaggle.com/datasets/shashwatwork/dataco-smart-supply-chain-for-big-data-analysis |
| **Global Product Inventory 2025** | Multi-region inventory levels | https://www.kaggle.com/datasets/keyushnisar/global-product-inventory-dataset-2025 |
| **Odoo Demo Database** | ~600 tables, full ERP schema | Install Odoo with demo data |
| **AWS Supply Chain Data Model** | 45 entities, 11 modules (gold standard reference) | https://docs.aws.amazon.com/aws-supply-chain/latest/userguide/data-model-asc.html |

### Your Novel Benchmark Contribution
Create **SCM-SQL**: A supply chain NL-to-SQL benchmark with:
- 500+ query pairs across 6 complexity levels
- Based on Odoo ERP schema (~600 tables)
- Covers all 8 complexity dimensions
- Multi-turn conversational queries
- Temporal reasoning test suite
- Cross-domain join test suite
- Ambiguity resolution test suite

---

## COMPANIES BUILDING THIS (Market Validation)

| Company | What They Do | Gap You Fill |
|---------|-------------|--------------|
| **Snowflake Cortex Analyst** | Single-database NL-to-SQL with semantic views | No multi-database federation |
| **ThoughtSpot** ($800M+ funded) | Search-first BI with AI agent | Proprietary, no domain-specific agents |
| **TextQL** ($4.1M+) | Connects to existing BI tools | No multi-agent architecture |
| **Vanna AI** (open source) | Agentic NL-to-SQL with RBAC | No domain decomposition |
| **Defog/SQLCoder** | Purpose-built SQL models | No multi-agent, no supply chain focus |
| **Salesforce Horizon** | Slack-based text-to-SQL | Consensus approach, not domain-specialist |
| **Swiggy Hermes V3** | Conversational AI analyst (54% → 93%) | Single-domain (food delivery) |

**Market size:** NLP market $36-49B (2025) → $64-114B (2029). Data analytics $132.9B by 2026. 65% of organizations adopting AI for analytics.

---

## PUBLICATION VENUES

| Venue | Tier | Relevance | Deadline (typical) |
|-------|------|-----------|-------------------|
| **ACL** | A* | NLP flagship | Jan/Feb |
| **EMNLP** | A* | NLP + applied | May/Jun |
| **COLING** | A | NLP (MAC-SQL published here) | Jul |
| **ICLR** | A* | ML (CHASE-SQL, Spider 2.0 published here) | Sep/Oct |
| **VLDB** | A* | Databases (NL2SQL survey published here) | Mar |
| **SIGMOD** | A* | Databases | Jul |
| **NAACL** | A | NLP regional | Dec/Jan |
| **AAAI** | A* | AI broad | Aug/Sep |

---

*All tools verified as 100% open-source. No paid API dependencies for core functionality.*
*Generated: 2026-04-05*

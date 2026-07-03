# Project Decisions & Clarifications Log
## Domain-Aware Multi-Agent NL-to-SQL for Enterprise Supply Chain Intelligence

### Date: 2026-04-05 | Status: Pre-Development

---

## FINALIZED DECISIONS

### 1. Project Title
**"Domain-Aware Multi-Agent Natural Language to SQL Framework for Enterprise Supply Chain Intelligence"**

### 2. LLM Strategy
- **Primary:** OpenRouter API (free tier) for Qwen 2.5-Coder, DeepSeek, Llama, GPT-OSS models
- **Fallback:** Ollama for offline/local inference (2nd priority)
- **Design principle:** Minimize LLM dependency. Use LLMs only where essential (SQL generation, intent classification, ambiguity resolution). Use rule-based/deterministic approaches wherever possible (SQL validation, schema linking, temporal parsing).
- **Architecture:** Abstract LLM provider behind a unified interface so switching between OpenRouter/Ollama is a config change.

### 3. Database Setup
- **Method:** Docker (Odoo + PostgreSQL containers)
- **Schema:** Odoo ERP (~600 tables) as primary enterprise schema
- **Analytics DB:** DuckDB for historical aggregations and federation testing
- **Real-time cache:** Redis for live inventory levels
- **Additional data:** DataCo Smart Supply Chain (180K+ rows, Kaggle) + Global Inventory 2025 loaded into DuckDB

### 4. Scope
- **All 8 complexity dimensions** implemented:
  1. Enterprise Schema (600+ tables)
  2. Multi-DB Federation (PostgreSQL + DuckDB + Redis)
  3. Temporal Reasoning (YoY, rolling averages, fiscal calendars)
  4. Hierarchical Aggregation (Company→Region→Country→Warehouse→Shelf)
  5. Cross-Domain Joins (5-10 tables per query)
  6. Ambiguity Resolution (interactive disambiguation)
  7. Access Control (row-level security)
  8. Self-Correction with RL (MARS-SQL inspired, max 3 attempts)
- **Multi-turn conversational queries:** Built from day one (not phased later)

### 5. Frontend
- **Framework:** Next.js + Shadcn/ui
- **Features:** Chat interface, SQL visualization, query results (tables/charts), agent activity view, confidence scores, data lineage

### 6. Publication Target
- **Target:** Top venue (ACL / EMNLP / COLING / VLDB)
- **Benchmark:** SCM-SQL with 500+ query pairs across 6 complexity levels
- **Evaluation:** Rigorous -- ablation studies, baseline comparisons, statistical significance tests

### 7. Timeline
- **BITS Structure:**
  - **Outline Phase:** Architecture, roadmap, resources (current phase)
  - **Midterm:** At least 50% of development phases completed
  - **Final:** Complete project demonstration
- **Hard deadline:** 1st week of August 2026 (complete project)
- **Development window:** ~4 months (April 2026 - August 2026)

### 8. Deployment
- **Demo:** Local Docker on laptop (Docker Compose)
- **No cloud hosting needed** -- everything runs locally

### 9. Development Continuity
- Project must be resumable across Claude sessions
- Each phase must be clearly marked with completion status
- If Claude limit hits during development, document exact resume point
- All progress tracked via phase checklist

---

## USER STORY

**As** an MTech student building a dissertation project,
**I want** a production-grade multi-agent NL-to-SQL system for enterprise supply chain intelligence,
**So that** I can demonstrate novel research contributions (domain-aware agent decomposition, cross-DB federation, SCM-SQL benchmark) and publish at a top venue while completing my BITS Pilani MTech dissertation by August 2026.

### Acceptance Criteria
1. System handles all 8 complexity dimensions
2. 500+ query benchmark (SCM-SQL) with 6 levels
3. Multi-turn conversational support from day one
4. All 5 domain-specialist agents functional (Inventory, Logistics, Finance, Demand, Compliance)
5. Self-correction loop with max 3 attempts
6. Cross-database federation across PostgreSQL + DuckDB + Redis
7. Production-quality Next.js frontend with chat UI
8. Runs entirely on local Docker (laptop demo)
9. 100% open-source stack (OpenRouter API + Ollama fallback)
10. Publishable evaluation results with ablation studies

---

## OPEN ITEMS (None -- All Clarified)

All pre-development questions have been answered. Ready for Phase 2: Roadmap & Architecture.

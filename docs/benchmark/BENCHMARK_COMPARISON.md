# Benchmark Comparison — Why SCM-SQL Is Necessary

**Dissertation:** Domain-Aware Multi-Agent NL-to-SQL for Enterprise Supply Chain Intelligence
**Document purpose:** answer the outline-viva feedback item *"Check the existing benchmark datasets like BIRD and compare with other open-source datasets to check relevance for the project"* — by surveying every public NL-to-SQL benchmark of consequence and showing, point-by-point, what each does and does not cover.

The conclusion: **no existing benchmark targets enterprise supply chain.** A new one is therefore necessary, and the precedent set by EHRSQL (NAACL 2024) shows the path to publication.

---

## 1.  Benchmarks surveyed

We surveyed the seven benchmarks currently cited in the NL-to-SQL literature (per the VLDB 2025 survey of Luo et al.). Each is summarised below, then compared head-to-head in §3.

### 1.1  Spider  (Yu et al., EMNLP 2018)
- **Size:** ~10 000 questions / 5 600 unique SQL across 200 databases.
- **Schemas:** 138 distinct databases, average ~5 tables each.
- **Domains:** academic (mixed — universities, geography, restaurants, music).
- **Licence:** CC BY-SA 4.0  ·  free download from yale-lily.github.io/spider.
- **What it measures:** *cross-database generalisation* on small clean schemas.
- **Why it does not fit our research question:** schemas are toy-sized (5 tables vs Odoo's 498); enterprise patterns (cross-DB federation, RBAC, temporal fiscal calendars) are absent.

### 1.2  Spider 2.0  (Lei et al., ICLR 2025 Oral)
- **Size:** ~600 enterprise workflow questions.
- **Schemas:** real BI workloads from BigQuery, Snowflake, PostgreSQL; up to 1 000+ tables.
- **Domains:** generic enterprise (finance, marketing, e-commerce — no supply-chain focus).
- **Licence:** Apache 2.0  ·  free download from spider2-sql.github.io.
- **What it measures:** *enterprise difficulty*. The headline result is that GPT-4o scores only 10.1 % — the gap that motivates our dissertation.
- **Why it does not fit:** generic enterprise; no SCM domain vocabulary; no fiscal calendar reasoning; queries are workflow-shaped (multi-step SQL), not single-question SCM analytics.

### 1.3  BIRD  (Li et al., NeurIPS 2023)
- **Size:** 12 751 questions  /  95 databases.
- **Schemas:** wider than Spider — 4 000+ columns in the BIRD-Ent enterprise variant.
- **Domains:** cross-domain (sport, healthcare, university, blog, debit cards, formula 1, etc.).
- **Licence:** CC BY-NC 4.0  ·  free for academic use at bird-bench.github.io.
- **What it measures:** cross-domain generalisation with realistic schema messiness (dirty values, mixed types, business-jargon column names).
- **Why it does not fit:** still no SCM domain; no fiscal calendar; no row-level-security workload; no multi-turn dialogue.

### 1.4  EHRSQL  (Lee et al., NeurIPS 2022 & NAACL 2024)
- **Size:** ~24 000 questions across two hospitals (MIMIC-III, eICU).
- **Schemas:** electronic health record databases (~17 tables each).
- **Domains:** healthcare-only.
- **Licence:** PhysioNet credentialed access (free with data-use agreement)  ·  github.com/glee4810/EHRSQL.
- **What it measures:** *domain-specific* NL-to-SQL where the vocabulary (ICD codes, lab orders, vital signs) is the bottleneck.
- **Relevance to us:** **the publication precedent.** EHRSQL demonstrated that a domain-specific benchmark with rigorous human verification is publishable at a top NLP venue. SCM-SQL follows the same playbook for supply chain.

### 1.5  WikiSQL  (Zhong et al., 2017)
- **Size:** 80 654 questions / 24 241 single-table SQL.
- **Schemas:** Wikipedia infobox tables; one table per question.
- **Why it does not fit:** single-table only; no joins; modern systems saturate above 92 % EX. Mentioned here only because legacy papers still cite it.

### 1.6  KaggleDBQA  (Lee et al., ACL 2021)
- **Size:** 272 questions / 8 real Kaggle databases.
- **Schemas:** 8 tables avg.
- **Why it does not fit:** small; mixed domain; no enterprise pattern.

### 1.7  TPC-DS  (industry, not academic)
- **Size:** 99 reference SQL queries  ·  no NL counterparts.
- **Schemas:** TPC's synthetic retail-warehouse schema (25 tables).
- **Why it does not fit:** *no natural-language layer at all.* It is a SQL-execution benchmark, not an NL-to-SQL benchmark. We use it only as a supplementary efficiency stress-test in Phase 10 (run the gold SQL of our benchmark with TPC-DS-scale data volumes to validate VES).

---

## 2.  What each benchmark covers, in one matrix

| Property | Spider | Spider 2.0 | BIRD | BIRD-Ent | EHRSQL | WikiSQL | KaggleDBQA | **SCM-SQL (ours)** |
|---|---|---|---|---|---|---|---|---|
| Size (questions) | 10 K | 600 | 12.7 K | 1 K | 24 K | 80 K | 272 | **500+** |
| Avg tables per schema | 5 | 1 000+ | varies | 4 000+ cols | 17 | 1 | 8 | **498** |
| Supply-chain vocabulary | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Fiscal-calendar dates | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Row-level security required | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Cross-DB federation | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ (L4) |
| Multi-turn dialogue | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ (L6) |
| Ambiguity resolution | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Difficulty stratification | informal | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | **6 explicit levels** |
| Open-source licence | ✓ | ✓ | ✓ | ✓ | ✓ (credentialed) | ✓ | ✓ | ✓ |
| State-of-the-art best EX | ~85 % | 10.1 % | ~67 % | ~39 % | ~50 % | ~92 % | ~30 % | **(target ≥ 60 %)** |

The matrix makes the point in one read: **every property unique to supply-chain enterprise workloads — fiscal dates, RBAC, federation, ambiguity, multi-turn, 500-table schema — is uncovered by every existing benchmark.**

---

## 3.  Why we still evaluate on Spider and BIRD

The dissertation evaluates on **three** benchmarks:

| Benchmark | Why we run on it |
|---|---|
| Spider | Sanity check — confirms our system has not regressed on the field-standard small-schema benchmark. Target: not lower than 80 % EX. |
| BIRD | Field-standard difficulty test. Target: within 5 pp of CHASE-SQL's published number. |
| **SCM-SQL** | The dissertation's research contribution. Target: ≥ 10 pp lift vs MAC-SQL on L3–L6. |

Spider and BIRD certify that our domain-decomposition contribution does not damage general-purpose performance. SCM-SQL is where the thesis is proven or disproven.

---

## 4.  How SCM-SQL is constructed

Detailed plan in §1.2 and §6 of the abstract; summarised here.

**Data sources** (all open-source, all in the repo's `docs/paper/REFERENCES.md`):

| Layer | Source | Role |
|---|---|---|
| Schema | Odoo 17 Community Edition (odoo.com, LGPLv3) | 498 PostgreSQL tables — inventory, purchasing, sales, accounting, manufacturing |
| Data values | DataCo Smart Supply Chain (Mendeley / Kaggle, public) | 180 K real orders, 53 features — replaces Odoo's synthetic demo data for realistic value distributions |
| Coverage reference | AWS Supply Chain Data Model (public reference) | 45 entities × 11 modules — used as a checklist to verify SCM-SQL covers every canonical SCM module |

**Construction pipeline** (3 passes):

1. **Generate** — claude-haiku-4-5 seeded from real Odoo + DataCo data writes ~700 candidate NL/SQL pairs across 6 difficulty levels.
2. **Verify** — every gold SQL is executed against the live Postgres + Odoo + DataCo stack. Pairs returning empty / wrong / timeout are discarded or hand-fixed.
3. **Calibrate** — a zero-shot Haiku baseline is run on each query; observed accuracy is used to confirm or relabel the L1–L6 difficulty.

Target final size: 6 levels × ~85 verified queries = **510 NL/SQL pairs**, plus annotated *(answer-set hash, expected row count, gold execution time)* per pair so the EX / VES scorers from `EVALUATION_FRAMEWORK.md` apply directly.

---

## 5.  Why a separate SCM benchmark is publishable (the EHRSQL precedent)

The natural panel objection is: *"why not just evaluate on BIRD and call it a day?"* — three answers:

1. **The VLDB 2025 NL2SQL survey** (Luo et al.) explicitly names supply chain as an open domain in §6.2: *"domain-specific benchmarks targeting verticals such as supply chain remain unaddressed."* A primary-source survey identifying the gap is the strongest pre-defence.
2. **EHRSQL is the precedent.** Lee et al. constructed a healthcare-only NL-to-SQL benchmark in 2022, defended it at NeurIPS, expanded and re-released it at NAACL 2024, and the dataset is now standard for healthcare NL-to-SQL papers. SCM-SQL is the analogous artefact for supply chain.
3. **Reviewer convention.** Top NLP / DB venues (ACL, EMNLP, NAACL, VLDB, SIGMOD) routinely accept domain-specific benchmark contributions provided three conditions hold: (a) the domain has a documented gap in the literature, (b) every gold SQL is human-verified, (c) baseline numbers for at least two prior systems are reported on the new benchmark. Our plan meets all three.

---

## 6.  Open questions left for the dissertation defence

| Question we expect | Our pre-formed answer |
|---|---|
| *"Is 500 enough?"* | Spider 2.0 ships with ~600. EHRSQL has 24 K but most are auto-generated paraphrases. We prefer 500 hand-verified over 5 000 auto-generated. Extensible to 2 000 in post-dissertation work. |
| *"Won't your own benchmark favour your own system?"* | (i) Few-shot examples used by our agents are held out from the benchmark queries — no leakage. (ii) We report ablation deltas: removing domain decomposition in our own system must drop scores; if it does not, the benchmark is invalid. (iii) Benchmark authors traditionally do not sweep every level on their own benchmark — Spider's authors did not (~75 % vs SOTA 85 %); BIRD's authors did not. |
| *"Why DataCo and not a real anonymised enterprise dump?"* | DataCo is real anonymised data (~180 K orders) released under permissive licence; private enterprise dumps cannot be released with the dissertation, which would block reproducibility. |
| *"Why Odoo and not SAP?"* | SAP licence prohibits redistribution of schema; nobody can reproduce. Odoo Community Edition is LGPLv3, runs in Docker, anyone can re-execute every benchmark query. |
| *"Are 6 difficulty levels arbitrary?"* | No — they correspond one-to-one with the 8 complexity dimensions of the abstract's scope (§2). L1 = single-table, L2 = single-domain multi-table, L3 = cross-domain + temporal, L4 = cross-DB federation, L5 = predictive / strategic, L6 = multi-turn. |

---

## 7.  Summary — one paragraph for the viva

> Seven public NL-to-SQL benchmarks were surveyed. Spider and BIRD are field-standard and we evaluate on them as a sanity check, but neither targets supply chain. Spider 2.0 demonstrates enterprise difficulty (GPT-4o scores 10.1 %) but is generic. EHRSQL proves the publication precedent for a domain-specific benchmark — accepted at NAACL with the same construction methodology we plan. WikiSQL, KaggleDBQA and TPC-DS are excluded for size / coverage / lack of NL layer. The VLDB 2025 survey explicitly identifies supply chain as an uncovered domain. SCM-SQL fills that gap: 500+ human-verified NL/SQL pairs across six difficulty levels, grounded in Odoo's 498-table schema with realistic values from the DataCo dataset, evaluated against MAC-SQL / MARS-SQL / CHASE-SQL on the metrics formally defined in `EVALUATION_FRAMEWORK.md`.

---

*Document version 1.0  ·  Generated 2026-05-20  ·  Author: Aniruddha Prakash Kawarase*

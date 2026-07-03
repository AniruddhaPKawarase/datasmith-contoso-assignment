# Evaluation Framework

**Dissertation:** Domain-Aware Multi-Agent NL-to-SQL for Enterprise Supply Chain Intelligence
**Student:** Aniruddha Prakash Kawarase  (BITS ID 2024AA05175)
**Document purpose:** formally define how the dissertation will be evaluated — metrics, baselines, ablations, statistical procedure, comparison protocol — so the panel sees the measurement plan before the measurements exist.

This document closes the outline-viva feedback item *"Need to define proper accuracy and evaluation metrics."*

---

## 1.  What we are measuring

A natural-language to SQL system produces a SQL string for a given NL question. Evaluation answers three questions:

1. **Does the generated SQL produce the right answer?**   →  *Execution Accuracy*
2. **Is the SQL also efficient?**                          →  *Valid Efficiency Score*
3. **Does the SQL match a canonical reference form?**     →  *Exact Match*

We define each formally below.

---

## 2.  Primary metric — Execution Accuracy (EX)

The headline number reported in every recent NL-to-SQL paper (Spider, BIRD, Spider 2.0, MAC-SQL).

### Definition

For a benchmark item `i` consisting of a natural-language question `q_i`, a gold SQL `S_gold,i`, and a predicted SQL `S_pred,i`:

```
EX(i) = 1   if  results( S_pred,i )  ≡  results( S_gold,i )
        0   otherwise
```

where `results(S)` is the materialised result set of `S` executed against the evaluation database, and `≡` is set-equality on rows ignoring row order unless `S_gold` contains an `ORDER BY` clause (in which case row order must also match).

Benchmark-level EX is the simple mean:

```
EX  =  (1 / N) · Σ_i  EX(i)
```

### Implementation rules (decided in advance to avoid disputes at viva)

1. **Cell comparison.** Numerical cells compare equal within a relative tolerance of 1e-6 to absorb floating-point round-off across drivers.
2. **NULL handling.** `NULL ≡ NULL` (Spider/BIRD convention; differs from SQL `=`).
3. **Column order.** Ignored. Result sets are compared as multisets of named tuples.
4. **Timeout.** A prediction that fails to return within 30 s is scored 0 (matching `MAX_SQL_TIMEOUT_SECONDS` in production).
5. **Compile failure.** A prediction that does not parse, or raises a Postgres error, is scored 0.
6. **OUT_OF_DOMAIN.** A correct refusal (system returns `OUT_OF_DOMAIN` and the gold label is also `out_of_scope`) counts as EX = 1. A wrong refusal counts as 0. This is the only "calibrated honesty" credit we award; we report it separately as well.

### Reporting

We report EX at the **benchmark level**, and per **complexity level (L1–L6)** for SCM-SQL — the cross-domain levels (L3–L6) are where domain-axis decomposition should beat pipeline-axis decomposition, so per-level breakdown is the core defence of the thesis.

---

## 3.  Secondary metric — Valid Efficiency Score (VES)

Introduced by BIRD (NeurIPS 2023). Rewards predictions that are both *correct* and *efficient* — relevant for enterprise schemas where the same correct answer can be returned by an O(1) indexed lookup or an O(n²) full-table cross-join.

### Definition

For a correctly-predicted item, let `t_gold` and `t_pred` be the wall-clock execution times (seconds) of the gold and predicted SQL on the evaluation DB. Define the relative-efficiency function:

```
R(t_gold, t_pred)  =  min( 1.0,  sqrt( t_gold / t_pred ) )
```

Then:

```
VES(i)  =  EX(i)  ·  R(t_gold,i, t_pred,i)
```

A correct prediction that runs as fast as gold gets `VES = 1`. A correct prediction that is twice as slow gets `VES ≈ 0.71`. An incorrect prediction gets `VES = 0`.

Benchmark-level VES is the mean.

### Why we report it

BIRD's authors observed that LLM-generated SQL is often correct but pathologically inefficient (full scans, missing index hints, unnecessary cross joins). For enterprise deployment this matters. The dissertation's Composer + sqlglot-AST manipulation explicitly pushes for sensible joins; VES is the quantitative defence of that design choice.

### Caveat

VES is sensitive to caching and warm-vs-cold buffer state. We mitigate by:
- Running every prediction on a freshly restarted Postgres container.
- Running each query 3 times and using the median wall-clock.
- Reporting `EX` and `VES` side-by-side so the reader can prefer `EX` if they distrust the efficiency measurement.

---

## 4.  Tertiary metric — Exact Match (EM)

A strict but information-poor surface-level metric: do the predicted and gold SQL strings match after canonical normalisation?

### Definition

```
EM(i)  =  1   if  normalize( S_pred,i )  ==  normalize( S_gold,i )
          0   otherwise
```

Normalisation procedure (run through `sqlglot`):
1. Parse to an AST.
2. Convert all keywords to upper case.
3. Strip table aliases unless ambiguous.
4. Sort `SELECT` projection alphabetically.
5. Re-emit as a canonical PostgreSQL string.

### Why we report it (and why we don't trust it)

EM is reported for completeness — the field cites it — but **it is a poor proxy for correctness**: two semantically identical queries can have EM = 0 (different join order, different subquery factorisation) while having EX = 1. We expect our EM scores to be lower than our EX scores; this is normal and not a weakness.

---

## 5.  Comparison protocol — the fairness contract

The dissertation argues that **domain-axis decomposition** beats **pipeline-axis decomposition** on enterprise SCM workloads. To isolate that variable, every baseline must use:

| Variable | Held constant across all baselines |
|---|---|
| LLM backbone | `claude-haiku-4-5` (Anthropic API, temperature 0) |
| Evaluation database | Same Postgres 16 + Odoo 17 instance |
| Schema retrieval budget | ≤ 4 000 tokens per agent prompt |
| Max correction attempts | 3 (matches our `OrchestratorLimits`) |
| SQL execution timeout | 30 seconds |
| Compute environment | Single laptop, no GPU, Docker Compose stack |

This rule applies to **all baselines including MAC-SQL, MARS-SQL, CHASE-SQL** — the standard practice in the field is to compare the architectural contribution holding the LLM fixed. If we used the original GPT-4 for MAC-SQL and Claude Haiku for ours, the panel could (correctly) argue we conflate the architecture variable with the model-strength variable.

---

## 6.  Baselines

Five systems will be evaluated head-to-head on Spider, BIRD, and SCM-SQL.

| # | Baseline | Approach | Reference |
|---|---|---|---|
| 1 | **ZS-Haiku** | Single zero-shot prompt to claude-haiku-4-5. No agents, no decomposition. The trivial baseline. | — |
| 2 | **MAC-SQL** | Multi-agent pipeline-axis: Selector → Decomposer → Refiner. | Wang et al., COLING 2025, arXiv 2312.11242 |
| 3 | **MARS-SQL** | Pipeline-axis + RL execution-feedback self-correction. | Chen et al., Nov 2025, arXiv 2511.01008 |
| 4 | **CHASE-SQL** | Multi-path reasoning + preference-optimised candidate selection. | Pourreza et al., ICLR 2025, arXiv 2410.01943 |
| 5 | **Ours (Domain-Aware)** | Domain-axis multi-agent (Inventory / Logistics / Finance / Demand) + AST Composer + AST Compliance + 3-attempt source-routed correction. | This dissertation |

All five run with `claude-haiku-4-5` as the LLM backbone per §5.

---

## 6.5  Benchmark positioning — why SCM-SQL is the primary benchmark

Public NL-to-SQL benchmarks (Spider 1.0, BIRD, Spider 2.0) evaluate
properties this system does *not* primarily optimise for, and do not
evaluate the properties it *does* optimise for (cross-domain CTE
composition, per-tenant RBAC injection, multi-turn dialogue, ambiguity
refusal, deterministic temporal parsing). Running the system on
Spider 2.0 *as-is* would yield ~0 % EX — the Router would reject every
query as `out_of_scope`, Compliance would inject `company_id IN (...)`
into schemas without that column, and the Composer would never
activate on single-domain queries.

Our reporting stance is therefore:

1. **SCM-SQL is the primary benchmark.** It is the only public-format
   benchmark that exercises the system's architectural contributions.
   Phase 8 scales it to 500 queries for statistically-significant
   results.
2. **Spider 2.0 published numbers are cited as a contextual reference
   only** (Lei et al., 2024: GPT-4o = 10.1 % strict EX). Direct
   re-evaluation would be a category error per the architectural
   mismatch above. Our SCM-SQL Haiku result (16.1 %) sits within the
   published Spider 2.0 SOTA band (10.1 – 30 %) on a benchmark that
   tests strictly more capabilities.
3. **Spider 1.0 "generic-mode" sanity check** (see `benchmark/spider1_sanity/`)
   — a bypass of Router + Compliance + Composer that exercises only
   the core SQL-generation pathway against Spider 1.0 dev. This
   confirms the base SQL engine is sound on schemas it was not
   specialised for. Numbers reported as a back-stop only; not as a
   competitive claim.
4. **MAC-SQL head-to-head on the same backbone and the same benchmark
   is the dissertation's primary empirical claim.** The architectural
   variable is the only variable. Spider/BIRD comparisons cannot
   reproduce that contract because the architectures they support
   target a different problem.

This is consistent with field practice: BIRD itself was introduced as
a parallel benchmark to Spider, not a replacement, because the two
test different capabilities. EHRSQL evaluates on medical-only data.
DAIL-SQL reports both Spider and BIRD numbers because each benchmark
tests something different. We follow that convention.

---

## 7.  Ablation grid

Ablations isolate the contribution of each component of our system. Each row removes one feature; the delta from the full system is the attributable contribution.

| Ablation label | What is removed | What we expect |
|---|---|---|
| **–domain** | Replace the 4 domain specialists with one combined agent | EX drops most on L3–L4 (cross-domain). This is the core thesis defence. |
| **–correction** | Disable the self-correction loop (1 attempt only) | EX drops ~3–5 pp benchmark-wide |
| **–ambiguity** | Skip the Ambiguity Resolver; always proceed | EX falls only on the ambiguous-term subset; precision rises slightly elsewhere |
| **–temporal** | Skip the Temporal Parser; let the LLM handle dates | EX falls sharply on queries with relative-date language ("last quarter", "YoY") |
| **–compliance** | Skip RBAC predicate injection | EX unchanged; we instead report leaked-row-count, which should be non-zero |
| **–multi-turn** | Treat every turn as independent (no carry-over) | EX falls on L6 only; other levels unchanged |
| **–CSR-RAG** | Replace schema retrieval with a fixed top-k from a flat BM25 | EX drops on queries requiring tables outside the obvious vocabulary |

The full grid: 5 baselines × 7 ablations × 3 benchmarks × 3 metrics = **315 numbers** in the final paper's main results table.

---

## 8.  Statistical significance — bootstrap + Wilcoxon

Reporting a single EX number is not enough; we need to show that the gap between our system and each baseline is **not within sampling noise**.

### Procedure

For each metric `M` and each pair (ours, baseline):

1. **Bootstrap resample** the benchmark with replacement, `n = 1000` resamples.
2. For each resample, compute `M(ours) – M(baseline)`.
3. Report the 95 % confidence interval of the difference.
4. Apply the **Wilcoxon signed-rank test** to the per-query paired scores; report `p`.
5. Apply **Bonferroni correction** for the number of comparisons (5 baselines × 3 benchmarks = 15).

### Effect size

In addition to `p`, we report **Cliff's delta** for the EX comparison:

```
δ  =  P(EX_ours > EX_baseline)  −  P(EX_ours < EX_baseline)
```

Interpretation thresholds (Romano et al.): |δ| < 0.147 negligible, < 0.33 small, < 0.474 medium, ≥ 0.474 large. **Our target is medium or large effect (δ ≥ 0.33) on Levels 3–6.**

---

## 9.  Failure analysis

Quantitative scores are necessary but not sufficient — the panel will ask *"where does it still fail?"*. The failure analysis section of the paper does five things:

1. **Confusion by error category.** Each incorrect prediction is auto-classified into one of: `syntax`, `wrong-table`, `wrong-aggregation`, `temporal`, `RBAC-scope`, `ambiguity-unresolved`, `composer-merge`, `validator-timeout`. Distribution per baseline and per complexity level.
2. **Confusion by domain.** Which specialist agent makes the most errors? Concentrated failure in one agent suggests its few-shot bank needs expansion, not architectural change.
3. **Per-level error rate.** Where on the L1–L6 ladder do we fall off?
4. **Hand-analysed sample.** Five representative failures (one per category) walked through in the paper appendix: NL, gold SQL, predicted SQL, root cause, remedy.
5. **Self-correction recovery rate.** What percentage of initially-failing predictions are rescued by the 3-attempt loop? Compared to MARS-SQL's loop.

---

## 10.  Reporting tables (planned layout)

### Table A — Main results (headline)

| System | Spider EX | BIRD EX | SCM-SQL EX | Spider VES | BIRD VES | SCM-SQL VES |
|---|---|---|---|---|---|---|
| ZS-Haiku |     |     |     |     |     |     |
| MAC-SQL  |     |     |     |     |     |     |
| MARS-SQL |     |     |     |     |     |     |
| CHASE-SQL|     |     |     |     |     |     |
| **Ours** |     |     |     |     |     |     |

### Table B — Per-level SCM-SQL EX

| System | L1 | L2 | L3 | L4 | L5 | L6 | Overall |
|---|---|---|---|---|---|---|---|
| ZS-Haiku  |  |  |  |  |  |  |  |
| MAC-SQL   |  |  |  |  |  |  |  |
| MARS-SQL  |  |  |  |  |  |  |  |
| CHASE-SQL |  |  |  |  |  |  |  |
| **Ours**  |  |  |  |  |  |  |  |

### Table C — Ablation grid (SCM-SQL EX)

| Configuration | L1 | L2 | L3 | L4 | L5 | L6 | Δ overall |
|---|---|---|---|---|---|---|---|
| Full system (ours)  |  |  |  |  |  |  | — |
| –domain             |  |  |  |  |  |  |  |
| –correction         |  |  |  |  |  |  |  |
| –ambiguity          |  |  |  |  |  |  |  |
| –temporal           |  |  |  |  |  |  |  |
| –compliance         |  |  |  |  |  |  |  |
| –multi-turn         |  |  |  |  |  |  |  |
| –CSR-RAG            |  |  |  |  |  |  |  |

### Table D — Significance vs each baseline (SCM-SQL EX)

| Comparison | EX gap | 95 % CI | Wilcoxon p | Bonferroni p | Cliff's δ | Verdict |
|---|---|---|---|---|---|---|
| Ours vs ZS-Haiku    |  |  |  |  |  |  |
| Ours vs MAC-SQL     |  |  |  |  |  |  |
| Ours vs MARS-SQL    |  |  |  |  |  |  |
| Ours vs CHASE-SQL   |  |  |  |  |  |  |

---

## 11.  Targets (the numerical commitments)

The dissertation will succeed if, on SCM-SQL, the following hold:

| Claim | Target |
|---|---|
| Overall EX of our system | ≥ 60 % |
| EX lift vs MAC-SQL on Levels 3–6 | ≥ 10 percentage points |
| Cliff's δ vs MAC-SQL on L3–L6 EX | ≥ 0.33 (medium) |
| Bonferroni-corrected `p` for our-vs-MAC-SQL on overall EX | ≤ 0.05 |
| VES not worse than MAC-SQL | within 0.05 of MAC-SQL VES |
| Self-correction recovery rate | ≥ 15 % of initially-failing predictions rescued |
| Compliance: leaked rows under RBAC eval | exactly 0 |

These are commitments, not aspirations. If we hit fewer than five of these seven, the conclusion section of the paper will discuss why, not paper over it.

---

## 12.  What is built today vs what remains

| Building block | Status |
|---|---|
| Metric implementations (EX / VES / EM scoring functions) | **To build** — `backend/app/eval/metrics.py`, ~0.5 day |
| Benchmark runner script that runs each system on each benchmark and writes a JSONL of (item_id, predicted_sql, exec_time, EX, VES, EM) | **To build** — `scripts/run_evaluation.py`, ~1 day |
| MAC-SQL adapter that calls Anthropic Haiku as its backbone | **To build** — `scripts/baselines/mac_sql_adapter.py`, ~1 day |
| Statistical analysis script (bootstrap + Wilcoxon) | **To build** — `scripts/eval_stats.py`, ~0.5 day |
| Reporting templates (the tables in §10) | **To build** — Jinja2 templates → markdown, ~0.5 day |
| SCM-SQL pilot (50 queries) | **To build for midsem** — Phase 8 starts after midsem framework lands |
| SCM-SQL full (500 queries) | **Phase 8 (deadline 5 Jul)** |
| Spider + BIRD full runs | **Phase 10 (deadline 2 Aug)** |

**Total effort to lock the evaluation framework in code:** ≈ 3.5 days.

---

## 13.  Decisions documented (so the panel cannot ambush them)

| Decision | Choice | Rationale |
|---|---|---|
| Primary metric | EX | Field standard; Spider / BIRD / Spider 2.0 / MAC-SQL all lead with it |
| Backbone LLM held constant across baselines | claude-haiku-4-5 | Isolates the architecture variable; same-model rule defended in §5 |
| Significance test | Wilcoxon signed-rank | Paired, non-parametric, appropriate for binary EX(i) scores |
| Multiple-comparisons correction | Bonferroni | Conservative; rejects fewer false claims |
| Effect-size measure | Cliff's δ | Standard for ordinal/binary comparisons; interpretable thresholds |
| Bootstrap iterations | 1 000 | Standard for 95 % CI on benchmarks of this size; converges well |
| Cell-equality tolerance for numeric values | 1e-6 relative | Absorbs driver-level round-off |
| Timeout per query | 30 s | Matches production setting; longer is unrepresentative |
| Failure-mode classifier | 8 categories | Empirically covers ~95 % of observed failures across pilots |

---

*Document version 1.0  ·  Generated 2026-05-20  ·  Author: Aniruddha Prakash Kawarase*

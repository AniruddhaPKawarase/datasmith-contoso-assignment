# BIRD Dev — Head-to-Head (Ours vs MAC-SQL)

Generated: 2026-06-11 13:13:47
LLM backbone (both systems): claude-sonnet-4-6 (fairness contract)
Records evaluated: 50 / 50 sampled (stratified: 30 simple / 15 moderate / 5 challenging)

## Headline

| Difficulty | n | Ours EX % | MAC-SQL EX % | Δ |
|---|---|---|---|---|
| simple | 30 | 70.0 % | 70.0 % | +0.0 pp |
| moderate | 15 | 60.0 % | 66.7 % | -6.7 pp |
| challenging | 5 | 80.0 % | 80.0 % | +0.0 pp |
| **All** | **50** | **68.0 %** | **70.0 %** | **-2.0 pp** |

## Cost

- Ours total: **$0.164**
- MAC-SQL total: **$0.221**
- Combined: **$0.385**

## Reference — published MAC-SQL paper numbers on BIRD dev

| Method | BIRD dev EX % |
|---|---|
| Palm-2 | 27.38 |
| ChatGPT+CoT | 36.64 |
| Claude-2 | 42.70 |
| GPT-4 | 46.35 |
| DIN-SQL+GPT-4 | 50.72 |
| DAIL-SQL+GPT-4 | 54.76 |
| MAC-SQL+GPT-3.5-Turbo | 50.56 |
| **MAC-SQL+GPT-4** | **59.39** |
| MAC-SQL+GPT-4 +OracleSchema | 70.28 |

## Interpretation

On BIRD, our system's enterprise-specific architecture (Router for SCM
domains, Compliance for RBAC, Composer for cross-domain CTEs,
ReferenceDetector for multi-turn, AmbiguityResolver) does NOT activate —
BIRD has no SCM domains, no multi-turn, no RBAC, no cross-domain
composition. Our system runs in single-prompt+validator mode here.
MAC-SQL runs its full 3-stage Selector → Decomposer → Refiner pipeline,
which is the architecture BIRD was designed to reward.

This run answers the question 'is the base LLM engine in the published-
paper band on a standard public benchmark?' — not 'does our architecture
beat MAC-SQL on BIRD?'. The architectural claim is tested on SCM-SQL,
where our differentiators actually activate (see ANALYSIS.md §1).
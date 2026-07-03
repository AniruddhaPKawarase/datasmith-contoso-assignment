# SCM-SQL Pilot — Statistical Analysis

n = 56 paired records  ·  bootstrap n = 1000  ·  α = 0.05

## Per-level strict Execution Accuracy with 95 % CI

| Level | n | Ours EX % (95 % CI) | MAC-SQL EX % (95 % CI) | Δ % | Wilcoxon p | Bonferroni p | Cliff's δ |
|---|---|---|---|---|---|---|---|
| L1 | 10 | 20.0 (0.0–40.0) | 40.0 (10.0–70.0) | -20.0 | 0.361 | 1.000 | -0.20 (small) |
| L2 | 10 | 0.0 (0.0–0.0) | 0.0 (0.0–0.0) | +0.0 | 1.000 | 1.000 | +0.00 (negligible) |
| L3 | 15 | 33.3 (13.3–60.0) | 13.3 (0.0–33.3) | +20.0 | 0.225 | 1.000 | +0.20 (small) |
| L4 | 5 | 0.0 (0.0–0.0) | 0.0 (0.0–0.0) | +0.0 | 1.000 | 1.000 | +0.00 (negligible) |
| L5 | 5 | 0.0 (0.0–0.0) | 0.0 (0.0–0.0) | +0.0 | 1.000 | 1.000 | +0.00 (negligible) |
| L6 | 11 | 0.0 (0.0–0.0) | 0.0 (0.0–0.0) | +0.0 | 1.000 | 1.000 | +0.00 (negligible) |
| **All** | **56** | **12.5 (3.6–23.2)** | **10.7 (3.6–19.6)** | **+1.8** | **0.767** | **1.000** | **+0.02 (negligible)** |

## Per-level Soft-EX (column-name-agnostic) with 95 % CI

| Level | n | Ours Soft-EX % (95 % CI) | MAC-SQL Soft-EX % (95 % CI) | Δ % |
|---|---|---|---|---|
| L1 | 10 | 30.0 (10.0–60.0) | 40.0 (10.0–70.0) | -10.0 |
| L2 | 10 | 0.0 (0.0–0.0) | 0.0 (0.0–0.0) | +0.0 |
| L3 | 15 | 33.3 (13.3–60.0) | 13.3 (0.0–33.3) | +20.0 |
| L4 | 5 | 0.0 (0.0–0.0) | 0.0 (0.0–0.0) | +0.0 |
| L5 | 5 | 0.0 (0.0–0.0) | 0.0 (0.0–0.0) | +0.0 |
| L6 | 11 | 0.0 (0.0–0.0) | 0.0 (0.0–0.0) | +0.0 |
| **All** | **56** | **14.3 (5.4–23.2)** | **10.7 (3.6–19.6)** | **+3.6** |

## Commitment scorecard (from EVALUATION_FRAMEWORK §11)

| Target | Threshold | Observed | Met? |
|---|---|---|---|
| Overall EX | ≥ 60 % | 14.3 % | ✗ |
| Δ vs MAC-SQL on L3-L6 | ≥ +10 pp | +8.3 pp | ✗ |
| Cliff's δ vs MAC-SQL (overall) | ≥ 0.33 (medium) | +0.02 | ✗ |
| Bonferroni-corrected p (overall) | ≤ 0.05 | 1.000 | ✗ |
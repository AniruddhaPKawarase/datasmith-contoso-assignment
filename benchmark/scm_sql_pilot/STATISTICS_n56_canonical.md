# SCM-SQL Pilot — Statistical Analysis

n = 56 paired records  ·  bootstrap n = 1000  ·  α = 0.05

## Per-level strict Execution Accuracy with 95 % CI

| Level | n | Ours EX % (95 % CI) | MAC-SQL EX % (95 % CI) | Δ % | Wilcoxon p | Bonferroni p | Cliff's δ |
|---|---|---|---|---|---|---|---|
| L1 | 10 | 40.0 (10.0–70.0) | 40.0 (10.0–70.0) | +0.0 | 1.000 | 1.000 | +0.00 (negligible) |
| L2 | 10 | 10.0 (0.0–30.0) | 0.0 (0.0–0.0) | +10.0 | 0.317 | 1.000 | +0.10 (negligible) |
| L3 | 15 | 20.0 (0.0–40.0) | 6.7 (0.0–20.0) | +13.3 | 0.361 | 1.000 | +0.13 (negligible) |
| L4 | 5 | 0.0 (0.0–0.0) | 0.0 (0.0–0.0) | +0.0 | 1.000 | 1.000 | +0.00 (negligible) |
| L5 | 5 | 0.0 (0.0–0.0) | 0.0 (0.0–0.0) | +0.0 | 1.000 | 1.000 | +0.00 (negligible) |
| L6 | 11 | 9.1 (0.0–27.3) | 0.0 (0.0–0.0) | +9.1 | 0.317 | 1.000 | +0.09 (negligible) |
| **All** | **56** | **16.1 (7.1–26.8)** | **8.9 (1.8–17.9)** | **+7.1** | **0.262** | **1.000** | **+0.07 (negligible)** |

## Per-level Soft-EX (column-name-agnostic) with 95 % CI

| Level | n | Ours Soft-EX % (95 % CI) | MAC-SQL Soft-EX % (95 % CI) | Δ % |
|---|---|---|---|---|
| L1 | 10 | 40.0 (10.0–70.0) | 40.0 (10.0–70.0) | +0.0 |
| L2 | 10 | 10.0 (0.0–30.0) | 0.0 (0.0–0.0) | +10.0 |
| L3 | 15 | 20.0 (0.0–40.0) | 6.7 (0.0–20.0) | +13.3 |
| L4 | 5 | 0.0 (0.0–0.0) | 0.0 (0.0–0.0) | +0.0 |
| L5 | 5 | 0.0 (0.0–0.0) | 0.0 (0.0–0.0) | +0.0 |
| L6 | 11 | 9.1 (0.0–27.3) | 0.0 (0.0–0.0) | +9.1 |
| **All** | **56** | **16.1 (7.1–26.8)** | **8.9 (1.8–16.1)** | **+7.1** |

## Commitment scorecard (from EVALUATION_FRAMEWORK §11)

| Target | Threshold | Observed | Met? |
|---|---|---|---|
| Overall EX | ≥ 60 % | 16.1 % | ✗ |
| Δ vs MAC-SQL on L3-L6 | ≥ +10 pp | +8.3 pp | ✗ |
| Cliff's δ vs MAC-SQL (overall) | ≥ 0.33 (medium) | +0.07 | ✗ |
| Bonferroni-corrected p (overall) | ≤ 0.05 | 1.000 | ✗ |
# SCM-SQL Pilot — Statistical Analysis

n = 113 paired records  ·  bootstrap n = 1000  ·  α = 0.05

## Per-level strict Execution Accuracy with 95 % CI

| Level | n | Ours EX % (95 % CI) | MAC-SQL EX % (95 % CI) | Δ % | Wilcoxon p | Bonferroni p | Cliff's δ |
|---|---|---|---|---|---|---|---|
| L1 | 20 | 45.0 (25.0–65.0) | 50.0 (30.0–70.0) | -5.0 | 0.686 | 1.000 | -0.05 (negligible) |
| L2 | 20 | 10.0 (0.0–25.0) | 0.0 (0.0–0.0) | +10.0 | 0.180 | 1.000 | +0.10 (negligible) |
| L3 | 30 | 26.7 (13.3–43.3) | 20.0 (6.7–36.7) | +6.7 | 0.463 | 1.000 | +0.07 (negligible) |
| L4 | 10 | 0.0 (0.0–0.0) | 0.0 (0.0–0.0) | +0.0 | 1.000 | 1.000 | +0.00 (negligible) |
| L5 | 10 | 0.0 (0.0–0.0) | 0.0 (0.0–0.0) | +0.0 | 1.000 | 1.000 | +0.00 (negligible) |
| L6 | 23 | 8.7 (0.0–21.7) | 4.3 (0.0–13.0) | +4.3 | 0.317 | 1.000 | +0.04 (negligible) |
| **All** | **113** | **18.6 (11.5–25.7)** | **15.0 (8.8–21.2)** | **+3.5** | **0.346** | **1.000** | **+0.04 (negligible)** |

## Per-level Soft-EX (column-name-agnostic) with 95 % CI

| Level | n | Ours Soft-EX % (95 % CI) | MAC-SQL Soft-EX % (95 % CI) | Δ % |
|---|---|---|---|---|
| L1 | 20 | 45.0 (25.0–65.0) | 50.0 (30.0–70.0) | -5.0 |
| L2 | 20 | 10.0 (0.0–25.0) | 0.0 (0.0–0.0) | +10.0 |
| L3 | 30 | 26.7 (10.0–43.3) | 20.0 (6.7–36.7) | +6.7 |
| L4 | 10 | 0.0 (0.0–0.0) | 0.0 (0.0–0.0) | +0.0 |
| L5 | 10 | 0.0 (0.0–0.0) | 0.0 (0.0–0.0) | +0.0 |
| L6 | 23 | 8.7 (0.0–21.7) | 4.3 (0.0–13.0) | +4.3 |
| **All** | **113** | **18.6 (11.5–25.7)** | **15.0 (8.8–21.2)** | **+3.5** |

## Commitment scorecard (from EVALUATION_FRAMEWORK §11)

| Target | Threshold | Observed | Met? |
|---|---|---|---|
| Overall EX | ≥ 60 % | 18.6 % | ✗ |
| Δ vs MAC-SQL on L3-L6 | ≥ +10 pp | +4.1 pp | ✗ |
| Cliff's δ vs MAC-SQL (overall) | ≥ 0.33 (medium) | +0.04 | ✗ |
| Bonferroni-corrected p (overall) | ≤ 0.05 | 1.000 | ✗ |
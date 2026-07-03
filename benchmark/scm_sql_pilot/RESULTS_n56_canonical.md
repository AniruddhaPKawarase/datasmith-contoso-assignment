# SCM-SQL Pilot — Head-to-Head Results

Generated: 2026-05-27 17:04:34
Pairs evaluated: 56

## Per-level Execution Accuracy  (strict + Soft-EX)

Soft-EX is column-name-agnostic: row count + value-multiset match.
See `docs/eval/EVALUATION_FRAMEWORK.md` §2.

| Level | n | Ours EX | Ours Soft-EX | MAC EX | MAC Soft-EX | Δ EX | Δ Soft-EX |
|---|---|---|---|---|---|---|---|
| L1 | 10 | 40.0 % | 40.0 % | 40.0 % | 40.0 % | +0.0 pp | +0.0 pp |
| L2 | 10 | 10.0 % | 10.0 % | 0.0 % | 0.0 % | +10.0 pp | +10.0 pp |
| L3 | 15 | 20.0 % | 20.0 % | 6.7 % | 6.7 % | +13.3 pp | +13.3 pp |
| L4 | 5 | 0.0 % | 0.0 % | 0.0 % | 0.0 % | +0.0 pp | +0.0 pp |
| L5 | 5 | 0.0 % | 0.0 % | 0.0 % | 0.0 % | +0.0 pp | +0.0 pp |
| L6 | 11 | 9.1 % | 9.1 % | 0.0 % | 0.0 % | +9.1 pp | +9.1 pp |
| **All** | **56** | **16.1 %** | **16.1 %** | **8.9 %** | **8.9 %** | **+7.1 pp** | **+7.1 pp** |

## Token usage

| Task | Model | Calls | Input | Output |
|---|---|---|---|---|
| router | gpt-4o-mini | 112 | 37124 | 6434 |
| sql_gen | claude-haiku-4-5 | 122 | 285380 | 15811 |
| validator | claude-haiku-4-5 | 6 | 6305 | 656 |
| **Total** |  |  | **328809** | **22901** |

Estimated cost: **$0.0887**
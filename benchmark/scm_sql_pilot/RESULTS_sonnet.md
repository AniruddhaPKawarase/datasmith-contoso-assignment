# SCM-SQL Pilot — Head-to-Head Results

Generated: 2026-05-27 17:46:19
Pairs evaluated: 56

## Per-level Execution Accuracy  (strict + Soft-EX)

Soft-EX is column-name-agnostic: row count + value-multiset match.
See `docs/eval/EVALUATION_FRAMEWORK.md` §2.

| Level | n | Ours EX | Ours Soft-EX | MAC EX | MAC Soft-EX | Δ EX | Δ Soft-EX |
|---|---|---|---|---|---|---|---|
| L1 | 10 | 20.0 % | 30.0 % | 40.0 % | 40.0 % | -20.0 pp | -10.0 pp |
| L2 | 10 | 0.0 % | 0.0 % | 0.0 % | 0.0 % | +0.0 pp | +0.0 pp |
| L3 | 15 | 33.3 % | 33.3 % | 13.3 % | 13.3 % | +20.0 pp | +20.0 pp |
| L4 | 5 | 0.0 % | 0.0 % | 0.0 % | 0.0 % | +0.0 pp | +0.0 pp |
| L5 | 5 | 0.0 % | 0.0 % | 0.0 % | 0.0 % | +0.0 pp | +0.0 pp |
| L6 | 11 | 0.0 % | 0.0 % | 0.0 % | 0.0 % | +0.0 pp | +0.0 pp |
| **All** | **56** | **12.5 %** | **14.3 %** | **10.7 %** | **10.7 %** | **+1.8 pp** | **+3.6 pp** |

## Token usage

| Task | Model | Calls | Input | Output |
|---|---|---|---|---|
| router | gpt-4o-mini | 112 | 37124 | 6429 |
| sql_gen | claude-sonnet-4-6 | 121 | 278014 | 20441 |
| validator | claude-sonnet-4-6 | 4 | 5449 | 2318 |
| **Total** |  |  | **320587** | **29188** |

Estimated cost: **$0.0933**
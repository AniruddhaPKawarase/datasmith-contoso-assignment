# SCM-SQL Pilot — Head-to-Head Results

Generated: 2026-06-11 12:22:24
Pairs evaluated: 113

## Per-level Execution Accuracy  (strict + Soft-EX)

Soft-EX is column-name-agnostic: row count + value-multiset match.
See `docs/eval/EVALUATION_FRAMEWORK.md` §2.

| Level | n | Ours EX | Ours Soft-EX | MAC EX | MAC Soft-EX | Δ EX | Δ Soft-EX |
|---|---|---|---|---|---|---|---|
| L1 | 20 | 45.0 % | 45.0 % | 50.0 % | 50.0 % | -5.0 pp | -5.0 pp |
| L2 | 20 | 10.0 % | 10.0 % | 0.0 % | 0.0 % | +10.0 pp | +10.0 pp |
| L3 | 30 | 26.7 % | 26.7 % | 20.0 % | 20.0 % | +6.7 pp | +6.7 pp |
| L4 | 10 | 0.0 % | 0.0 % | 0.0 % | 0.0 % | +0.0 pp | +0.0 pp |
| L5 | 10 | 0.0 % | 0.0 % | 0.0 % | 0.0 % | +0.0 pp | +0.0 pp |
| L6 | 23 | 8.7 % | 8.7 % | 4.3 % | 4.3 % | +4.3 pp | +4.3 pp |
| **All** | **113** | **18.6 %** | **18.6 %** | **15.0 %** | **15.0 %** | **+3.5 pp** | **+3.5 pp** |

## Token usage

| Task | Model | Calls | Input | Output |
|---|---|---|---|---|
| router | gpt-4o-mini | 226 | 74700 | 12945 |
| sql_gen | claude-haiku-4-5 | 248 | 570305 | 33561 |
| validator | claude-haiku-4-5 | 22 | 24115 | 3978 |
| **Total** |  |  | **669120** | **50484** |

Estimated cost: **$0.1843**
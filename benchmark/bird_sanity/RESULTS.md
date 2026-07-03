# BIRD — Generic-Mode Sanity Check

Generated: 2026-06-01 17:34:33
Records: 50
Backbone: claude-haiku-4-5 (single-prompt; Router + Compliance + Composer bypassed)
Source: xu3kev/BIRD-SQL-data-train (public BIRD training-data mirror)

## Headline

- **Exact Match (sqlglot canonical):  6.0 %** (3/50)
- **Structurally valid SQL (sqlglot-parseable):  98.0 %** (49/50)

## Interpretation

Strict EM is famously brittle (column-name aliases, ORDER BY
stability, equivalent JOIN orderings all break it). Published
Spider 1.0 leaderboards use execution accuracy against the live
SQLite databases — which the public mirror does not ship — and
thus report 10-30 pp higher than the EM rate seen here. The
parse-rate is the more useful sanity-check signal: it shows
the LLM is producing structurally valid SQL against schemas it
has not been specialised for. See EVALUATION_FRAMEWORK §6.5 for
the full rationale on why this is a back-stop check rather than
a competitive evaluation.

## Token usage

| Task | Model | Calls | Input | Output |
|---|---|---|---|---|
| sql_gen | claude-haiku-4-5 | 50 | 74632 | 3821 |
| **Total** |  |  | **74632** | **3821** |

Estimated cost: **$0.0937**
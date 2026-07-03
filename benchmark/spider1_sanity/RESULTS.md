# Spider 1.0 — Generic-Mode Sanity Check

Generated: 2026-05-27 21:53:17
Records: 50
Backbone: claude-haiku-4-5 (single-prompt; Router + Compliance + Composer bypassed)
Source: b-mc2/sql-create-context (public Spider 1.0 mirror with bundled schemas)

## Headline

- **Exact Match (sqlglot canonical):  18.0 %** (9/50)
- **Structurally valid SQL (sqlglot-parseable):  100.0 %** (50/50)

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
| sql_gen | claude-haiku-4-5 | 50 | 5067 | 2069 |
| **Total** |  |  | **5067** | **2069** |

Estimated cost: **$0.0154**
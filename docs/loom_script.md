# 3-min Loom demo script

**Target length:** 2:45 – 3:00. Anything longer and mentors skim.
**Open beforehand:** [scm-contoso.vercel.app](https://scm-contoso.vercel.app) in a fresh tab (cold-start warms the Render backend on first click — hit `/healthz` once yourself before you press record so the demo isn't waiting on cold Docker).

## Warm-up (30 s before recording)
```
curl -s https://scm-contoso-api.onrender.com/healthz
```
Should return `{"ok":true,"tables":15,"sessions":0}` in <1 s. If it takes 30 s, Render just cold-booted; give it one more request to settle.

## Recording outline

| Sec | On-screen | Voice-over |
|-----|-----------|------------|
| 0-15 | Vercel URL open, sidebar with sample questions visible | "This is SCM-Contoso — an agentic natural-language analyst over the Microsoft Contoso retail data warehouse. FastAPI backend on Render, Next.js frontend on Vercel, Postgres on Neon. Fifteen tables, twelve million rows in the local build, 200k live." |
| 15-45 | Click **"Show monthly revenue for 2009 by region"** → wait for chart | "One click. The Router classifies the intent, a demand specialist picks the tables, the composer generates SQL using dynamic schema injection — no column names hard-coded in prompts — and sqlglot validates before we ever touch the database. Postgres returns twenty-six rows, VizSelector picks a line chart with region as the series. Total: eleven seconds." |
| 45-75 | Open the collapsible SQL block · click "Copy SQL" | "Every response ships with the generated SQL, an EXPLAIN-OK badge, and a copy button. Below it, the Agent Trace shows planner intent, plan steps, and executor notes — audit-grade transparency." |
| 75-105 | Click **"Show me a sales funnel: orders → shipped → revenue by territory"** → 3 panels appear stacked | "Multi-step queries: the planner recognises the funnel shape, emits three sub-steps, executes each, and stacks the results into a 3-panel view. Deterministic planner — regex-based, not LLM-driven — so this is reproducible across runs." |
| 105-135 | Click **"Give me a full customer demographic breakdown for the Pacific region"** → 3 panels | "Same pattern for demographic breakdowns. Notice: 'Pacific' isn't a real region in the data — Contoso uses Asia, Europe, North America. The planner has a synonym map that translates Pacific → Asia automatically. Ten customers matched, split across gender, income, and education." |
| 135-165 | Type free-form: "Show top 10 products by revenue in 2009" · CSV download · PNG download | "Ambiguity, clarification, out-of-scope — all handled by the router. CSV export, chart PNG export, error hints with schema suggestions. Cost is tracked per request — the whole demo you just watched cost about four cents." |
| 165-180 | Show repo URL + docs folder in a new tab | "Full code at github.com/AniruddhaPKawarase/datasmith-contoso-assignment. Ten-test pytest suite, honest test-case matrix documenting known limits under gpt-4o-mini, and a 5-step deployment runbook. Thanks for watching." |

## What NOT to demo (skip if pinched for time)
- Voice input — skipped this build.
- Semantic cache — designed but not implemented.
- Streaming — the /ask/stream endpoint exists; skip because the polished UI is on non-streaming.

## Talking points about limitations (if asked in Q&A)

- **Live DB is a 200k-row subset of 2009** — Neon free tier caps at 512 MB. Local dev uses the full 12.6 M-row dataset. Nothing about the pipeline changes; only data volume differs.
- **Backbone is gpt-4o-mini** — Anthropic Haiku credits were exhausted mid-build. The pipeline is provider-agnostic (env-var-driven); swap to Sonnet or Haiku 4.5 by changing one env var.
- **TC03 (multi-fact UNION) fails on the small model** — documented in [test_case_matrix.md](../repo/docs/test_case_matrix.md). Schema and few-shots are correct; the composer prompt is at its size ceiling for 4o-mini.
- **Render cold-start ~30 s** — free-tier web service sleeps after 15 min idle. First request after idle is slow; every subsequent request is fast. Frontend timeout is 180 s so it survives.

## Two safety notes for the recording

1. Do NOT click into the token-usage chip if any earlier request contained sensitive data — the response body carries prompts. (Nothing sensitive is in this demo, so ignore.)
2. The Agent Trace panel shows internal planner steps — that's the point, don't hide it.

# Demo question bank — 20 prompts covering the full behavior surface

Live gateway: `https://scm-contoso-api.onrender.com` · UI: `https://scm-contoso.vercel.app`
Backbone: `openai/gpt-4o-mini` · DB: CockroachDB Serverless with full 22.8 M-row Contoso (12.03 M `factonlinesales`, 3.4 M `factsales`, 7.37 M `factsalesquota`, 25 k dims).

The 20 questions are grouped by what they test in the agent pipeline. Every "should PASS" entry has been verified against the live stack today. Every "should CLARIFY" or "should reject" is designed to exercise a specific decision path.

---

## A — Single-domain data queries (8) · should **PASS**

Each one hits a single specialist (`demand`), goes through composer → executor → VizSelector, and returns a chart or table.

| # | Question | Expected viz | Expected rows |
|---|----------|--------------|---------------|
| 1 | Show monthly revenue for 2009 by region | **line** (multi-series) | 100 |
| 2 | Who are our top 10 customers by lifetime value? | **bar** | 10 |
| 3 | Show top 10 products by revenue in 2009 | **bar** | 10 |
| 4 | Show revenue by product category for 2009 | **bar** | 8 |
| 5 | Show revenue by territory group for 2009 | **bar** | 3 |
| 6 | Show me the top 10 stores by revenue in 2009 | **bar** | 10 |
| 7 | What is the average order value by product category in 2009? | **bar** | 8 |
| 8 | Show quarterly revenue trend for 2008 and 2009 | **line** | ~8 |

**What each proves:**
- **#1, #8** — time series, dynamic schema injection, VizSelector correctly picks line
- **#2-#7** — ranking + aggregation over the 12 M-row fact
- **#7** — dialect-safe division (`::float` cast — rule 11)

---

## B — Multi-domain / multi-step queries (5) · should **PASS or PARTIAL**

Cross-table joins or planner-triggered multi-panel output.

| # | Question | Tables touched | Expected shape |
|---|----------|----------------|----------------|
| 9 | Which employees exceeded their sales quota in Q2 2009? | `factsales` × `factsalesquota` × `dimstore` × `dimgeography` × `dimsalesterritory` × `dimemployee` | **table**, ~100 rows |
| 10 | Show me a sales funnel: orders → shipped → revenue by territory | Planner emits 3 sub-queries against `factonlinesales` + `dimcustomer` + `dimsalesterritory` | **multi-panel × 3** (~60 rows each) |
| 11 | Compare monthly revenue between 2008 and 2009 by region | `factonlinesales` × `dimdate` × `dimcustomer` × `dimgeography` × `dimsalesterritory` (grouped 2-year) | **line** (~24 rows) |
| 12 | Give me a full customer demographic breakdown for the Pacific region | Planner emits 3 panels (gender / income / education); "Pacific" auto-mapped to `salesterritorygroup = 'Asia'` | **multi-panel × 3** |
| 13 | Show revenue by channel for 2009 | `factsales` × `dimchannel` (Store / Online / Reseller / Catalog) | **bar** or **pie**, 4 rows |

**What each proves:**
- **#9** — snowflake join graph (store → geography → territory → employee) plus quota-vs-actual math (rule 10)
- **#10** — deterministic PlannerChain regex fires; 3 sub-queries run through the same pipeline
- **#11** — multi-year time series with a proper GROUP BY that survives 22 M rows
- **#12** — synonym mapping ("Pacific" → "Asia") + planner fan-out
- **#13** — channel dim join (`dimchannel` has 4 values), tests categorical viz selection

---

## C — Ambiguous queries (3) · should **CLARIFY**

The AmbiguityResolver kicks in — router returns `intent = "clarification_needed"` and the UI shows an amber card instead of forcing a bad guess.

| # | Question | Why it's ambiguous | Expected system reply |
|---|----------|--------------------|-----------------------|
| 14 | Show me sales. | Sales *by what*? month, region, channel, product? | "Did you want revenue by month, region, channel, or product?" |
| 15 | How are we doing this year? | "Doing" = revenue / margin / attainment / growth? Which fact table? | "Which metric — revenue, quota attainment, order count?" |
| 16 | Tell me about our customers. | No aggregation dimension specified | "Do you want counts by demographic, top customers by spend, or a geographic breakdown?" |

**What each proves:**
- Router doesn't hallucinate a "safe" SQL — it explicitly returns `intent = clarification_needed` and asks a question
- UI renders the clarification path (amber card, no chart, no SQL block)
- Follow-up in the same session lets the user refine without repeating the whole context

---

## D — Out-of-scope queries (4) · should be **REJECTED**

Queries the system can't answer with Contoso data. Router returns `intent = "out_of_scope"` and the UI shows a neutral "not an SCM domain I can answer" card. Cost per query: ~$0.001 (only router LLM ran).

| # | Question | Category | Expected behavior |
|---|----------|----------|-------------------|
| 17 | What's the weather in Bangalore today? | General knowledge | rejected — no weather data in schema |
| 18 | Write me a poem about supply chains. | Creative writing | rejected — not a data question |
| 19 | What is the meaning of life? | Philosophical | rejected — no data grounding |
| 20 | How do I reset my email password? | IT support / off-topic | rejected — no user directory in Contoso |

**What each proves:**
- Router correctly refuses non-data queries instead of guessing SQL
- No wasted tokens on the composer / validator / executor for out-of-scope queries
- UI shows a distinct "out of scope" card (not the amber clarify card, not an error)

---

## Quick copy-paste block for a demo session

```
Show monthly revenue for 2009 by region
Who are our top 10 customers by lifetime value?
Show top 10 products by revenue in 2009
Show revenue by product category for 2009
Show revenue by territory group for 2009
Show me the top 10 stores by revenue in 2009
What is the average order value by product category in 2009?
Show quarterly revenue trend for 2008 and 2009
Which employees exceeded their sales quota in Q2 2009?
Show me a sales funnel: orders → shipped → revenue by territory
Compare monthly revenue between 2008 and 2009 by region
Give me a full customer demographic breakdown for the Pacific region
Show revenue by channel for 2009
Show me sales.
How are we doing this year?
Tell me about our customers.
What's the weather in Bangalore today?
Write me a poem about supply chains.
What is the meaning of life?
How do I reset my email password?
```

---

## What to expect in each block

- **A (8 queries):** rapid-fire PASS, ~25-40 s each on live stack, cumulative cost ~$0.05
- **B (5 queries):** 3 clean PASS + 2 that may PARTIAL under Render's 512 MB tier (funnel and demographic breakdown do heavy sub-query work — see [`docs/test_case_matrix.md`](test_case_matrix.md) for the specific limits)
- **C (3 queries):** all should return within ~2 s each — router is cheap, no SQL generation happens
- **D (4 queries):** all should return within ~1 s each — router rejects before any composer work

**Total ~15-20 minutes** to walk through all 20 in a live demo. Cost: under $0.10.

---

*See [`test_case_matrix.md`](test_case_matrix.md) for the full verbatim-PDF 8-TC audit with per-TC SQL and the gpt-4o-mini vs. gpt-4.1 A/B trajectory.*

# Mid-Sem Checkpoint Design — 20-day plan to viva on 16 June 2026

**Student:** Aniruddha Prakash Kawarase  ·  **BITS ID:** 2024AA05175
**Project:** Domain-Aware Multi-Agent NL-to-SQL for Enterprise Supply Chain Intelligence
**Plan date:** 2026-05-27 (T-20 days)  ·  **Viva date:** 2026-06-16

---

## 1.  Scope decision

This plan is for the **mid-sem checkpoint viva on 16 June**, not the final defense (which is 2 August). Mid-sem is a progress milestone; full Phase 8 (500-query benchmark), Phase 9 (production frontend), and Phase 10 (paper + dissertation) stay on the August track.

Confirmed in brainstorming session 2026-05-27:

| Decision | Choice |
|---|---|
| Ambition | Show progress (checkpoint scope) |
| Public benchmark | BIRD (per user request) — generic-mode sanity check |
| SCM-SQL benchmark size | 100 queries (current 50 + 50 new) |
| Demo UI | Next.js dashboard (MVP feature set) |
| UI features (MVP) | Chat input + SQL + results table + multi-turn history sidebar |
| UI features (stretch) | Per-call token cost, ambiguity-prompt cards |

---

## 2.  What is already done — do not re-do

| Asset | Path | Status |
|---|---|---|
| 5-layer multi-agent system | `backend/app/` | Phases 1-7 complete |
| SCM-SQL pilot benchmark (50 queries) | `benchmark/scm_sql_pilot/pilot_50.yaml` | Haiku 16.1 % vs MAC-SQL 8.9 % |
| Sonnet LLM ablation | `benchmark/scm_sql_pilot/RESULTS_sonnet.md` | L3 +20 pp, overall +1.8 pp |
| Spider 1.0 generic sanity check | `benchmark/spider1_sanity/RESULTS.md` | 100 % parse, 18 % EM |
| Mid-sem PPT v1 (9 slides) | `docs/viva/Midsem_Viva_2024AA05175.pptx` | Needs refresh with new numbers |
| Mid-sem report (3 font variants) | `docs/midsem/Midsem_Report_2024AA05175_*.docx` | Done |
| Terminal demo script | `scripts/midsem_demo.py` | 3 demos, 3 min, $0.04 |
| ANALYSIS / EVALUATION_FRAMEWORK | `benchmark/scm_sql_pilot/ANALYSIS.md`, `docs/eval/EVALUATION_FRAMEWORK.md` | Done with §1.5, §1.6, §2.5, §6.5 |

---

## 3.  Deliverables for mid-sem

### 3.1  Benchmark deliverables

**D1. BIRD generic-mode sanity check** (~0.5 day, ~$0.02)
- Pick 50-100 queries from BIRD dev via HuggingFace mirror
- Same single-prompt approach as Spider 1.0 sanity check (Router + Compliance + Composer bypassed)
- Output: `benchmark/bird_sanity/RESULTS.md` + new §1.7 in ANALYSIS.md
- Success criterion: ≥95 % structurally valid SQL, EM rate in published BIRD small-LLM band

**D2. SCM-SQL benchmark expansion: 50 → 100 queries** (~2 days)
- Author 50 new NL/SQL pairs against the live Odoo schema
- Distribution: +10 L1, +10 L2, +15 L3, +5 L4, +5 L5, +5 L6 (matches current proportions)
- All gold SQL verified to execute against the running Docker stack
- Output: `benchmark/scm_sql_pilot/pilot_100.yaml`

**D3. Re-run benchmark at expanded scale + new stats** (~0.5 day, ~$0.20)
- Run `scripts/run_evaluation.py` against the 100-query version with both Haiku and Sonnet
- Update `RESULTS.md` / `STATISTICS.md` / `ANALYSIS.md` with new numbers
- Expected outcome: lift remains positive on L2 / L3 / L6; bootstrap CIs tighten; Wilcoxon p drops but likely still >0.05 (full power needs n=500 in August)

### 3.2  Prototype deliverables

**D4. FastAPI gateway** (~1 day)
- Single endpoint `POST /ask` wrapping the existing orchestrator
- Request: `{query: string, session_id: string}`
- Response: streaming JSON with: intent, domains, SQL, executed result rows, token usage, latency
- Health endpoint `GET /healthz` returning Docker stack status
- Located at `backend/app/api/`
- Uvicorn entrypoint: `scripts/serve_api.py`

**D5. Next.js dashboard MVP** (~5 days)
- Single page (`/`) with:
  - Chat input bar at the bottom (Enter to send)
  - Main pane: streaming render of last response — SQL block, result table, EXPLAIN OK badge, latency
  - Left sidebar: list of past turns in the current session (clickable to re-display)
  - Top bar: "New session" button, model badge ("claude-haiku-4-5")
- Tech: Next.js 15 (App Router) + Tailwind + shadcn/ui table/card components
- No auth, no DB persistence — session lives in browser state only
- Located at `frontend/` (new directory)
- Stretch features (only if Day 9 finishes early):
  - Token-cost display per turn
  - Ambiguity-prompt clarification cards (when intent = `clarification_needed`)

### 3.3  Viva-prep deliverables

**D6. PPT refresh** (~0.5 day)
- Update slides with new 100-query numbers
- Add UI screenshot slide (1 new slide, position 7)
- Add LLM-ablation slide (1 new slide, position 8)
- Re-run `scripts/generate_midsem_pptx.py` after slide-content updates

**D7. Backup demo recording** (~0.5 day)
- Follow `docs/viva/MIDSEM_DEMO_RECORDING.md` instructions
- Record 3-minute MP4 of `scripts/midsem_demo.py` + brief UI walkthrough
- Save as `docs/viva/MIDSEM_DEMO_BACKUP.mp4`
- One copy on disk, one on USB stick

**D8. Rehearsal** (user's time, 2 days)
- 3 full dry-runs across Days 14-15, 18
- Watch `MIDSEM_DEMO_BACKUP.mp4` once between each dry-run

---

## 4.  Architecture — how the new pieces connect

### 4.1  Component diagram (text)

```
┌────────────────────────────────────────────────────────────────┐
│  Browser  (Next.js dashboard on localhost:3000)                │
│    ├── Chat input          → POST /ask                         │
│    ├── Multi-turn sidebar  ← session state (browser memory)    │
│    └── Result render       ← streaming JSON response           │
└──────────────────┬─────────────────────────────────────────────┘
                   │ HTTP/JSON
                   ▼
┌────────────────────────────────────────────────────────────────┐
│  FastAPI gateway  (uvicorn on localhost:8000)                  │
│    ├── /ask         calls Orchestrator.handle_query(...)       │
│    ├── /healthz     returns Docker stack health                │
│    └── /stream      SSE wrapper for streaming responses        │
└──────────────────┬─────────────────────────────────────────────┘
                   │ async function call (in-process)
                   ▼
┌────────────────────────────────────────────────────────────────┐
│  Orchestrator  (existing — no changes)                         │
│    Router → Specialists → Composer → Compliance → Validator    │
└──────────────────┬─────────────────────────────────────────────┘
                   │ asyncpg
                   ▼
┌────────────────────────────────────────────────────────────────┐
│  Postgres 16 + Odoo 17  (existing — Docker)                    │
└────────────────────────────────────────────────────────────────┘
```

### 4.2  Boundaries

| Component | Owns | Does NOT own |
|---|---|---|
| Frontend | session state in browser, render | LLM calls, schema knowledge, SQL execution |
| FastAPI gateway | HTTP serialization, request/response shape, CORS | business logic, multi-turn state |
| Orchestrator (existing) | agent coordination, multi-turn ConversationMemory, ambiguity detection | HTTP, UI |
| Postgres (existing) | data, RBAC enforcement | everything else |

The gateway is intentionally a thin adapter — no business logic. All architectural contributions remain in `backend/app/agents/` and `backend/app/composer/`. This means the gateway is also easy to swap (e.g., for the August final you can put it behind nginx or in Lambda).

### 4.3  Data shapes

**Request:**
```json
{
  "query": "Show top customers by revenue this quarter",
  "session_id": "uuid-v4-string"
}
```

**Response (non-streaming):**
```json
{
  "intent": "supply_chain_question",
  "domains": ["finance", "demand"],
  "sql": "WITH q_finance AS (...) SELECT ...;",
  "rows": [{"customer": "...", "revenue": 12345.67}, ...],
  "row_count": 25,
  "latency_ms": 5421,
  "token_usage": {"router": 150, "sql_gen": 1200, "validator": 80},
  "estimated_cost_usd": 0.0087,
  "explain_ok": true,
  "error": null
}
```

**Response (streaming, SSE):** events `intent`, `domains`, `sql`, `executing`, `result`, `cost`, `done`, `error`.

The MVP uses non-streaming (simpler). Streaming is a stretch goal.

---

## 5.  20-day calendar

| Day | Date | Item | Owner | Output | Slack |
|---|---|---|---|---|---|
| 1 | Wed 28 May | D1 BIRD sanity check | Claude | `benchmark/bird_sanity/RESULTS.md` |  |
| 2 | Thu 29 May | D2 SCM-SQL +50 queries (L1+L2+L3) | Claude | first 30 queries verified |  |
| 3 | Fri 30 May | D2 cont. (L4+L5+L6) + D3 run | Claude | `pilot_100.yaml` done + Haiku run done |  |
| 4 | Sat 31 May | D4 FastAPI gateway | Claude | `/ask` returns valid JSON |  |
| 5 | Sun 1 Jun | D5 Next.js scaffold + Tailwind + shadcn/ui | Claude | empty page renders, layout in place |  |
| 6 | Mon 2 Jun | D5 chat input + POST /ask wiring | Claude | typing a question prints SQL |  |
| 7 | Tue 3 Jun | D5 result table + EXPLAIN badge + latency | Claude | full single-turn loop works |  |
| 8 | Wed 4 Jun | D5 multi-turn sidebar + session state | Claude | sidebar populates across turns |  |
| 9 | Thu 5 Jun | D5 polish + (stretch) ambiguity-card UI | Claude | UI feels finished |  |
| 10 | Fri 6 Jun | D6 PPT refresh + UI screenshots | Claude | slides v2 |  |
| 11 | Sat 7 Jun | D7 demo recording | User | MP4 saved |  |
| 12 | Sun 8 Jun | **slack** |  |  | ✓ |
| 13 | Mon 9 Jun | **slack** |  |  | ✓ |
| 14 | Tue 10 Jun | D8 rehearsal #1 | User | dry-run ok |  |
| 15 | Wed 11 Jun | D8 rehearsal #2 | User | dry-run ok |  |
| 16 | Thu 12 Jun | **slack** |  |  | ✓ |
| 17 | Fri 13 Jun | **slack** |  |  | ✓ |
| 18 | Sat 14 Jun | D8 rehearsal #3 + light review | User | mock viva done |  |
| 19 | Sun 15 Jun | **slack** — read VIVA_PREP_OUTLINE once, then stop |  |  | ✓ |
| 20 | Mon 16 Jun | **VIVA DAY** | User |  |  |

**Committed work:** 11 days of Claude execution + 2 days of user rehearsal = 13.
**Slack:** 7 days. Comfortable.

---

## 6.  Error handling & testing strategy

| Layer | Failure mode | Recovery |
|---|---|---|
| LLM call (Haiku rate limit) | retry with exponential backoff in `LLMProvider` (existing) | already handled |
| LLM call (timeout) | fall back to `ollama/qwen2.5-coder:7b` via existing fallback chain | already handled |
| SQL execution (syntax error) | route back to originating agent for re-attempt (max 3) | already handled |
| Docker stack down | gateway `/healthz` returns 503; UI shows red banner | new (Day 4) |
| Frontend bug (chat won't send) | "Send" button stays disabled if input empty; show error toast on 5xx | new (Day 5-7) |
| User refreshes browser mid-session | session state lost (no persistence in MVP); explicit "new session" UX | accepted limitation |

**Testing:**
- Backend: existing 210 unit tests stay green
- Gateway: 3 new tests — `/ask` happy path, `/ask` bad input, `/healthz`
- Frontend: 1 Playwright smoke test — type "How many products?" → SQL appears → result table renders
- Benchmark: existing eval harness, no new tests needed for benchmark expansion

---

## 7.  Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Writing 50 new SCM-SQL queries takes longer than 2 days** | Medium | Slips Day 4+ | Hard cap: if not done by Day 3 close, ship with 75 queries (current 50 + 25 new) |
| **Next.js learning curve consumes Day 5 with no output** | Medium | Slips D5 | Use `create-next-app` template + shadcn/ui defaults; no custom design |
| **CORS / network issues between Next.js (3000) and FastAPI (8000)** | Medium | Slips Day 6 | Use Next.js API routes as a proxy if direct fetch is blocked |
| **Demo recording reveals a bug in the UI** | Low | Slips Day 11 | Day 12-13 slack absorbs one re-record |
| **Life event (illness, family)** | Low | Variable | 7-day slack absorbs it |
| **Panel asks for something Phase 8 / 10 deliverable** | Low | Embarrassing | Have the Aug 2 roadmap ready as a one-pager; honest "that's planned for July" answer |

---

## 8.  Out of scope (do NOT do)

- Phase 8 full 500-query benchmark — August final
- Phase 10 paper draft / dissertation chapters — August final
- Multi-user auth, deployment to public URL, SSL — local-only is fine for viva
- Mobile responsiveness / accessibility audit — desktop-only viva demo
- Real-time streaming of LLM tokens to the UI — non-streaming JSON is fine for MVP
- Persistence of multi-turn sessions across browser refreshes — accepted limitation
- Storybook / component library — single page, no design system needed
- Performance optimization beyond what already exists

The August 2 final scope picks up everything in this "out of scope" list.

---

## 9.  Success criteria for mid-sem viva

The viva is successful if **all** of these hold:

1. Demo runs end-to-end on viva-day laptop (terminal + UI both functional)
2. Panel sees the +7.1 pp Haiku result and the +20 pp Sonnet-L3 ablation result on a slide
3. Panel sees the BIRD and Spider 1.0 sanity-check rates on a slide
4. Panel sees the UI dashboard with one live query → SQL → result
5. Backup MP4 exists and works if Docker / network fails
6. User has rehearsed 3 times and can deliver the 1-paragraph summary cleanly
7. Honest answers to the panel's likely questions are documented in `MIDSEM_DEMO_NARRATION.md`

If 4 or 5 fail (UI or video doesn't work) the viva still passes on items 1-3 (existing results + terminal demo) — the UI is upside, not a single point of failure.

---

## 10.  Open questions resolved during brainstorm

| Q | Resolution |
|---|---|
| Mid-sem ambition? | Checkpoint scope, not final-defense scope |
| Public benchmark? | BIRD (replaces / extends the existing Spider 1.0 sanity check) |
| SCM-SQL size? | 100 queries (current 50 + 50 new) |
| UI tech? | Next.js dashboard |
| UI features? | Chat + SQL + results table + multi-turn sidebar (MVP); token cost + ambiguity cards (stretch) |

---

*Generated 2026-05-27 via /superpowers:brainstorming. Source artefacts: VIVA_PREP_OUTLINE.md, this session's progress (Haiku pilot, Sonnet ablation, Spider 1.0 sanity check), DEVELOPMENT_ROADMAP.md.*

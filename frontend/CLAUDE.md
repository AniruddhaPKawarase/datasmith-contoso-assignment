# CLAUDE.md — Frontend

## Stack
Next.js 14 (App Router) · TypeScript strict · TailwindCSS · Shadcn/ui · Zustand · React Markdown · React Syntax Highlighter

## Module Layout
```
app/
├── layout.tsx        Root layout (dark mode default)
├── page.tsx          Landing / health check (Phase 1)
├── chat/             Multi-turn chat UI (Phase 9)
├── sql/              SQL viewer + diff viewer
├── agents/           Agent activity timeline
└── api/              (route handlers if needed)

components/
├── ui/               Shadcn/ui primitives
├── chat/             ChatBox, MessageBubble, StreamingText
├── sql/              SqlViewer, SqlDiff, ResultTable
└── agent/            AgentTimeline, ConfidenceBar

lib/
├── api-client.ts     Typed FastAPI client
├── store.ts          Zustand session store
└── utils.ts          clsx + tw-merge helpers
```

## Coding Rules
1. **TypeScript strict** + `noUncheckedIndexedAccess`. No `any`. No `as` casts unless type-narrowing.
2. **Server components by default**. Mark `"use client"` only when interactivity demands it.
3. **No prop-drilling beyond 2 levels** — use Zustand for session state.
4. **Tailwind only**. No inline `style={{...}}` unless dynamic.
5. **One component per file** under `components/`. File name matches export.
6. **API calls** go through `lib/api-client.ts`. Never `fetch()` directly in components.

## Phase Roadmap
- Phase 1 (now) — health check page + skeleton
- Phase 9 — full chat UI + SQL panel + agent timeline + session sidebar

## Quality Gates
- `npm run lint` clean
- `npm run type-check` clean
- `npm run build` succeeds
- Dark mode default; light mode optional but must work
- Responsive: ≥ 320px (mobile) to ≥ 1440px (desktop)

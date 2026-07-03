"""Spider 1.0 generic-mode sanity check.

This is **not** a head-to-head architectural test — see EVALUATION_FRAMEWORK
§6.5 for the rationale. It is a single-prompt sanity check that confirms
our underlying LLM backbone (claude-haiku-4-5) can produce structurally
correct SQL on a public benchmark when the Router + Compliance + Composer
are bypassed (as Spider 1.0's single-domain queries would not exercise
them anyway).

Procedure:
    For each record in ``benchmark/spider1_sanity/spider_subset.jsonl``:
        1. Build prompt: SYSTEM = "You are a SQLite expert."
                          USER  = "Schema:\\n<DDL>\\n\\nQuestion: <NL>\\n\\n
                                   Return ONLY the SQL."
        2. Single call to claude-haiku-4-5 via LLMProvider.
        3. Score with sqlglot canonical EM (no DB execution required —
           the public mirror does not ship SQLite files).

Output:
    benchmark/spider1_sanity/RESULTS.md       per-query + headline EM rate
    benchmark/spider1_sanity/results.jsonl    one line per query

Run from project root:
    .venv\\Scripts\\python.exe scripts\\run_spider_sanity.py
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

env_path = ROOT / ".env"
if env_path.exists():
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

from app.eval import compute_em  # noqa: E402
from app.llm import LLMConfig, LLMProvider, ModelTask  # noqa: E402
from app.llm.token_tracker import TokenTracker  # noqa: E402

SUBSET = ROOT / "benchmark" / "spider1_sanity" / "spider_subset.jsonl"
RESULTS_JSONL = ROOT / "benchmark" / "spider1_sanity" / "results.jsonl"
RESULTS_MD = ROOT / "benchmark" / "spider1_sanity" / "RESULTS.md"

_SYSTEM_PROMPT = (
    "You are a SQLite expert. Given a database schema and a natural-"
    "language question, return ONLY the SQL query that answers it. "
    "Do not include explanations, markdown, or commentary — the response "
    "must be a single valid SQL statement."
)


def _build_user(schema: str, question: str) -> str:
    return f"Schema:\n{schema}\n\nQuestion: {question}\n\nSQL:"


_SQL_FENCE = re.compile(r"```(?:sql)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _extract_sql(raw: str) -> str:
    """Strip code-fence markers and trailing prose if the LLM emitted them."""
    if not raw:
        return ""
    m = _SQL_FENCE.search(raw)
    if m:
        return m.group(1).strip().rstrip(";")
    # No fence — assume the whole response is SQL; strip trailing prose
    # after the first semicolon if any.
    raw = raw.strip()
    if ";" in raw:
        raw = raw.split(";")[0]
    return raw.strip().rstrip(";")


async def main() -> int:
    if not SUBSET.exists():
        print(f"Missing {SUBSET}. Run scripts/spider_sample.py first.")
        return 1

    rows = [json.loads(line) for line in SUBSET.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"Spider 1.0 sanity check — {len(rows)} records")

    cfg = LLMConfig.from_env()
    provider = LLMProvider(cfg)
    tracker = TokenTracker()

    outcomes: list[dict] = []
    em_total = 0
    parse_ok_total = 0

    for r in rows:
        t0 = time.time()
        try:
            resp = await provider.generate(
                task=ModelTask.SQL_GEN,
                system=_SYSTEM_PROMPT,
                user=_build_user(r["schema"], r["question"]),
                temperature=0.0,
                max_tokens=512,
            )
            pred_sql = _extract_sql(resp.text)
            err = ""
            tracker.record(task=ModelTask.SQL_GEN, response=resp)
        except Exception as exc:
            pred_sql = ""
            err = str(exc)[:200]
        latency_ms = int((time.time() - t0) * 1000)

        em = compute_em(pred_sql, r["gold_sql"]) if pred_sql else 0
        # sqlglot-parseable counts separately so we can tell "wrote any
        # valid SQL" from "wrote SQL that exactly matches gold".
        try:
            import sqlglot

            sqlglot.parse_one(pred_sql, read="sqlite")
            parse_ok = 1
        except Exception:
            parse_ok = 0

        em_total += em
        parse_ok_total += parse_ok

        outcomes.append({
            "id": r["id"],
            "question": r["question"],
            "gold_sql": r["gold_sql"],
            "pred_sql": pred_sql,
            "em": em,
            "parse_ok": parse_ok,
            "latency_ms": latency_ms,
            "error": err,
        })
        print(f"  [{r['id']}]  EM={em}  parse_ok={parse_ok}  {r['question'][:60]}")

    await provider.aclose()

    # write jsonl
    RESULTS_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_JSONL, "w", encoding="utf-8") as f:
        for o in outcomes:
            f.write(json.dumps(o) + "\n")

    # write markdown
    em_rate = em_total / len(rows) if rows else 0.0
    parse_rate = parse_ok_total / len(rows) if rows else 0.0
    usage = tracker.snapshot()
    lines = [
        "# Spider 1.0 — Generic-Mode Sanity Check",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Records: {len(rows)}",
        f"Backbone: claude-haiku-4-5 (single-prompt; Router + Compliance + Composer bypassed)",
        f"Source: b-mc2/sql-create-context (public Spider 1.0 mirror with bundled schemas)",
        "",
        "## Headline",
        "",
        f"- **Exact Match (sqlglot canonical):  {em_rate*100:.1f} %** ({em_total}/{len(rows)})",
        f"- **Structurally valid SQL (sqlglot-parseable):  {parse_rate*100:.1f} %** ({parse_ok_total}/{len(rows)})",
        "",
        "## Interpretation",
        "",
        "Strict EM is famously brittle (column-name aliases, ORDER BY",
        "stability, equivalent JOIN orderings all break it). Published",
        "Spider 1.0 leaderboards use execution accuracy against the live",
        "SQLite databases — which the public mirror does not ship — and",
        "thus report 10-30 pp higher than the EM rate seen here. The",
        "parse-rate is the more useful sanity-check signal: it shows",
        "the LLM is producing structurally valid SQL against schemas it",
        "has not been specialised for. See EVALUATION_FRAMEWORK §6.5 for",
        "the full rationale on why this is a back-stop check rather than",
        "a competitive evaluation.",
        "",
        "## Token usage",
        "",
        "| Task | Model | Calls | Input | Output |",
        "|---|---|---|---|---|",
    ]
    grand_in = grand_out = 0
    for snap in usage:
        lines.append(
            f"| {snap.task.value} | {snap.model} | {snap.call_count} | "
            f"{snap.prompt_tokens} | {snap.completion_tokens} |"
        )
        grand_in += snap.prompt_tokens
        grand_out += snap.completion_tokens
    lines.append(f"| **Total** |  |  | **{grand_in}** | **{grand_out}** |")
    # Haiku pricing per Anthropic public rates: $1/M input, $5/M output
    cost = grand_in / 1_000_000 * 1.0 + grand_out / 1_000_000 * 5.0
    lines.append("")
    lines.append(f"Estimated cost: **${cost:.4f}**")

    RESULTS_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nEM = {em_total}/{len(rows)} ({em_rate*100:.1f} %)")
    print(f"Parse-OK = {parse_ok_total}/{len(rows)} ({parse_rate*100:.1f} %)")
    print(f"Cost ≈ ${cost:.4f}")
    print(f"Wrote {RESULTS_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

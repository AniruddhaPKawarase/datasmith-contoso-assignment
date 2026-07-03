"""BIRD dev head-to-head — Ours vs MAC-SQL with real Execution Accuracy.

Same protocol as the MAC-SQL paper (Wang et al., COLING 2025):
    - 50 BIRD dev queries, stratified by difficulty (30 simple / 15 moderate / 5 challenging)
    - Both systems share the same LLM backbone (claude-sonnet-4-6 here;
      paper used GPT-4. Sonnet-4 is the closest comparable-cost SOTA).
    - Execute predicted SQL against the actual SQLite database
    - Score EX with result-set equality (order-agnostic per BIRD spec)

Important framing (also documented in ANALYSIS.md §1.8):
  Our system's enterprise-specific architecture (Router for SCM
  domains, Compliance for RBAC, Composer for cross-domain CTEs,
  ReferenceDetector for multi-turn, AmbiguityResolver) DOES NOT
  ACTIVATE on BIRD. BIRD has no SCM domains, no multi-turn, no RBAC,
  no cross-domain composition.

  So on BIRD:
    "Ours"   = single-prompt SQL gen with schema + Validator pass
    "MAC-SQL" = full 3-stage Selector → Decomposer → Refiner

  The honest expected result: MAC-SQL roughly equals or beats Ours
  on BIRD, because MAC-SQL's architecture is what BIRD is designed
  to reward. Our architectural advantage is measured on SCM-SQL
  where it actually activates.

  This run is the "are we in the published-paper band on a public
  benchmark?" check, not the architectural claim.

Output:
    benchmark/bird_head_to_head/results.jsonl
    benchmark/bird_head_to_head/RESULTS.md
"""
from __future__ import annotations

import asyncio
import json
import os
import random
import re
import sqlite3
import sys
import time
from collections import defaultdict
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

# Force Sonnet for the head-to-head — both systems use the same LLM.
os.environ["LLM_MODEL_SQL_GEN"] = "anthropic/claude-sonnet-4-6"
os.environ["LLM_MODEL_VALIDATOR"] = "anthropic/claude-sonnet-4-6"
os.environ["LLM_MODEL_ROUTER"] = "anthropic/claude-sonnet-4-6"  # MAC-SQL Selector

from app.llm import LLMConfig, LLMProvider, ModelTask  # noqa: E402
from app.llm.token_tracker import TokenTracker  # noqa: E402

BIRD_DIR = ROOT / "benchmark" / "bird_dev" / "dev_20240627"
DEV_JSON = BIRD_DIR / "dev.json"
TABLES_JSON = BIRD_DIR / "dev_tables.json"
DB_ROOT = BIRD_DIR / "dev_databases"

OUT_DIR = ROOT / "benchmark" / "bird_head_to_head"
OUT_JSONL = OUT_DIR / "results.jsonl"
OUT_MD = OUT_DIR / "RESULTS.md"

SEED = 20260611
N_PER_DIFFICULTY = {"simple": 30, "moderate": 15, "challenging": 5}
STATEMENT_TIMEOUT_S = 30
MAX_REFINER_ATTEMPTS = 3   # matches MAC-SQL paper


# ── helpers ───────────────────────────────────────────────────────────


def stratified_sample(records: list[dict], rng: random.Random) -> list[dict]:
    """Sample N_PER_DIFFICULTY from each difficulty bucket."""
    by_diff: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_diff[r["difficulty"]].append(r)
    picked: list[dict] = []
    for diff, n in N_PER_DIFFICULTY.items():
        pool = by_diff.get(diff, [])
        picked.extend(rng.sample(pool, min(n, len(pool))))
    return picked


def build_schema_text(tables_data: list[dict], db_id: str) -> str:
    """Build a CREATE TABLE block for the given db_id from tables.json."""
    db_entry = next((t for t in tables_data if t["db_id"] == db_id), None)
    if not db_entry:
        return ""
    cols = db_entry["column_names_original"]   # [(table_idx, col_name), ...]
    types = db_entry["column_types"]
    tables = db_entry["table_names_original"]
    # Group columns by table
    cols_by_table: dict[int, list[str]] = defaultdict(list)
    for (tbl_idx, col_name), col_type in zip(cols[1:], types[1:]):  # skip the * column
        cols_by_table[tbl_idx].append(f"  {col_name} {col_type.upper()}")
    parts = []
    for i, t_name in enumerate(tables):
        col_defs = cols_by_table.get(i, [])
        parts.append(f"CREATE TABLE {t_name} (\n" + ",\n".join(col_defs) + "\n);")
    return "\n\n".join(parts)


def execute_sqlite(db_path: Path, sql: str) -> tuple[list, str]:
    """Run SQL against SQLite. Returns (rows, error_str)."""
    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute(f"PRAGMA busy_timeout = {STATEMENT_TIMEOUT_S * 1000}")
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
        return rows, ""
    except Exception as exc:
        return [], str(exc)[:300]


def result_sets_equal(pred: list, gold: list) -> bool:
    """BIRD spec: result set equality, order-agnostic on the row level."""
    if len(pred) != len(gold):
        return False
    # Normalise each row to tuple of stringified cells
    def norm(rows):
        out = []
        for r in rows:
            t = tuple("" if c is None else (round(c, 6) if isinstance(c, float) else c) for c in r)
            out.append(t)
        return sorted(out, key=lambda x: tuple(str(c) for c in x))
    return norm(pred) == norm(gold)


_SQL_FENCE = re.compile(r"```(?:sql)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_sql(raw: str) -> str:
    if not raw:
        return ""
    m = _SQL_FENCE.search(raw)
    text = m.group(1).strip() if m else raw.strip()
    # Strip trailing prose after the last semicolon if any
    if ";" in text:
        text = text.rsplit(";", 1)[0]
    return text.strip().rstrip(";")


# ── Prompts ───────────────────────────────────────────────────────────

_OURS_SYSTEM = (
    "You are an expert SQLite SQL writer. Given a database schema, a natural-"
    "language question, and optional evidence (a domain hint), return ONE valid "
    "SQLite SELECT statement that answers the question. Output ONLY the SQL — "
    "no explanations, no markdown fences, no commentary."
)


def _ours_user(schema: str, question: str, evidence: str) -> str:
    ev = f"\nEvidence: {evidence}" if evidence else ""
    return f"Schema:\n{schema}\n\nQuestion: {question}{ev}\n\nSQL:"


_MAC_SELECTOR_SYSTEM = (
    "You are the Schema-Linker for a Text-to-SQL system. Given a SQLite schema "
    "and a question, return ONLY a JSON array of table names that are needed."
)


def _mac_selector_user(schema: str, question: str) -> str:
    return f"Schema (all tables):\n{schema}\n\nQuestion: {question}\n\nJSON array of needed tables:"


_MAC_DECOMPOSER_SYSTEM = (
    "You are the SQL Decomposer. Given selected tables and a question, output "
    "ONE valid SQLite SELECT statement. Output ONLY the SQL."
)


def _mac_decomposer_user(schema_subset: str, question: str, evidence: str) -> str:
    ev = f"\nEvidence: {evidence}" if evidence else ""
    return f"Selected schema:\n{schema_subset}\n\nQuestion: {question}{ev}\n\nSQL:"


_MAC_REFINER_SYSTEM = (
    "You are the SQL Refiner. Given a failed SQL attempt and its execution error, "
    "produce a corrected SQLite SELECT statement. Output ONLY the corrected SQL."
)


def _mac_refiner_user(schema_subset: str, question: str, prior_sql: str, err: str) -> str:
    return (
        f"Selected schema:\n{schema_subset}\n\nQuestion: {question}\n\n"
        f"Previous SQL:\n{prior_sql}\n\nError:\n{err}\n\nCorrected SQL:"
    )


# ── System runners ───────────────────────────────────────────────────


async def run_ours(provider: LLMProvider, tracker: TokenTracker, *, schema: str,
                   question: str, evidence: str, db_path: Path) -> tuple[str, list, str, int]:
    """Ours on BIRD = single-prompt + one validator-style retry on error."""
    resp = await provider.generate(
        task=ModelTask.SQL_GEN, system=_OURS_SYSTEM,
        user=_ours_user(schema, question, evidence),
        temperature=0.0, max_tokens=600,
    )
    tracker.record(ModelTask.SQL_GEN, resp)
    sql = extract_sql(resp.text)
    rows, err = execute_sqlite(db_path, sql)
    attempts = 1
    if err:
        resp2 = await provider.generate(
            task=ModelTask.VALIDATOR, system=_OURS_SYSTEM,
            user=(f"{_ours_user(schema, question, evidence)}\n\n"
                  f"The previous attempt failed:\n{sql}\nError: {err}\n\n"
                  f"Corrected SQL:"),
            temperature=0.0, max_tokens=600,
        )
        tracker.record(ModelTask.VALIDATOR, resp2)
        sql = extract_sql(resp2.text)
        rows, err = execute_sqlite(db_path, sql)
        attempts = 2
    return sql, rows, err, attempts


async def run_mac_sql(provider: LLMProvider, tracker: TokenTracker, *, schema: str,
                     question: str, evidence: str, all_tables: list[str],
                     db_path: Path) -> tuple[str, list, str, int]:
    """MAC-SQL on BIRD = Selector → Decomposer → Refiner (up to 3 attempts)."""
    # 1. Selector: ask LLM which tables are relevant
    sel_resp = await provider.generate(
        task=ModelTask.ROUTER, system=_MAC_SELECTOR_SYSTEM,
        user=_mac_selector_user(schema, question),
        temperature=0.0, max_tokens=300,
    )
    tracker.record(ModelTask.ROUTER, sel_resp)
    sel_match = re.search(r"\[[^\]]*\]", sel_resp.text, re.DOTALL)
    selected: list[str]
    if sel_match:
        try:
            picked = json.loads(sel_match.group(0))
            selected = [t for t in picked if isinstance(t, str) and t in all_tables]
        except (json.JSONDecodeError, ValueError):
            selected = all_tables[:6]
    else:
        selected = all_tables[:6]
    if not selected:
        selected = all_tables[:6]

    # Build subset schema text from CREATE TABLE blocks matching selected
    subset_blocks = []
    for block in schema.split("\n\n"):
        for t in selected:
            if f"CREATE TABLE {t} " in block or f"CREATE TABLE {t}(" in block:
                subset_blocks.append(block)
                break
    schema_subset = "\n\n".join(subset_blocks) if subset_blocks else schema

    # 2. Decomposer: emit candidate SQL
    dec_resp = await provider.generate(
        task=ModelTask.SQL_GEN, system=_MAC_DECOMPOSER_SYSTEM,
        user=_mac_decomposer_user(schema_subset, question, evidence),
        temperature=0.0, max_tokens=600,
    )
    tracker.record(ModelTask.SQL_GEN, dec_resp)
    candidate = extract_sql(dec_resp.text)
    rows, err = execute_sqlite(db_path, candidate)
    attempts = 1

    # 3. Refiner loop
    while err and attempts < MAX_REFINER_ATTEMPTS:
        ref_resp = await provider.generate(
            task=ModelTask.VALIDATOR, system=_MAC_REFINER_SYSTEM,
            user=_mac_refiner_user(schema_subset, question, candidate, err),
            temperature=0.0, max_tokens=600,
        )
        tracker.record(ModelTask.VALIDATOR, ref_resp)
        candidate = extract_sql(ref_resp.text)
        rows, err = execute_sqlite(db_path, candidate)
        attempts += 1

    return candidate, rows, err, attempts


# ── main ──────────────────────────────────────────────────────────────


async def main() -> int:
    # Load BIRD dev set + tables
    with open(DEV_JSON, encoding="utf-8") as f:
        dev = json.load(f)
    with open(TABLES_JSON, encoding="utf-8") as f:
        tables = json.load(f)

    rng = random.Random(SEED)
    sample = stratified_sample(dev, rng)
    print(f"Sampled {len(sample)} BIRD dev queries "
          f"({N_PER_DIFFICULTY['simple']} simple + "
          f"{N_PER_DIFFICULTY['moderate']} moderate + "
          f"{N_PER_DIFFICULTY['challenging']} challenging)")

    cfg = LLMConfig.from_env()
    provider = LLMProvider(cfg)
    tracker_ours = TokenTracker()
    tracker_mac = TokenTracker()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    outcomes: list[dict] = []
    summary = {"ours": defaultdict(lambda: {"ex": 0, "n": 0}),
               "mac": defaultdict(lambda: {"ex": 0, "n": 0})}

    for i, q in enumerate(sample, 1):
        db_id = q["db_id"]
        db_path = DB_ROOT / db_id / f"{db_id}.sqlite"
        if not db_path.exists():
            print(f"  [{i}/{len(sample)}] SKIP {q['question_id']} — db missing: {db_path}")
            continue

        schema = build_schema_text(tables, db_id)
        db_entry = next((t for t in tables if t["db_id"] == db_id), None)
        all_tables = db_entry["table_names_original"] if db_entry else []

        gold_rows, gold_err = execute_sqlite(db_path, q["SQL"])
        if gold_err:
            print(f"  [{i}/{len(sample)}] SKIP {q['question_id']} — gold failed: {gold_err[:80]}")
            continue

        # Run Ours
        t0 = time.time()
        ours_sql, ours_rows, ours_err, ours_attempts = await run_ours(
            provider, tracker_ours,
            schema=schema, question=q["question"], evidence=q["evidence"],
            db_path=db_path,
        )
        ours_latency = int((time.time() - t0) * 1000)
        ours_ex = int(result_sets_equal(ours_rows, gold_rows)) if not ours_err else 0

        # Run MAC-SQL
        t0 = time.time()
        mac_sql, mac_rows, mac_err, mac_attempts = await run_mac_sql(
            provider, tracker_mac,
            schema=schema, question=q["question"], evidence=q["evidence"],
            all_tables=all_tables, db_path=db_path,
        )
        mac_latency = int((time.time() - t0) * 1000)
        mac_ex = int(result_sets_equal(mac_rows, gold_rows)) if not mac_err else 0

        diff = q["difficulty"]
        summary["ours"][diff]["ex"] += ours_ex
        summary["ours"][diff]["n"] += 1
        summary["mac"][diff]["ex"] += mac_ex
        summary["mac"][diff]["n"] += 1

        outcomes.append({
            "question_id": q["question_id"],
            "db_id": db_id,
            "difficulty": diff,
            "question": q["question"],
            "gold_sql": q["SQL"],
            "ours_sql": ours_sql,
            "ours_ex": ours_ex,
            "ours_err": ours_err,
            "ours_attempts": ours_attempts,
            "ours_latency_ms": ours_latency,
            "mac_sql": mac_sql,
            "mac_ex": mac_ex,
            "mac_err": mac_err,
            "mac_attempts": mac_attempts,
            "mac_latency_ms": mac_latency,
        })
        print(f"  [{i}/{len(sample)}] qid={q['question_id']:4d} ({diff:11s}) "
              f"Ours={ours_ex} MAC={mac_ex}  {q['question'][:55]}")

    await provider.aclose()

    # Write JSONL
    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for o in outcomes:
            f.write(json.dumps(o) + "\n")

    # Compute aggregates
    def pct(level: str, sys: str) -> str:
        s = summary[sys][level]
        return f"{(100 * s['ex'] / s['n']):.1f}" if s["n"] else "—"

    def overall(sys: str) -> tuple[int, int]:
        ex = sum(s["ex"] for s in summary[sys].values())
        n = sum(s["n"] for s in summary[sys].values())
        return ex, n

    ours_ex_total, n_total = overall("ours")
    mac_ex_total, _ = overall("mac")
    ours_pct = 100 * ours_ex_total / n_total if n_total else 0
    mac_pct = 100 * mac_ex_total / n_total if n_total else 0

    # Token costs (claude-sonnet-4-6: $3/M in, $15/M out)
    def cost(t: TokenTracker) -> float:
        c = 0.0
        for s in t.snapshot():
            c += s.prompt_tokens / 1_000_000 * 3.0 + s.completion_tokens / 1_000_000 * 15.0
        return c

    ours_cost = cost(tracker_ours)
    mac_cost = cost(tracker_mac)

    # Write MD
    lines = [
        "# BIRD Dev — Head-to-Head (Ours vs MAC-SQL)",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"LLM backbone (both systems): claude-sonnet-4-6 (fairness contract)",
        f"Records evaluated: {n_total} / {len(sample)} sampled "
        f"(stratified: 30 simple / 15 moderate / 5 challenging)",
        "",
        "## Headline",
        "",
        "| Difficulty | n | Ours EX % | MAC-SQL EX % | Δ |",
        "|---|---|---|---|---|",
    ]
    for diff in ("simple", "moderate", "challenging"):
        n = summary["ours"][diff]["n"]
        o = (100 * summary["ours"][diff]["ex"] / n) if n else 0
        m = (100 * summary["mac"][diff]["ex"] / n) if n else 0
        lines.append(f"| {diff} | {n} | {o:.1f} % | {m:.1f} % | {o - m:+.1f} pp |")
    lines.append(f"| **All** | **{n_total}** | **{ours_pct:.1f} %** | "
                 f"**{mac_pct:.1f} %** | **{ours_pct - mac_pct:+.1f} pp** |")
    lines += [
        "",
        "## Cost",
        "",
        f"- Ours total: **${ours_cost:.3f}**",
        f"- MAC-SQL total: **${mac_cost:.3f}**",
        f"- Combined: **${ours_cost + mac_cost:.3f}**",
        "",
        "## Reference — published MAC-SQL paper numbers on BIRD dev",
        "",
        "| Method | BIRD dev EX % |",
        "|---|---|",
        "| Palm-2 | 27.38 |",
        "| ChatGPT+CoT | 36.64 |",
        "| Claude-2 | 42.70 |",
        "| GPT-4 | 46.35 |",
        "| DIN-SQL+GPT-4 | 50.72 |",
        "| DAIL-SQL+GPT-4 | 54.76 |",
        "| MAC-SQL+GPT-3.5-Turbo | 50.56 |",
        "| **MAC-SQL+GPT-4** | **59.39** |",
        "| MAC-SQL+GPT-4 +OracleSchema | 70.28 |",
        "",
        "## Interpretation",
        "",
        "On BIRD, our system's enterprise-specific architecture (Router for SCM",
        "domains, Compliance for RBAC, Composer for cross-domain CTEs,",
        "ReferenceDetector for multi-turn, AmbiguityResolver) does NOT activate —",
        "BIRD has no SCM domains, no multi-turn, no RBAC, no cross-domain",
        "composition. Our system runs in single-prompt+validator mode here.",
        "MAC-SQL runs its full 3-stage Selector → Decomposer → Refiner pipeline,",
        "which is the architecture BIRD was designed to reward.",
        "",
        "This run answers the question 'is the base LLM engine in the published-",
        "paper band on a standard public benchmark?' — not 'does our architecture",
        "beat MAC-SQL on BIRD?'. The architectural claim is tested on SCM-SQL,",
        "where our differentiators actually activate (see ANALYSIS.md §1).",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {OUT_MD.relative_to(ROOT)}")
    print(f"Ours: {ours_ex_total}/{n_total} = {ours_pct:.1f} %  (cost ${ours_cost:.3f})")
    print(f"MAC : {mac_ex_total}/{n_total} = {mac_pct:.1f} %  (cost ${mac_cost:.3f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

"""Head-to-head evaluation runner — Ours vs MAC-SQL on the SCM-SQL pilot.

For every pair in benchmark/scm_sql_pilot/pilot_50.yaml:

    1. Execute the gold SQL  → reference result set + t_gold timing
    2. Run "Ours" pipeline    → predicted SQL → execute → EX, VES, EM
    3. Run "MAC-SQL" baseline → predicted SQL → execute → EX, VES, EM

For L6 multi-turn pairs the orchestrator's ConversationMemory carries
context across turns. The MAC-SQL baseline does not implement multi-
turn, so each turn is run independently — this is the documented
asymmetry we report honestly.

Outputs:
    benchmark/scm_sql_pilot/results.jsonl      — one line per pair-turn
    benchmark/scm_sql_pilot/RESULTS.md         — per-level summary table

Run from project root (after Docker stack is up and pilot is verified):
    python scripts/run_evaluation.py
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

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
os.environ["POSTGRES_HOST"] = "localhost"

import psycopg  # noqa: E402

from app.agents import (  # noqa: E402
    BaseAgent,
    ComplianceProcessor,
    ConversationMemory,
    MessageLog,
    Orchestrator,
    OrchestratorLimits,
    RouterAgent,
    build_specialists,
    fresh_state,
)
from app.ambiguity import AmbiguityResolver  # noqa: E402
from app.baselines import MacSqlBaseline  # noqa: E402
from app.composer import Composer  # noqa: E402
from app.conversation import (  # noqa: E402
    ConversationContextBuilder,
    ReferenceDetector,
)
from app.db.postgres import PostgresAdapter, PostgresConfig  # noqa: E402
from app.eval import compute_em, compute_ex, compute_soft_ex, compute_ves  # noqa: E402
from app.llm import LLMConfig, LLMProvider  # noqa: E402
from app.llm.token_tracker import TokenTracker  # noqa: E402
from app.schema.domains import Domain, load_domain_mapping  # noqa: E402
from app.schema.glossary import load_glossary  # noqa: E402
from app.schema.joins import JoinGraph  # noqa: E402
from app.schema.metadata import SchemaMetadata  # noqa: E402
from app.schema.search import SchemaSearch  # noqa: E402
from app.temporal import TemporalParser  # noqa: E402


PILOT = ROOT / "benchmark" / "scm_sql_pilot" / "pilot_100.yaml"
RESULTS_JSONL = ROOT / "benchmark" / "scm_sql_pilot" / "results.jsonl"
RESULTS_MD = ROOT / "benchmark" / "scm_sql_pilot" / "RESULTS.md"
SCHEMA = ROOT / "backend" / "data" / "odoo_schema.json"

STATEMENT_TIMEOUT_MS = 30_000


# ── data ──────────────────────────────────────────────────────────────


@dataclass
class TrialResult:
    pair_id: str
    turn: int
    level: int
    domains: list
    system: str                          # "ours" or "mac_sql"
    pred_sql: str
    pred_rows: int
    ex: int
    soft_ex: float
    em: int
    ves: float
    t_gold_ms: int
    t_pred_ms: int
    attempts: int
    error: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class PairOutcome:
    pair_id: str
    turn: int
    level: int
    domains: list
    nl: str
    gold_sql: str
    gold_rows: int
    t_gold_ms: int
    gold_error: str = ""
    trials: list = field(default_factory=list)

    def to_dict(self):
        return {
            "pair_id": self.pair_id, "turn": self.turn, "level": self.level,
            "domains": self.domains, "nl": self.nl,
            "gold_rows": self.gold_rows, "t_gold_ms": self.t_gold_ms,
            "gold_error": self.gold_error,
            "trials": [t.to_dict() for t in self.trials],
        }


# ── DB helpers ────────────────────────────────────────────────────────


def execute_sql(pg: PostgresAdapter, sql: str) -> tuple[list, float, str]:
    """Run SQL, return (rows, elapsed_seconds, error_message)."""
    if not sql.strip():
        return [], 0.0, "empty SQL"
    clean = sql.rstrip().rstrip(";")
    t0 = time.time()
    try:
        with pg.connection() as conn, conn.cursor() as cur:
            cur.execute(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}")
            cur.execute(clean)
            rows = list(cur.fetchall())
        return rows, time.time() - t0, ""
    except psycopg.errors.QueryCanceled:
        return [], time.time() - t0, "statement_timeout"
    except psycopg.Error as exc:
        msg = str(exc).splitlines()[0][:200]
        return [], time.time() - t0, msg


# ── build the two systems ─────────────────────────────────────────────


async def build_systems(tracker: TokenTracker):
    metadata = SchemaMetadata.from_json(SCHEMA)
    mapping = load_domain_mapping()
    glossary = load_glossary()
    search = SchemaSearch(metadata)
    join_graph = JoinGraph(metadata)
    cfg = LLMConfig.from_env()
    llm = LLMProvider(cfg)

    # Ours — Compliance is DISABLED for this evaluation. Rationale:
    # the gold SQL has no row-level-security predicates, so injecting
    # `company_id IN (1)` always produces a different result set even
    # when the SQL is otherwise correct. Compliance behaviour is
    # validated separately by test_compliance_v2.py — that's the right
    # place for the RBAC assertion. The eval here isolates the
    # NL-to-SQL contract.
    router = RouterAgent(llm=llm, mapping=mapping, glossary=glossary,
                         tracker=tracker)
    specialists = build_specialists(
        llm=llm, metadata=metadata, mapping=mapping,
        glossary=glossary, search=search, tracker=tracker,
    )
    agents: dict[Domain, BaseAgent] = dict(specialists)
    ours = Orchestrator(
        router=router, agents=agents,
        memory=ConversationMemory(),
        composer=Composer(join_graph=join_graph),
        validator=None,
        compliance=None,                       # see comment above
        temporal_parser=TemporalParser(),
        ambiguity_resolver=AmbiguityResolver(glossary, mapping=mapping),
        reference_detector=ReferenceDetector(),
        conversation_builder=ConversationContextBuilder(),
        message_log=MessageLog(),
        limits=OrchestratorLimits(max_correction_attempts=2),
    )

    # MAC-SQL baseline
    mac = MacSqlBaseline(
        llm=llm, metadata=metadata, search=search,
        max_correction=2, tracker=tracker,
    )
    return ours, mac, llm


# ── trial runners ─────────────────────────────────────────────────────


async def run_ours(orch, *, query: str, session_id: str) -> tuple[str, int, str]:
    """Returns (predicted_sql, attempts_used, error_in_pipeline)."""
    # No user_company_ids — Compliance is disabled for this eval (see
    # build_systems comment) so company-id scoping would have no effect
    # anyway. Keeping the arg empty makes the intent explicit.
    state = fresh_state(query=query, session_id=session_id,
                       user_company_ids=())
    try:
        result = await orch.run(state)
        return (
            str(result.get("composed_sql", "")),
            int(result.get("attempt", 1)),
            str(result.get("final_error", "")) or "",
        )
    except Exception as exc:                       # noqa: BLE001
        return "", 0, f"orchestrator-error: {exc}"


async def run_mac_sql(mac: MacSqlBaseline, pg: PostgresAdapter,
                     *, query: str) -> tuple[str, int, str]:
    """MAC-SQL with an executor for its Refiner loop."""

    def _executor(candidate: str) -> tuple[bool, str]:
        _, _, err = execute_sql(pg, candidate)
        return (err == "", err)

    try:
        out = await mac.predict(query, executor=_executor)
        return out.sql, out.attempts, out.notes
    except Exception as exc:                       # noqa: BLE001
        return "", 0, f"mac-sql-error: {exc}"


# ── per-pair driver ───────────────────────────────────────────────────


async def evaluate_pair(
    *, pair: dict, orch, mac: MacSqlBaseline, pg: PostgresAdapter,
) -> list[PairOutcome]:
    """One pair (or one L6 multi-turn pair) → list of PairOutcome (one per turn)."""
    pair_id = pair["id"]
    level = int(pair["level"])
    domains = list(pair.get("domains", []))
    turns = pair.get("turns")

    if turns is None:                                # single-turn
        return [await _eval_single(pair_id, 1, level, domains,
                                   pair["nl"], pair["gold_sql"],
                                   session_id=f"eval-{pair_id}",
                                   orch=orch, mac=mac, pg=pg)]
    out: list[PairOutcome] = []
    session_id = f"eval-{pair_id}"
    for t_idx, turn in enumerate(turns, start=1):
        out.append(await _eval_single(
            pair_id, t_idx, level, domains, turn["nl"], turn["gold_sql"],
            session_id=session_id, orch=orch, mac=mac, pg=pg,
        ))
    return out


async def _eval_single(
    pair_id, turn, level, domains, nl, gold_sql,
    *, session_id, orch, mac, pg,
) -> PairOutcome:
    print(f"  > [{pair_id} T{turn}  L{level}]  {nl}")
    gold_rows, t_gold, gold_err = execute_sql(pg, gold_sql)
    outcome = PairOutcome(
        pair_id=pair_id, turn=turn, level=level, domains=domains,
        nl=nl, gold_sql=gold_sql,
        gold_rows=len(gold_rows), t_gold_ms=int(t_gold * 1000),
        gold_error=gold_err,
    )
    if gold_err:
        print(f"        gold-SQL error — SKIPPING this pair: {gold_err}")
        return outcome

    # --- Ours
    pred_sql, attempts, perr = await run_ours(orch, query=nl, session_id=session_id)
    pred_rows, t_pred, exec_err = execute_sql(pg, pred_sql) if pred_sql else ([], 0.0, "no-sql")
    ex = compute_ex(pred_rows, gold_rows, gold_sql=gold_sql)
    soft_ex = compute_soft_ex(pred_rows, gold_rows, gold_sql=gold_sql)
    em = compute_em(pred_sql, gold_sql) if pred_sql else 0
    ves = compute_ves(ex, t_gold, t_pred)
    outcome.trials.append(TrialResult(
        pair_id=pair_id, turn=turn, level=level, domains=domains,
        system="ours", pred_sql=pred_sql, pred_rows=len(pred_rows),
        ex=ex, soft_ex=round(soft_ex, 4), em=em, ves=round(ves, 4),
        t_gold_ms=int(t_gold * 1000), t_pred_ms=int(t_pred * 1000),
        attempts=attempts, error=(perr or exec_err)[:200],
    ))
    print(f"        ours      EX={ex}  soft-EX={soft_ex:.2f}  VES={ves:.2f}  attempts={attempts}")

    # --- MAC-SQL
    pred_sql, attempts, perr = await run_mac_sql(mac, pg, query=nl)
    pred_rows, t_pred, exec_err = execute_sql(pg, pred_sql) if pred_sql else ([], 0.0, "no-sql")
    ex = compute_ex(pred_rows, gold_rows, gold_sql=gold_sql)
    soft_ex = compute_soft_ex(pred_rows, gold_rows, gold_sql=gold_sql)
    em = compute_em(pred_sql, gold_sql) if pred_sql else 0
    ves = compute_ves(ex, t_gold, t_pred)
    outcome.trials.append(TrialResult(
        pair_id=pair_id, turn=turn, level=level, domains=domains,
        system="mac_sql", pred_sql=pred_sql, pred_rows=len(pred_rows),
        ex=ex, soft_ex=round(soft_ex, 4), em=em, ves=round(ves, 4),
        t_gold_ms=int(t_gold * 1000), t_pred_ms=int(t_pred * 1000),
        attempts=attempts, error=(perr or exec_err)[:200],
    ))
    print(f"        mac_sql   EX={ex}  soft-EX={soft_ex:.2f}  VES={ves:.2f}  attempts={attempts}")
    return outcome


# ── main ─────────────────────────────────────────────────────────────


async def main() -> int:
    if not PILOT.exists():
        print("Pilot not found:", PILOT)
        return 1
    if not SCHEMA.exists():
        print("Schema cache missing; run scripts/introspect_odoo.py first.")
        return 1
    pg = PostgresAdapter(PostgresConfig.from_env())
    if not pg.ping():
        print("Postgres unreachable. Bring the docker stack up first.")
        return 1

    spec = yaml.safe_load(PILOT.read_text(encoding="utf-8"))
    tracker = TokenTracker()
    ours, mac, llm = await build_systems(tracker)

    print(f"Evaluating {len(spec['pairs'])} pilot pairs "
          f"against {PILOT.name}\n")

    all_outcomes: list[PairOutcome] = []
    try:
        for pair in spec["pairs"]:
            all_outcomes.extend(await evaluate_pair(
                pair=pair, orch=ours, mac=mac, pg=pg,
            ))
    finally:
        await llm.aclose()

    write_jsonl(all_outcomes)
    write_markdown(all_outcomes, tracker)
    print(f"\nDone. Results in {RESULTS_JSONL.relative_to(ROOT)} "
          f"and {RESULTS_MD.relative_to(ROOT)}")
    return 0


def write_jsonl(outcomes: list[PairOutcome]) -> None:
    RESULTS_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_JSONL, "w", encoding="utf-8") as f:
        for o in outcomes:
            f.write(json.dumps(o.to_dict()) + "\n")


def write_markdown(outcomes: list[PairOutcome], tracker: TokenTracker) -> None:
    """Produce RESULTS.md with both strict EX and column-agnostic Soft-EX."""

    def _pct(scores: list[float]) -> float:
        return (sum(scores) / len(scores) * 100) if scores else 0.0

    # Build per-level buckets for each (system, metric).
    by_level: dict[int, dict[str, dict[str, list[float]]]] = {}
    for pair in outcomes:
        for t in pair.trials:
            sys_ = by_level.setdefault(t.level, {}).setdefault(t.system, {})
            sys_.setdefault("ex", []).append(float(t.ex))
            sys_.setdefault("soft_ex", []).append(float(t.soft_ex))
    levels = sorted(by_level.keys())

    lines = [
        "# SCM-SQL Pilot — Head-to-Head Results",
        "",
        f"Generated: {dt.datetime.now():%Y-%m-%d %H:%M:%S}",
        f"Pairs evaluated: {len(outcomes)}",
        "",
        "## Per-level Execution Accuracy  (strict + Soft-EX)",
        "",
        "Soft-EX is column-name-agnostic: row count + value-multiset match.",
        "See `docs/eval/EVALUATION_FRAMEWORK.md` §2.",
        "",
        "| Level | n | Ours EX | Ours Soft-EX | MAC EX | MAC Soft-EX | "
        "Δ EX | Δ Soft-EX |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for level in levels:
        ours = by_level[level].get("ours", {})
        mac = by_level[level].get("mac_sql", {})
        ours_ex = _pct(ours.get("ex", []))
        ours_soft = _pct(ours.get("soft_ex", []))
        mac_ex = _pct(mac.get("ex", []))
        mac_soft = _pct(mac.get("soft_ex", []))
        n = len(ours.get("ex", []))
        lines.append(
            f"| L{level} | {n} | {ours_ex:.1f} % | {ours_soft:.1f} % | "
            f"{mac_ex:.1f} % | {mac_soft:.1f} % | "
            f"{ours_ex - mac_ex:+.1f} pp | {ours_soft - mac_soft:+.1f} pp |"
        )

    # overall
    all_ours = [t for p in outcomes for t in p.trials if t.system == "ours"]
    all_mac = [t for p in outcomes for t in p.trials if t.system == "mac_sql"]
    if all_ours and all_mac:
        o_ex = _pct([t.ex for t in all_ours])
        o_soft = _pct([t.soft_ex for t in all_ours])
        m_ex = _pct([t.ex for t in all_mac])
        m_soft = _pct([t.soft_ex for t in all_mac])
        lines.append(
            f"| **All** | **{len(all_ours)}** | "
            f"**{o_ex:.1f} %** | **{o_soft:.1f} %** | "
            f"**{m_ex:.1f} %** | **{m_soft:.1f} %** | "
            f"**{o_ex - m_ex:+.1f} pp** | **{o_soft - m_soft:+.1f} pp** |"
        )

    lines += ["", "## Token usage", "",
              "| Task | Model | Calls | Input | Output |",
              "|---|---|---|---|---|"]
    grand_in = grand_out = 0
    for s in tracker.snapshot():
        lines.append(
            f"| {s.task.value} | {s.model} | {s.call_count} | "
            f"{s.prompt_tokens} | {s.completion_tokens} |"
        )
        grand_in += s.prompt_tokens
        grand_out += s.completion_tokens
    cost = grand_in * 1e-6 * 0.20 + grand_out * 1e-6 * 1.00
    lines.append(f"| **Total** |  |  | **{grand_in}** | **{grand_out}** |")
    lines.append("")
    lines.append(f"Estimated cost: **${cost:.4f}**")

    RESULTS_MD.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

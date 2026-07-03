"""Verify every gold SQL in the SCM-SQL pilot executes against live Postgres.

Reads benchmark/scm_sql_pilot/pilot_50.yaml, runs each gold_sql with a
30 s statement timeout, and reports:
    pass   — executed cleanly, returned ≥ 1 row
    empty  — executed cleanly, returned 0 rows (recorded as pass-empty)
    error  — Postgres raised an error  (these MUST be fixed)
    timeout — statement_timeout fired

Outputs a JSONL log to benchmark/scm_sql_pilot/verification.jsonl and
a markdown summary to benchmark/scm_sql_pilot/VERIFICATION.md.

For multi-turn (L6) pairs, every turn's gold_sql is verified
independently — the script does not chain turns; the verification
only checks the SQL is syntactically and semantically valid Postgres
against the live demo data.

Run from project root:
    python scripts/verify_pilot.py
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
from dataclasses import dataclass
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

from app.db.postgres import PostgresAdapter, PostgresConfig  # noqa: E402

import psycopg  # noqa: E402

_PILOT_NAME = sys.argv[1] if len(sys.argv) > 1 else "pilot_50.yaml"
PILOT = ROOT / "benchmark" / "scm_sql_pilot" / _PILOT_NAME
_STEM = PILOT.stem
OUT_JSONL = ROOT / "benchmark" / "scm_sql_pilot" / f"verification_{_STEM}.jsonl"
OUT_MD = ROOT / "benchmark" / "scm_sql_pilot" / f"VERIFICATION_{_STEM}.md"

STATEMENT_TIMEOUT_MS = 30_000


@dataclass(frozen=True)
class Outcome:
    pair_id: str
    turn: int                # 1 for single-turn pairs; 1..N for L6
    level: int
    domains: tuple[str, ...]
    status: str              # "pass" | "pass-empty" | "error" | "timeout"
    row_count: int
    elapsed_ms: int
    error_message: str = ""

    def to_dict(self) -> dict:
        return {
            "pair_id": self.pair_id,
            "turn": self.turn,
            "level": self.level,
            "domains": list(self.domains),
            "status": self.status,
            "row_count": self.row_count,
            "elapsed_ms": self.elapsed_ms,
            "error_message": self.error_message,
        }


def execute_one(pg: PostgresAdapter, sql: str) -> Outcome:
    """Run one SQL with timeout and return a partial Outcome (caller fills meta)."""
    t0 = time.time()
    try:
        with pg.connection() as conn, conn.cursor() as cur:
            cur.execute(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}")
            cur.execute(sql.rstrip().rstrip(";"))
            rows = cur.fetchall()
        elapsed = int((time.time() - t0) * 1000)
        if rows:
            return Outcome(
                pair_id="", turn=0, level=0, domains=(),
                status="pass", row_count=len(rows), elapsed_ms=elapsed,
            )
        return Outcome(
            pair_id="", turn=0, level=0, domains=(),
            status="pass-empty", row_count=0, elapsed_ms=elapsed,
        )
    except psycopg.errors.QueryCanceled:
        return Outcome(
            pair_id="", turn=0, level=0, domains=(),
            status="timeout", row_count=0,
            elapsed_ms=int((time.time() - t0) * 1000),
            error_message="statement_timeout exceeded",
        )
    except psycopg.Error as exc:
        return Outcome(
            pair_id="", turn=0, level=0, domains=(),
            status="error", row_count=0,
            elapsed_ms=int((time.time() - t0) * 1000),
            error_message=str(exc).splitlines()[0][:300],
        )


def main() -> int:
    if not PILOT.exists():
        print(f"Pilot file not found: {PILOT}")
        return 1

    spec = yaml.safe_load(PILOT.read_text(encoding="utf-8"))
    pg = PostgresAdapter(PostgresConfig.from_env())
    if not pg.ping():
        print("Postgres is not reachable. Start the stack first:")
        print("    docker compose -f docker/docker-compose.yml up -d postgres odoo")
        return 1

    outcomes: list[Outcome] = []
    print(f"Verifying {len(spec['pairs'])} pilot pairs against live Postgres")
    print(f"Statement timeout: {STATEMENT_TIMEOUT_MS} ms\n")

    for pair in spec["pairs"]:
        pair_id = pair["id"]
        level = int(pair["level"])
        domains = tuple(pair.get("domains", ()))

        if "turns" in pair:                                # L6 multi-turn
            for t_idx, turn in enumerate(pair["turns"], start=1):
                outcome = execute_one(pg, turn["gold_sql"])
                outcome = Outcome(
                    pair_id=pair_id, turn=t_idx, level=level, domains=domains,
                    status=outcome.status, row_count=outcome.row_count,
                    elapsed_ms=outcome.elapsed_ms,
                    error_message=outcome.error_message,
                )
                outcomes.append(outcome)
                _print_row(outcome)
        else:
            outcome = execute_one(pg, pair["gold_sql"])
            outcome = Outcome(
                pair_id=pair_id, turn=1, level=level, domains=domains,
                status=outcome.status, row_count=outcome.row_count,
                elapsed_ms=outcome.elapsed_ms,
                error_message=outcome.error_message,
            )
            outcomes.append(outcome)
            _print_row(outcome)

    write_jsonl(outcomes)
    write_markdown(outcomes)
    return _summary_exit_code(outcomes)


def _print_row(o: Outcome) -> None:
    badge = {
        "pass":       "OK     ",
        "pass-empty": "OK[0]  ",
        "error":      "ERROR  ",
        "timeout":    "TIMEOUT",
    }[o.status]
    turn_str = f"T{o.turn}" if o.turn > 1 else "  "
    print(f"  {badge}  {o.pair_id} {turn_str:>3}  L{o.level}  "
          f"rows={o.row_count:<5}  {o.elapsed_ms:>5} ms"
          + (f"   {o.error_message}" if o.error_message else ""))


def write_jsonl(outcomes: list[Outcome]) -> None:
    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for o in outcomes:
            f.write(json.dumps(o.to_dict()) + "\n")
    print(f"\nWrote {OUT_JSONL.relative_to(ROOT)}")


def write_markdown(outcomes: list[Outcome]) -> None:
    by_status: dict[str, int] = {}
    by_level: dict[int, dict[str, int]] = {}
    for o in outcomes:
        by_status[o.status] = by_status.get(o.status, 0) + 1
        by_level.setdefault(o.level, {})
        by_level[o.level][o.status] = by_level[o.level].get(o.status, 0) + 1

    md = [
        "# SCM-SQL Pilot Verification Report",
        "",
        f"Generated: {dt.datetime.now():%Y-%m-%d %H:%M:%S}",
        f"Total SQL statements verified: **{len(outcomes)}**",
        "",
        "## Overall outcome",
        "",
        "| Status | Count |",
        "|---|---|",
    ]
    for status in ("pass", "pass-empty", "error", "timeout"):
        md.append(f"| {status} | {by_status.get(status, 0)} |")

    md += ["", "## Per-level outcome", "",
           "| Level | pass | pass-empty | error | timeout | total |",
           "|---|---|---|---|---|---|"]
    for level in sorted(by_level.keys()):
        row = by_level[level]
        total = sum(row.values())
        md.append(
            f"| L{level} | {row.get('pass', 0)} | {row.get('pass-empty', 0)} "
            f"| {row.get('error', 0)} | {row.get('timeout', 0)} | {total} |"
        )

    errs = [o for o in outcomes if o.status == "error"]
    if errs:
        md += ["", "## Errors needing fix", "",
               "| Pair | Turn | Level | Error |",
               "|---|---|---|---|"]
        for o in errs:
            md.append(f"| `{o.pair_id}` | {o.turn} | L{o.level} | {o.error_message} |")

    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {OUT_MD.relative_to(ROOT)}")


def _summary_exit_code(outcomes: list[Outcome]) -> int:
    errors = sum(1 for o in outcomes if o.status == "error")
    timeouts = sum(1 for o in outcomes if o.status == "timeout")
    passes = sum(1 for o in outcomes if o.status in ("pass", "pass-empty"))
    print()
    print(f"Summary: {passes} pass, {errors} error, {timeouts} timeout")
    return 0 if (errors + timeouts) == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

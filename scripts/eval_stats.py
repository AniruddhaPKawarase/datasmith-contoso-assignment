"""Statistical analysis of the head-to-head results.

Consumes ``benchmark/scm_sql_pilot/results.jsonl`` (produced by
``run_evaluation.py``) and computes:

  * Per-level EX with 95 % bootstrap CI (n = 1 000 resamples).
  * Paired EX delta (ours − MAC-SQL) with 95 % CI.
  * Wilcoxon signed-rank p (paired, non-parametric).
  * Bonferroni-corrected p across the 6 level comparisons.
  * Cliff's δ effect size.

All measures are documented in docs/eval/EVALUATION_FRAMEWORK.md §8.
Numbers go to benchmark/scm_sql_pilot/STATISTICS.md.

Run AFTER ``scripts/run_evaluation.py``.
"""
from __future__ import annotations

import json
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_JSONL = ROOT / "benchmark" / "scm_sql_pilot" / "results.jsonl"
STATS_MD = ROOT / "benchmark" / "scm_sql_pilot" / "STATISTICS.md"

N_BOOTSTRAP = 1_000
ALPHA = 0.05
RNG = random.Random(20260616)               # midsem date — deterministic seed


# ── data ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Paired:
    level: int
    ours_ex: int
    mac_ex: int
    ours_soft: float
    mac_soft: float


def load_paired() -> list[Paired]:
    if not RESULTS_JSONL.exists():
        print(f"Missing {RESULTS_JSONL} — run scripts/run_evaluation.py first.")
        sys.exit(1)
    paired: list[Paired] = []
    with open(RESULTS_JSONL, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            ours_ex = mac_ex = None
            ours_soft = mac_soft = None
            for t in rec["trials"]:
                if t["system"] == "ours":
                    ours_ex = t["ex"]
                    ours_soft = t.get("soft_ex", 0.0)
                elif t["system"] == "mac_sql":
                    mac_ex = t["ex"]
                    mac_soft = t.get("soft_ex", 0.0)
            if ours_ex is None or mac_ex is None:
                continue                      # gold SQL failed; skip the pair
            paired.append(Paired(
                level=rec["level"],
                ours_ex=ours_ex, mac_ex=mac_ex,
                ours_soft=ours_soft or 0.0, mac_soft=mac_soft or 0.0,
            ))
    return paired


# ── statistics ────────────────────────────────────────────────────────


def mean(xs: list[int | float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def bootstrap_ci(xs: list[int | float], n: int = N_BOOTSTRAP,
                 alpha: float = ALPHA) -> tuple[float, float, float]:
    """Return (mean, ci_low, ci_high)."""
    if not xs:
        return 0.0, 0.0, 0.0
    m = mean(xs)
    samples = []
    L = len(xs)
    for _ in range(n):
        resample = [xs[RNG.randrange(L)] for _ in range(L)]
        samples.append(mean(resample))
    samples.sort()
    lo = samples[int((alpha / 2) * n)]
    hi = samples[int((1 - alpha / 2) * n)]
    return m, lo, hi


def wilcoxon_signed_rank(diffs: list[float]) -> tuple[float, float]:
    """Two-sided Wilcoxon signed-rank test, normal approximation.

    Returns (W, p_two_sided). For small n (< 20) the normal approximation
    is conservative; the pilot has n = 50 so the approximation is fine.
    """
    nonzero = [d for d in diffs if d != 0]
    n = len(nonzero)
    if n == 0:
        return 0.0, 1.0
    ranks = _ranks([abs(d) for d in nonzero])
    W_plus = sum(r for r, d in zip(ranks, nonzero) if d > 0)
    W_minus = sum(r for r, d in zip(ranks, nonzero) if d < 0)
    W = min(W_plus, W_minus)
    mu = n * (n + 1) / 4.0
    sigma = math.sqrt(n * (n + 1) * (2 * n + 1) / 24.0)
    if sigma == 0:
        return W, 1.0
    z = (W - mu) / sigma
    # two-sided p via the standard-normal cdf approximation
    p = 2 * (1 - _phi(abs(z)))
    return W, max(0.0, min(1.0, p))


def _ranks(xs: list[float]) -> list[float]:
    """Rank with average for ties — 1-indexed."""
    indexed = sorted(enumerate(xs), key=lambda kv: kv[1])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg_rank
        i = j + 1
    return ranks


def _phi(x: float) -> float:
    """Standard-normal CDF via the error-function approximation."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))


def cliffs_delta(a: list[float], b: list[float]) -> float:
    """Cliff's δ effect size between two paired/unpaired lists."""
    if not a or not b:
        return 0.0
    greater = 0
    less = 0
    for x in a:
        for y in b:
            if x > y:
                greater += 1
            elif x < y:
                less += 1
    return (greater - less) / (len(a) * len(b))


def cliffs_label(delta: float) -> str:
    a = abs(delta)
    if a < 0.147:
        return "negligible"
    if a < 0.33:
        return "small"
    if a < 0.474:
        return "medium"
    return "large"


# ── main ──────────────────────────────────────────────────────────────


def main() -> int:
    paired = load_paired()
    if not paired:
        print("No paired records to analyse.")
        return 1

    print(f"Loaded {len(paired)} paired records.")

    by_level: dict[int, list[Paired]] = {}
    for p in paired:
        by_level.setdefault(p.level, []).append(p)

    lines = [
        "# SCM-SQL Pilot — Statistical Analysis",
        "",
        f"n = {len(paired)} paired records  ·  bootstrap n = {N_BOOTSTRAP}  ·  α = {ALPHA}",
        "",
        "## Per-level strict Execution Accuracy with 95 % CI",
        "",
        "| Level | n | Ours EX % (95 % CI) | MAC-SQL EX % (95 % CI) | Δ % | "
        "Wilcoxon p | Bonferroni p | Cliff's δ |",
        "|---|---|---|---|---|---|---|---|",
    ]
    n_comparisons = max(1, len(by_level))
    for level in sorted(by_level.keys()):
        items = by_level[level]
        ours = [p.ours_ex for p in items]
        mac = [p.mac_ex for p in items]
        ours_m, ours_lo, ours_hi = bootstrap_ci(ours)
        mac_m, mac_lo, mac_hi = bootstrap_ci(mac)
        diffs = [a - b for a, b in zip(ours, mac)]
        _, p_w = wilcoxon_signed_rank([float(d) for d in diffs])
        p_bf = min(1.0, p_w * n_comparisons)
        delta = cliffs_delta([float(x) for x in ours], [float(x) for x in mac])
        lines.append(
            f"| L{level} | {len(items)} | "
            f"{ours_m*100:.1f} ({ours_lo*100:.1f}–{ours_hi*100:.1f}) | "
            f"{mac_m*100:.1f} ({mac_lo*100:.1f}–{mac_hi*100:.1f}) | "
            f"{(ours_m-mac_m)*100:+.1f} | "
            f"{p_w:.3f} | {p_bf:.3f} | {delta:+.2f} ({cliffs_label(delta)}) |"
        )

    # overall
    all_ours = [p.ours_ex for p in paired]
    all_mac = [p.mac_ex for p in paired]
    ours_m, ours_lo, ours_hi = bootstrap_ci(all_ours)
    mac_m, mac_lo, mac_hi = bootstrap_ci(all_mac)
    diffs = [a - b for a, b in zip(all_ours, all_mac)]
    _, p_w = wilcoxon_signed_rank([float(d) for d in diffs])
    p_bf = min(1.0, p_w * n_comparisons)
    delta = cliffs_delta([float(x) for x in all_ours],
                          [float(x) for x in all_mac])
    lines.append(
        f"| **All** | **{len(paired)}** | "
        f"**{ours_m*100:.1f} ({ours_lo*100:.1f}–{ours_hi*100:.1f})** | "
        f"**{mac_m*100:.1f} ({mac_lo*100:.1f}–{mac_hi*100:.1f})** | "
        f"**{(ours_m-mac_m)*100:+.1f}** | "
        f"**{p_w:.3f}** | **{p_bf:.3f}** | **{delta:+.2f} ({cliffs_label(delta)})** |"
    )

    # per-level Soft-EX with 95% CI
    lines += [
        "",
        "## Per-level Soft-EX (column-name-agnostic) with 95 % CI",
        "",
        "| Level | n | Ours Soft-EX % (95 % CI) | MAC-SQL Soft-EX % (95 % CI) | Δ % |",
        "|---|---|---|---|---|",
    ]
    for level in sorted(by_level.keys()):
        items = by_level[level]
        ours = [p.ours_soft for p in items]
        mac = [p.mac_soft for p in items]
        ours_m, ours_lo, ours_hi = bootstrap_ci(ours)
        mac_m, mac_lo, mac_hi = bootstrap_ci(mac)
        lines.append(
            f"| L{level} | {len(items)} | "
            f"{ours_m*100:.1f} ({ours_lo*100:.1f}–{ours_hi*100:.1f}) | "
            f"{mac_m*100:.1f} ({mac_lo*100:.1f}–{mac_hi*100:.1f}) | "
            f"{(ours_m-mac_m)*100:+.1f} |"
        )
    all_ours_soft = [p.ours_soft for p in paired]
    all_mac_soft = [p.mac_soft for p in paired]
    ours_m, ours_lo, ours_hi = bootstrap_ci(all_ours_soft)
    mac_m, mac_lo, mac_hi = bootstrap_ci(all_mac_soft)
    overall_soft_delta = ours_m - mac_m
    lines.append(
        f"| **All** | **{len(paired)}** | "
        f"**{ours_m*100:.1f} ({ours_lo*100:.1f}–{ours_hi*100:.1f})** | "
        f"**{mac_m*100:.1f} ({mac_lo*100:.1f}–{mac_hi*100:.1f})** | "
        f"**{overall_soft_delta*100:+.1f}** |"
    )

    # commitment scorecard from EVALUATION_FRAMEWORK §11
    lines += [
        "",
        "## Commitment scorecard (from EVALUATION_FRAMEWORK §11)",
        "",
        "| Target | Threshold | Observed | Met? |",
        "|---|---|---|---|",
        f"| Overall EX | ≥ 60 % | {ours_m*100:.1f} % | "
        f"{'✓' if ours_m >= 0.60 else '✗'} |",
        f"| Δ vs MAC-SQL on L3-L6 | ≥ +10 pp | "
        f"{_l3l6_delta(by_level)*100:+.1f} pp | "
        f"{'✓' if _l3l6_delta(by_level) >= 0.10 else '✗'} |",
        f"| Cliff's δ vs MAC-SQL (overall) | ≥ 0.33 (medium) | "
        f"{delta:+.2f} | {'✓' if abs(delta) >= 0.33 else '✗'} |",
        f"| Bonferroni-corrected p (overall) | ≤ 0.05 | "
        f"{p_bf:.3f} | {'✓' if p_bf <= 0.05 else '✗'} |",
    ]
    STATS_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {STATS_MD.relative_to(ROOT)}")
    return 0


def _l3l6_delta(by_level: dict[int, list[Paired]]) -> float:
    items = sum(
        (by_level.get(lvl, []) for lvl in (3, 4, 5, 6)),
        start=[],
    )
    if not items:
        return 0.0
    return (sum(p.ours_ex for p in items) - sum(p.mac_ex for p in items)) / len(items)


if __name__ == "__main__":
    raise SystemExit(main())

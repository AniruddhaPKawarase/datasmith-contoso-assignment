"""Sample 50 records from b-mc2/sql-create-context (Spider 1.0 mirror).

We use ``b-mc2/sql-create-context`` because Spider 1.0's original tables.json
is not publicly downloadable without auth (it ships on Google Drive). The
b-mc2 dataset is a public mirror that bundles each Spider question with
its CREATE TABLE schema in a single record — exactly the shape we need
for a single-prompt sanity check.

Output:
    benchmark/spider1_sanity/spider_subset.jsonl  (50 records, fixed seed)
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from datasets import load_dataset

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "benchmark" / "spider1_sanity" / "spider_subset.jsonl"
N = 50
SEED = 20260527


def main() -> int:
    ds = load_dataset("b-mc2/sql-create-context", split="train")
    rng = random.Random(SEED)
    # Take from the first 7000 rows where Spider 1.0 records are concentrated
    # per the dataset's documented composition. Any subset would do for a
    # sanity check — we fix the seed so the run is reproducible.
    pool = list(range(min(7000, len(ds))))
    picks = rng.sample(pool, N)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for i, idx in enumerate(picks):
            rec = ds[idx]
            f.write(json.dumps({
                "id": f"S{i + 1:03d}",
                "src_index": idx,
                "question": rec["question"],
                "schema": rec["context"],
                "gold_sql": rec["answer"],
            }) + "\n")
    print(f"Wrote {N} records to {OUT.relative_to(ROOT)} (seed={SEED}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

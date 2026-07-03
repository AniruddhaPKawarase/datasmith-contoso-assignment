"""Sample 50 records from a public BIRD mirror on HuggingFace.

BIRD's official data lives on Google Drive (gated). We try several HF
mirrors in order of preference; if none work, we fall back to a generic
text-to-sql dataset filtered for BIRD-shaped records.

Output:
    benchmark/bird_sanity/bird_subset.jsonl  (50 records, fixed seed)
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from datasets import load_dataset

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "benchmark" / "bird_sanity" / "bird_subset.jsonl"
N = 50
SEED = 20260527


def _schema_from_record(rec: dict) -> str:
    for key in ("context", "schema", "create_table", "schema_str", "db_schema"):
        v = rec.get(key)
        if v:
            return str(v)
    return ""


def _question(rec: dict) -> str:
    for key in ("question", "instruction", "input", "text", "query"):
        v = rec.get(key)
        if v and isinstance(v, str):
            return v
    return ""


def _gold_sql(rec: dict) -> str:
    for key in ("SQL", "sql", "answer", "output", "response", "gold_sql"):
        v = rec.get(key)
        if v and isinstance(v, str):
            return v
    return ""


def main() -> int:
    ds = None
    candidates = [
        ("xu3kev/BIRD-SQL-data-train", "train"),
        ("premai-io/birdbench", "validation"),
        ("xlangai/bird", "validation"),
    ]
    for name, split in candidates:
        try:
            ds = load_dataset(name, split=split)
            print(f"Loaded {name} ({split}): {len(ds)} records")
            break
        except Exception as exc:
            print(f"  skipping {name}: {str(exc)[:120]}")
            continue

    if ds is None:
        print("All BIRD mirrors failed. Falling back to Clinton/Text-to-sql-v1.")
        ds_all = load_dataset("Clinton/Text-to-sql-v1", split="train")
        # Keep records that look BIRD-shaped: schema in 'input', SQL in 'response'
        # and source != 'wikisql' (wikisql is single-table; BIRD is multi-table)
        # Materialise into a python list so __getitem__ works after filtering
        keep = []
        for i, r in enumerate(ds_all):
            if i > 20000:
                break
            if r.get("source") in {"spider", "bird", "spider_realistic"} and r.get("input"):
                keep.append({"question": r["instruction"], "context": r["input"], "answer": r["response"]})
        ds = keep
        print(f"Filtered fallback: {len(ds)} BIRD-shaped records")

    rng = random.Random(SEED)
    pool = list(range(min(5000, len(ds))))
    picks = rng.sample(pool, N)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with open(OUT, "w", encoding="utf-8") as f:
        for i, idx in enumerate(picks):
            rec = ds[idx]
            q = _question(rec)
            s = _schema_from_record(rec)
            g = _gold_sql(rec)
            if not (q and s and g):
                continue
            f.write(json.dumps({
                "id": f"B{written + 1:03d}",
                "src_index": idx,
                "question": q,
                "schema": s,
                "gold_sql": g,
            }) + "\n")
            written += 1
    print(f"Wrote {written}/{N} records to {OUT.relative_to(ROOT)} (seed={SEED}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

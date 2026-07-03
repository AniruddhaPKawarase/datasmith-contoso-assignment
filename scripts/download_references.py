"""Download the academic references cited in the dissertation outline.

Sources every paper from arXiv (or the canonical publisher URL) and
saves it under ``docs/paper/`` with a scannable filename of the form::

    <Key>_<FirstAuthor>_<Venue><Year>.pdf

Run from the project root:
    python scripts/download_references.py

The script is idempotent: it skips files that already exist. Set
``FORCE=1`` in the environment to re-download.
"""
from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

# ── paper catalogue ──────────────────────────────────────────────────


@dataclass(frozen=True)
class Paper:
    """One reference. ``url`` is the direct PDF link; arXiv IDs are
    materialised to ``https://arxiv.org/pdf/<id>``."""

    key: str                          # filename stem
    title: str                        # short human-readable
    arxiv_id: str = ""                # if arXiv, set this; URL is built
    url: str = ""                     # otherwise set this directly


# Ordered by relevance to the dissertation outline.
PAPERS: tuple[Paper, ...] = (
    # ── Multi-agent text-to-SQL frameworks (baselines) ──
    Paper("01_MAC-SQL_Wang_COLING2025",
          "MAC-SQL: A Multi-Agent Collaborative Framework for Text-to-SQL",
          arxiv_id="2312.11242"),
    Paper("02_MARS-SQL_Chen_2025",
          "MARS-SQL: A Multi-Agent RL Framework for Text-to-SQL",
          arxiv_id="2511.01008"),
    Paper("03_SQL-of-Thought_Chaturvedi_NeurIPS2025",
          "SQL-of-Thought: Multi-Agentic Text-to-SQL with Guided Error Correction",
          arxiv_id="2509.00581"),
    Paper("04_CHASE-SQL_Pourreza_ICLR2025",
          "CHASE-SQL: Multi-Path Reasoning + Preference-Optimised Candidate Selection",
          arxiv_id="2410.01943"),

    # ── Enterprise-scale benchmarks & challenges ──
    Paper("05_Spider-2.0_Lei_ICLR2025",
          "Spider 2.0: Evaluating LMs on Real-World Enterprise Text-to-SQL",
          arxiv_id="2411.07763"),
    Paper("06_BIRD_Li_NeurIPS2023",
          "BIRD: Can LLMs Already Serve as a Database Interface?",
          arxiv_id="2305.03111"),
    Paper("07_NL2SQL-Not-Solved_Floratou_CIDR2024",
          "NL2SQL is a Solved Problem... Not!",
          # CIDR 2024 — alternate arXiv preprint also exists for some
          # CIDR papers; the canonical PDF lives on cidrdb.org.
          url="https://www.cidrdb.org/cidr2024/papers/p74-floratou.pdf"),
    Paper("08_NL2SQL-Survey_Luo_VLDB2025",
          "A Survey of NL2SQL with Large Language Models — Where Are We?",
          arxiv_id="2408.05109"),

    # ── Ambiguity, self-correction, schema disambiguation ──
    Paper("09_AmbiSQL_Liu_2025",
          "AmbiSQL: Interactive Ambiguity Detection and Resolution",
          arxiv_id="2508.15276"),
    Paper("10_Odin_Patel_2025",
          "Odin: User-Feedback-Based Schema Disambiguation for Text-to-SQL",
          arxiv_id="2505.19302"),
    Paper("11_ReFoRCE_Deng_2025",
          "ReFoRCE: Text-to-SQL Agent with Self-Refinement + Column Exploration",
          arxiv_id="2502.00675"),
    Paper("12_TAG_Biswal_CIDR2025",
          "Text2SQL is Not Enough: Unifying AI and Databases with Table-Augmented Generation",
          arxiv_id="2408.14717"),

    # ── Recent agentic / multi-turn / SLM-based variants ──
    Paper("13_MA-Text2SQL-SLM_Zhang_2025",
          "Multi-Agent Text2SQL Framework using Small Language Models",
          arxiv_id="2512.18622"),
    Paper("14_AgentiQL_Ko_2025",
          "AgentiQL: Multi-Expert Text-to-SQL with Adaptive Routing",
          arxiv_id="2510.10661"),
    Paper("15_MTSQL-R1_Liu_2025",
          "MTSQL-R1: A Reinforcement-Learning Approach to Multi-Turn Text-to-SQL",
          arxiv_id="2510.12831"),

    # ── Foundation model + domain ──
    Paper("16_Qwen2.5-Coder_Hui_2024",
          "Qwen 2.5-Coder Technical Report",
          arxiv_id="2409.12186"),
    Paper("17_Agentic-LLMs-SCM_Klabe_IJPR2025",
          "Agentic LLMs in the Supply Chain — Towards Autonomous Multi-Agent Consensus",
          arxiv_id="2411.10184"),
)


# ── downloader ───────────────────────────────────────────────────────


HEADERS = {
    "User-Agent": "Mozilla/5.0 (academic-reference-downloader; "
                  "BITS-Pilani-MTech-Dissertation-2024AA05175)",
    "Accept": "application/pdf,*/*;q=0.8",
}


def url_for(paper: Paper) -> str:
    if paper.arxiv_id:
        return f"https://arxiv.org/pdf/{paper.arxiv_id}"
    return paper.url


def download_one(client: httpx.Client, paper: Paper, dest_dir: Path,
                 *, force: bool) -> tuple[bool, str]:
    """Return (success, message)."""
    out = dest_dir / f"{paper.key}.pdf"
    if out.exists() and not force:
        return True, f"already exists ({out.stat().st_size // 1024} KB)"

    url = url_for(paper)
    try:
        with client.stream("GET", url, follow_redirects=True, timeout=45) as r:
            if r.status_code != 200:
                return False, f"HTTP {r.status_code} from {url}"
            ctype = r.headers.get("content-type", "")
            tmp = out.with_suffix(".pdf.part")
            with open(tmp, "wb") as f:
                for chunk in r.iter_bytes(chunk_size=64 * 1024):
                    f.write(chunk)
            # Sanity: first 5 bytes of a PDF are '%PDF-'.
            with open(tmp, "rb") as f:
                head = f.read(5)
            if head != b"%PDF-":
                tmp.unlink(missing_ok=True)
                return False, (
                    f"response was not a PDF (content-type={ctype!r}, "
                    f"first bytes={head!r}); URL may need a manual visit"
                )
            tmp.replace(out)
            return True, f"downloaded ({out.stat().st_size // 1024} KB)"
    except httpx.HTTPError as exc:
        return False, f"HTTP error: {type(exc).__name__}: {exc}"


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    dest = root / "docs" / "paper"
    dest.mkdir(parents=True, exist_ok=True)

    force = os.getenv("FORCE") == "1"
    print(f"Destination: {dest.relative_to(root)}")
    print(f"Force re-download: {force}")
    print(f"Papers to fetch:    {len(PAPERS)}\n")

    successes: list[str] = []
    failures: list[tuple[str, str]] = []

    with httpx.Client(headers=HEADERS) as client:
        for i, paper in enumerate(PAPERS, start=1):
            label = f"[{i:>2}/{len(PAPERS)}] {paper.key}"
            ok, msg = download_one(client, paper, dest, force=force)
            status = "OK " if ok else "FAIL"
            print(f"  {status}  {label}  -  {msg}")
            (successes if ok else failures).append(
                paper.key if ok else (paper.key, msg)
            )
            # Be polite to arXiv: 1 s between requests when actually downloading.
            if ok and "downloaded" in msg:
                time.sleep(1.0)

    print(f"\nSummary: {len(successes)} ok, {len(failures)} failed")
    if failures:
        print("\nFailed downloads (try opening URLs in a browser):")
        for key, err in failures:
            paper = next(p for p in PAPERS if p.key == key)
            print(f"  - {key}")
            print(f"      reason: {err}")
            print(f"      url:    {url_for(paper)}")
    print("\nWrite a manifest file:")
    manifest = dest / "REFERENCES.md"
    lines = [
        "# Downloaded References",
        "",
        "Source: `scripts/download_references.py`",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "| # | Title | File |",
        "|---|---|---|",
    ]
    for paper in PAPERS:
        f = dest / f"{paper.key}.pdf"
        present = "✔" if f.exists() else "✗"
        lines.append(f"| {present} | {paper.title} | `{paper.key}.pdf` |")
    manifest.write_text("\n".join(lines), encoding="utf-8")
    print(f"  -> {manifest.relative_to(root)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())

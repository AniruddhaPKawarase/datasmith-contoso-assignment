"""Smoke test: call OpenAI and Anthropic with tiny prompts via LLMProvider.

Reads .env from project root, runs through LLMProvider, prints latency + tokens.
Run from project root:
    python scripts/smoke_llm.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

# Load .env into os.environ
env_path = ROOT / ".env"
if env_path.exists():
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        # split inline comments outside quotes only — keep value-side `#` chars intact for keys
        os.environ.setdefault(key.strip(), value.strip())

from app.llm import LLMConfig, LLMProvider, ModelTask  # noqa: E402


PROMPTS = {
    ModelTask.SQL_GEN: (
        "You are a precise SQL generator. Output ONE PostgreSQL statement, no markdown.",
        "List the top 5 most-expensive rows from table product_product ordered by list_price.",
    ),
    ModelTask.ROUTER: (
        'Classify the user query into one or more business domains. Reply with ONLY a JSON array of strings from: ["inventory","logistics","finance","demand","compliance"]',
        "Which warehouses had inventory turnover below average last quarter?",
    ),
}


async def main() -> int:
    cfg = LLMConfig.from_env()
    have_openai = bool(cfg.openai_api_key) and cfg.openai_api_key != "sk-replace-me"
    have_anthropic = bool(cfg.anthropic_api_key) and cfg.anthropic_api_key != "sk-ant-replace-me"
    if not have_openai and not have_anthropic:
        print("ERROR: neither OPENAI_API_KEY nor ANTHROPIC_API_KEY is set in .env")
        return 1
    print(f"OpenAI key:    {'present' if have_openai else 'MISSING'}")
    print(f"Anthropic key: {'present' if have_anthropic else 'MISSING'}")
    print(f"Fallback:      {cfg.fallback_model}")
    print()

    provider = LLMProvider(cfg)
    failures = 0
    for task, (system, user) in PROMPTS.items():
        model = cfg.model_for(task)
        print(f"[{task.value}] model={model}")
        try:
            resp = await provider.generate(
                task=task,
                system=system,
                user=user,
                temperature=0.0,
                max_tokens=200,
            )
            print(f"  provider:   {resp.provider}")
            print(f"  model:      {resp.model}")
            print(f"  latency:    {resp.latency_ms} ms")
            print(f"  tokens:     {resp.prompt_tokens} in / {resp.completion_tokens} out")
            print(f"  finish:     {resp.finish_reason}")
            print(f"  output:     {resp.text.strip()[:300]}")
        except Exception as exc:
            failures += 1
            print(f"  FAILED: {type(exc).__name__}: {exc}")
        print()

    await provider.aclose()
    if failures:
        print(f"Smoke test: {failures} failure(s).")
        return 2
    print("Smoke test OK — both backends reachable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

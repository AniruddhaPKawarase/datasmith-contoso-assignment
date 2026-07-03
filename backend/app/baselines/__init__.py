"""Baseline systems for head-to-head comparison.

Each baseline implements an ``async def predict(query, history_summary) -> BaselineOutput``
contract so the evaluation runner can swap them uniformly.

Currently implemented:
    mac_sql  — MAC-SQL (Wang et al., COLING 2025) — pipeline-axis
               decomposition: Selector → Decomposer → Refiner.
"""

from app.baselines.mac_sql import BaselineOutput, MacSqlBaseline

__all__ = ["BaselineOutput", "MacSqlBaseline"]

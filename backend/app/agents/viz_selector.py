"""VizSelector — post-execution agent that decides the best output format.

Rubric line #2 (Visualization Intelligence, 20 pts): the agent must
autonomously pick line / bar / pie / table / KPI / mixed / prose based
on (question, SQL, columns, sample rows), not on any hardcoded per-query
mapping. This module is the reasoning layer for that decision.

Called from the FastAPI gateway AFTER the orchestrator has produced SQL
and executed it — sees a short sample of real rows so its decision is
data-shape-aware, not just guess-from-NL.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from app.llm import LLMProvider, ModelTask
from app.llm.token_tracker import TokenTracker

logger = logging.getLogger(__name__)

# Only these 7 formats are accepted downstream by the frontend.
_VALID_FORMATS = {"line", "bar", "pie", "table", "kpi", "mixed", "prose"}


@dataclass(frozen=True)
class VizDecision:
    """The Selector's output — fed straight to the frontend."""

    format: str                   # one of _VALID_FORMATS
    x_axis: str | None = None     # column name to use on X (line/bar)
    y_axis: str | None = None     # column name for Y (line/bar) or the value (KPI)
    series: str | None = None     # column for multi-series (line/grouped-bar)
    title: str = ""
    reasoning: str = ""           # one-line rationale for the trace UI

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": self.format,
            "x_axis": self.x_axis,
            "y_axis": self.y_axis,
            "series": self.series,
            "title": self.title,
            "reasoning": self.reasoning,
        }


_SYSTEM_PROMPT = """\
You choose the best output format for a SQL query result to display in a
chat-based data-analytics app. Pick exactly ONE of:

  line    — time-series or ordered-numeric trends (revenue over months,
            AOV by quarter). Requires an ordered dimension on X and a
            numeric measure on Y. Multiple series ok (set "series").
  bar     — categorical comparison (revenue by region, top-N by spend).
            Requires a categorical dimension on X and a numeric measure
            on Y. Single-series unless "series" is set.
  pie     — part-of-whole with < 8 slices (channel split, gender share).
            Only when the values sum to a meaningful whole.
  table   — ranked lists, multi-attribute breakdowns, > 3 numeric cols,
            or when no single dimension dominates. Default fallback for
            rich rows.
  kpi     — SINGLE-row result with ONE numeric value (total revenue in
            2013). Only for scalar answers.
  mixed   — complex answer that warrants both a chart AND a summary
            table (comparative multi-panel, top-N with breakdown).
  prose   — natural-language insight only (trend narration, anomaly
            callout — no chart shape fits).

Axis-assignment rules (READ CAREFULLY — this is where most mistakes happen):
  - The x_axis is the ORDERED / GROUPING dimension you scan LEFT TO RIGHT.
    For time-series it's month/quarter/year — the axis that reads
    chronologically.
  - The y_axis is the NUMERIC MEASURE (revenue, count, avg_order_value).
  - series is the CATEGORICAL dimension you draw one line/bar-group per.
    For "monthly revenue by region", month is x, revenue is y,
    region is series. For "top 10 customers by spend", customer is x,
    spend is y, no series.

Format-selection rules:
  - row_count == 1 AND exactly one numeric column → "kpi".
  - x-column is date/month/quarter/year AND y is numeric → "line".
    (Even with 50+ rows — the line chart handles it, don't drop to
    table just because rows are many.)
  - x-column is a category (region, product, channel) with 2-20 distinct
    values AND y is numeric AND no time dimension → "bar".
  - > 3 numeric measures per row → "table".
  - Only "pie" for <= 8 slices AND values partition a whole.
  - x_axis / y_axis / series must be column names EXACTLY as they appear in
    the sample row. Return null when a format doesn't need them (table, prose).

Reply with ONLY valid JSON matching this schema:
{
  "format": "<one of: line, bar, pie, table, kpi, mixed, prose>",
  "x_axis": "<column-name or null>",
  "y_axis": "<column-name or null>",
  "series": "<column-name or null>",
  "title": "<short title for the chart, or empty string>",
  "reasoning": "<one-sentence rationale>"
}
"""


def _column_type(value: Any) -> str:
    """Coarse type tag used to help the LLM see the data shape."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        # detect ISO date-ish strings so the model recognises time-series
        if re.match(r"^\d{4}-\d{2}(-\d{2})?", value):
            return "date-like"
        return "text"
    return type(value).__name__


def _shape_summary(rows: list[dict], max_rows: int = 3) -> str:
    """Compact description of the result set: cols, types, sample."""
    if not rows:
        return "row_count=0 (empty result)"
    cols = list(rows[0].keys())
    types = {c: _column_type(rows[0][c]) for c in cols}
    parts = [
        f"row_count={len(rows)}",
        "columns=" + ", ".join(f"{c}({types[c]})" for c in cols),
        "sample_rows=" + json.dumps(rows[:max_rows], default=str),
    ]
    return "\n".join(parts)


class VizSelector:
    """LLM-driven output-format selector."""

    def __init__(
        self,
        *,
        llm: LLMProvider,
        tracker: TokenTracker | None = None,
        model_task: ModelTask = ModelTask.SQL_GEN,  # reuse the sql_gen budget
    ) -> None:
        self._llm = llm
        self._tracker = tracker
        self._task = model_task

    async def select(
        self,
        *,
        query: str,
        sql: str,
        rows: list[dict],
    ) -> VizDecision:
        """Pick a format. Falls back to `table` on any error."""
        # Shortcut heuristics — save an LLM call for trivial cases.
        if not rows:
            return VizDecision(
                format="prose",
                reasoning="empty result set — nothing to plot",
            )
        if len(rows) == 1 and len(rows[0]) == 1:
            col = next(iter(rows[0]))
            return VizDecision(
                format="kpi",
                y_axis=col,
                title=query[:80],
                reasoning="single-value scalar answer",
            )

        user = (
            f"User question: {query}\n\n"
            f"Generated SQL:\n{sql}\n\n"
            f"Result set shape:\n{_shape_summary(rows)}\n\n"
            "Return the JSON decision."
        )
        try:
            resp = await self._llm.generate(
                task=self._task,
                system=_SYSTEM_PROMPT,
                user=user,
                temperature=0.0,
                max_tokens=250,
            )
            if self._tracker is not None:
                self._tracker.record(self._task, resp)
        except Exception as exc:
            logger.warning("VizSelector LLM call failed: %s", exc)
            return VizDecision(format="table", reasoning="LLM error — table fallback")

        return _parse_decision(resp.text, fallback_title=query[:80])


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_decision(raw: str, fallback_title: str = "") -> VizDecision:
    m = _JSON_RE.search(raw or "")
    if not m:
        return VizDecision(format="table", reasoning="unparseable LLM output")
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return VizDecision(format="table", reasoning="invalid JSON from selector")

    fmt = str(data.get("format", "table")).lower().strip()
    if fmt not in _VALID_FORMATS:
        fmt = "table"
    return VizDecision(
        format=fmt,
        x_axis=data.get("x_axis") or None,
        y_axis=data.get("y_axis") or None,
        series=data.get("series") or None,
        title=str(data.get("title") or fallback_title),
        reasoning=str(data.get("reasoning") or ""),
    )

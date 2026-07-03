"""Request and response models for the FastAPI gateway."""
from __future__ import annotations

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(..., min_length=1, max_length=100)


class TokenUsage(BaseModel):
    router: int = 0
    sql_gen: int = 0
    validator: int = 0


class Visualization(BaseModel):
    """Decided by VizSelector after SQL execution."""

    format: str = "table"           # line | bar | pie | table | kpi | mixed | prose
    x_axis: str | None = None
    y_axis: str | None = None
    series: str | None = None
    title: str = ""
    reasoning: str = ""


class PlanStep(BaseModel):
    """One planned sub-query for multi-step queries (TC06 funnel, TC08 multi-panel)."""

    step: int
    name: str
    natural_language: str
    rationale: str = ""


class Panel(BaseModel):
    """A single sub-result of a multi-step plan."""

    step: int
    name: str
    sql: str | None = None
    rows: list[dict] | None = None
    row_count: int = 0
    visualization: Visualization | None = None
    error: str | None = None


class Trace(BaseModel):
    """Handoff log surfaced to the UI (Bonus B2 — Planner + Executor visibility)."""

    planner_intent: str = ""
    planner_domains: list[str] = []
    plan_steps: list[PlanStep] = []
    executor_notes: str = ""


class AskResponse(BaseModel):
    intent: str
    domains: list[str]
    sql: str | None = None
    rows: list[dict] | None = None
    row_count: int = 0
    latency_ms: int
    token_usage: TokenUsage
    estimated_cost_usd: float = 0.0
    explain_ok: bool = False
    error: str | None = None
    clarification_question: str | None = None
    visualization: Visualization | None = None
    panels: list[Panel] | None = None      # populated for multi-step queries
    trace: Trace | None = None

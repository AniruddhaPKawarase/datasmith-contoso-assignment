"""Tests for AgentState and the SubQuery / ValidationIssue / AgentOutput dataclasses."""
from __future__ import annotations

import dataclasses

import pytest

from app.agents.state import (
    AgentOutput,
    OrchestratorLimits,
    SubQuery,
    ValidationIssue,
    fresh_state,
)
from app.schema.domains import Domain


def test_fresh_state_defaults() -> None:
    s = fresh_state(query="hello", session_id="sid")
    assert s["query"] == "hello"
    assert s["session_id"] == "sid"
    assert s["domains"] == ()
    assert s["attempt"] == 0
    assert s["intent"] == ""


def test_subquery_immutable() -> None:
    sq = SubQuery(domain=Domain.INVENTORY, natural_language="stock?")
    with pytest.raises(dataclasses.FrozenInstanceError):
        sq.natural_language = "mutated"  # type: ignore[misc]


def test_validation_issue_fields() -> None:
    issue = ValidationIssue(kind="syntax", message="boom", location="composer")
    assert issue.kind == "syntax"
    assert issue.suggestion == ""


def test_agent_output_fields() -> None:
    out = AgentOutput(
        domain=Domain.FINANCE,
        sql="SELECT 1",
        confidence=0.8,
        used_tables=("account_move",),
    )
    assert out.sql == "SELECT 1"
    assert out.used_tables == ("account_move",)


def test_orchestrator_limits_defaults() -> None:
    lim = OrchestratorLimits()
    assert lim.max_correction_attempts == 3
    assert lim.sql_timeout_s == 30

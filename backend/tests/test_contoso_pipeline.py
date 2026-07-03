"""Contoso-scoped regression tests — 10 checks over the pure logic in the
NL→SQL pipeline that do NOT require the DB or an LLM. Fast and stable.

Cover:
 1. detect_decline_insight fires on obvious QoQ drop.
 2. detect_decline_insight returns None on rising series.
 3. detect_decline_insight handles composite time (year + quarter).
 4. detect_decline_insight is safe on empty input.
 5. PlannerChain recognises "sales funnel" query → 3 steps.
 6. PlannerChain demographic + "Pacific" → 'Asia' filter clause.
 7. PlannerChain demographic + "APAC" → 'Asia' filter clause.
 8. PlannerChain returns None for unrelated queries.
 9. domains.yaml loads with 15 Contoso primary tables under 'demand'.
10. Read-only SQL guard rejects mutation statements.

Run: pytest backend/tests/test_contoso_pipeline.py -v
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.agents.insight_detector import detect_decline_insight
from app.agents.planner_chain import maybe_multi_step

# ─── InsightDetector ──────────────────────────────────────────────────────

def test_decline_insight_fires_on_qoq_drop():
    rows = [
        {"product": "A", "year": 2008, "quarter": "Q1", "revenue": 1000.0},
        {"product": "A", "year": 2008, "quarter": "Q2", "revenue": 600.0},
        {"product": "B", "year": 2008, "quarter": "Q1", "revenue": 500.0},
        {"product": "B", "year": 2008, "quarter": "Q2", "revenue": 200.0},
    ]
    result = detect_decline_insight(rows, min_decline_pct=15.0)
    assert result is not None
    assert "declined" in result
    assert "product" in result


def test_decline_insight_none_on_rising():
    rows = [
        {"product": "A", "year": 2008, "quarter": "Q1", "revenue": 100.0},
        {"product": "A", "year": 2008, "quarter": "Q2", "revenue": 150.0},
        {"product": "B", "year": 2008, "quarter": "Q1", "revenue": 100.0},
        {"product": "B", "year": 2008, "quarter": "Q2", "revenue": 200.0},
    ]
    assert detect_decline_insight(rows) is None


def test_decline_insight_composite_year_quarter():
    """Insight scanner must build a composite time bucket from year + quarter."""
    rows = [
        {"category": "Bikes", "year": 2008, "quarter": "Q3", "revenue": 800.0},
        {"category": "Bikes", "year": 2008, "quarter": "Q4", "revenue": 500.0},  # -37%
        {"category": "Cars",  "year": 2008, "quarter": "Q3", "revenue": 900.0},
        {"category": "Cars",  "year": 2008, "quarter": "Q4", "revenue": 950.0},
    ]
    result = detect_decline_insight(rows, min_decline_pct=15.0)
    assert result is not None
    assert "Bikes" in result


def test_decline_insight_safe_on_empty():
    assert detect_decline_insight([]) is None
    assert detect_decline_insight([{"x": 1}]) is None  # only one row


# ─── PlannerChain ─────────────────────────────────────────────────────────

def test_planner_recognises_sales_funnel():
    plan = maybe_multi_step("Show me a sales funnel: orders → shipped → revenue by territory")
    assert plan is not None
    assert len(plan) == 3
    assert plan[0].name == "orders"
    assert plan[2].name == "revenue"


def test_planner_maps_pacific_to_asia():
    plan = maybe_multi_step("Give me a full customer demographic breakdown for the Pacific region")
    assert plan is not None
    assert len(plan) == 3
    # Every sub-step must instruct the specialist to filter by group='Asia',
    # NOT by literal "Pacific" text (which returns 0 rows).
    for step in plan:
        assert "Asia" in step.natural_language
        assert "Pacific" not in step.natural_language


def test_planner_maps_apac_to_asia():
    plan = maybe_multi_step("Full demographic breakdown for APAC")
    assert plan is not None
    for step in plan:
        assert "Asia" in step.natural_language


def test_planner_returns_none_for_unrelated_query():
    assert maybe_multi_step("What is the total revenue for 2009?") is None
    assert maybe_multi_step("Show top 10 customers") is None


# ─── Domain config ────────────────────────────────────────────────────────

def test_domains_yaml_has_15_contoso_tables_on_demand():
    domains_path = Path(__file__).resolve().parent.parent / "app" / "schema" / "domains.yaml"
    data = yaml.safe_load(domains_path.read_text(encoding="utf-8"))
    demand_tables = data["domains"]["demand"]["primary"]
    assert len(demand_tables) == 15, f"expected 15 tables, got {len(demand_tables)}"
    # Sanity: the load-bearing facts must be there.
    for required in ("factonlinesales", "factsales", "factsalesquota",
                     "dimcustomer", "dimproduct", "dimsalesterritory",
                     "dimgeography", "dimdate"):
        assert required in demand_tables, f"missing {required}"


# ─── Read-only SQL guard ──────────────────────────────────────────────────

@pytest.mark.parametrize("bad_sql", [
    "DELETE FROM factonlinesales WHERE salesamount > 100",
    "UPDATE dimcustomer SET yearlyincome = 0",
    "INSERT INTO dimcustomer (customerkey) VALUES (1)",
    "DROP TABLE dimcustomer",
    "TRUNCATE dimcustomer",
    "ALTER TABLE dimcustomer ADD COLUMN foo TEXT",
    "CREATE TABLE evil (x INT)",
])
def test_readonly_guard_rejects_mutations(bad_sql):
    """App-layer defence: sqlglot parses the SQL; only SELECT/WITH pass.

    Belt-and-suspenders with the DB-level `contoso_reader` role, but the app
    guard runs before any connection is opened.
    """
    from app.validator.syntax import SyntaxValidator

    result = SyntaxValidator().validate(bad_sql)
    assert not result.parsed_ok or result.issues, (
        f"guard did not flag {bad_sql!r}"
    )
    # At least one issue must mention "Forbidden statement type".
    messages = " ".join(iss.message for iss in result.issues)
    assert "Forbidden statement type" in messages, (
        f"expected 'Forbidden statement type' in issues, got: {messages}"
    )

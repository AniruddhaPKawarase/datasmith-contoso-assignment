"""Tests for the business glossary loader and lookup."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.schema.domains import Domain
from app.schema.glossary import load_glossary


def _write_yaml(path: Path, body: dict) -> Path:
    path.write_text(yaml.safe_dump(body), encoding="utf-8")
    return path


def _toy_glossary() -> dict:
    return {
        "version": 1,
        "terms": [
            {
                "term": "lead time",
                "aliases": ["supplier lead time"],
                "domain": "logistics",
                "sql_fragment": "DATE_PART('day', po.date_planned - po.date_order)",
                "tables": ["purchase_order"],
                "notes": "default = procurement",
            },
            {
                "term": "revenue",
                "aliases": ["sales revenue", "top line"],
                "domain": "finance",
                "sql_fragment": "SUM(aml.credit)",
                "tables": ["account_move_line"],
            },
        ],
        "ambiguous_terms": [
            {"term": "lead time", "candidates": ["procurement", "manufacturing"]},
        ],
    }


def test_load_glossary(tmp_path: Path) -> None:
    p = _write_yaml(tmp_path / "glossary.yaml", _toy_glossary())
    g = load_glossary(p)
    assert len(g.entries) == 2
    assert g.entries[0].domain == Domain.LOGISTICS


def test_find_by_term(tmp_path: Path) -> None:
    p = _write_yaml(tmp_path / "glossary.yaml", _toy_glossary())
    g = load_glossary(p)
    hits = g.find("show me the supplier lead time")
    assert len(hits) == 1
    assert hits[0].term == "lead time"


def test_find_case_insensitive(tmp_path: Path) -> None:
    p = _write_yaml(tmp_path / "glossary.yaml", _toy_glossary())
    g = load_glossary(p)
    assert g.find("REVENUE last quarter")
    assert g.find("Top Line growth")


def test_for_domain(tmp_path: Path) -> None:
    p = _write_yaml(tmp_path / "glossary.yaml", _toy_glossary())
    g = load_glossary(p)
    finance_only = g.for_domain(Domain.FINANCE)
    assert len(finance_only) == 1
    assert finance_only[0].term == "revenue"


def test_ambiguous_detection(tmp_path: Path) -> None:
    p = _write_yaml(tmp_path / "glossary.yaml", _toy_glossary())
    g = load_glossary(p)
    hits = g.is_ambiguous("what is our lead time")
    assert len(hits) == 1
    assert hits[0].term == "lead time"
    assert "procurement" in hits[0].candidates


def test_unknown_domain_raises(tmp_path: Path) -> None:
    body = _toy_glossary()
    body["terms"].append({
        "term": "x", "domain": "wrong", "sql_fragment": "", "tables": []
    })
    p = _write_yaml(tmp_path / "glossary.yaml", body)
    with pytest.raises(ValueError):
        load_glossary(p)


def test_real_glossary_loads() -> None:
    g = load_glossary()
    assert g.entries
    # Every non-cross-cutting domain must have at least one glossary entry.
    domains_with_entries = {e.domain for e in g.entries}
    for d in (Domain.INVENTORY, Domain.LOGISTICS, Domain.FINANCE, Domain.DEMAND):
        assert d in domains_with_entries, f"glossary missing entries for {d}"

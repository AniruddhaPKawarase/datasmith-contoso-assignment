"""Tests for the domain-to-schema mapping loader and resolver."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.schema.domains import Domain, load_domain_mapping


def _write_yaml(path: Path, body: dict) -> Path:
    path.write_text(yaml.safe_dump(body), encoding="utf-8")
    return path


def _minimal_yaml() -> dict:
    return {
        "version": 1,
        "domains": {
            "inventory": {
                "description": "stocks",
                "primary": ["stock_move", "stock_quant"],
                "keywords": ["stock"],
            },
            "logistics": {
                "description": "ship",
                "primary": ["stock_picking", "purchase_order"],
                "keywords": ["lead time"],
            },
            "finance": {
                "description": "money",
                "primary": ["account_move"],
                "keywords": [],
            },
            "demand": {
                "description": "sell",
                "primary": ["sale_order"],
                "keywords": [],
            },
            "compliance": {
                "description": "rbac",
                "primary": [],
                "cross_cutting": True,
                "keywords": [],
            },
        },
        "shared": {
            "product": {
                "description": "products",
                "tables": ["product_product", "product_template"],
            },
        },
        "prefix_rules": {
            "inventory": ["stock_", "mrp_"],
            "finance": ["account_"],
        },
        "excluded_prefixes": ["mail_", "ir_"],
        "suffix_rules": {
            "join_tables": ["_rel"],
            "wizard_tables": ["_wizard"],
        },
    }


def test_load_minimal_yaml(tmp_path: Path) -> None:
    p = _write_yaml(tmp_path / "domains.yaml", _minimal_yaml())
    m = load_domain_mapping(p)
    assert Domain.INVENTORY in m.domains
    assert Domain.COMPLIANCE in m.domains
    assert "product_product" in m.shared["product"].tables


def test_domains_owning_explicit(tmp_path: Path) -> None:
    p = _write_yaml(tmp_path / "domains.yaml", _minimal_yaml())
    m = load_domain_mapping(p)
    assert m.domains_owning("stock_move") == [Domain.INVENTORY]
    assert m.domains_owning("nonexistent") == []


def test_resolve_via_prefix_rule(tmp_path: Path) -> None:
    p = _write_yaml(tmp_path / "domains.yaml", _minimal_yaml())
    m = load_domain_mapping(p)
    assert m.resolve_domain("stock_some_new_table") == Domain.INVENTORY
    assert m.resolve_domain("mrp_workorder") == Domain.INVENTORY
    assert m.resolve_domain("account_journal_group") == Domain.FINANCE


def test_resolve_explicit_beats_prefix(tmp_path: Path) -> None:
    p = _write_yaml(tmp_path / "domains.yaml", _minimal_yaml())
    m = load_domain_mapping(p)
    # stock_picking is owned by logistics explicitly; prefix says inventory.
    assert m.resolve_domain("stock_picking") == Domain.LOGISTICS


def test_excluded_short_circuits(tmp_path: Path) -> None:
    p = _write_yaml(tmp_path / "domains.yaml", _minimal_yaml())
    m = load_domain_mapping(p)
    assert m.is_excluded("mail_message") is True
    assert m.resolve_domain("mail_message") is None


def test_wizard_short_circuits(tmp_path: Path) -> None:
    p = _write_yaml(tmp_path / "domains.yaml", _minimal_yaml())
    m = load_domain_mapping(p)
    assert m.is_wizard("change_password_wizard") is True
    assert m.resolve_domain("change_password_wizard") is None


def test_visible_to_includes_shared(tmp_path: Path) -> None:
    p = _write_yaml(tmp_path / "domains.yaml", _minimal_yaml())
    m = load_domain_mapping(p)
    vis = m.visible_to(Domain.INVENTORY)
    assert "stock_move" in vis
    assert "product_product" in vis           # from shared
    assert "account_move" not in vis          # finance-only primary


def test_compliance_sees_all_primaries(tmp_path: Path) -> None:
    p = _write_yaml(tmp_path / "domains.yaml", _minimal_yaml())
    m = load_domain_mapping(p)
    vis = m.visible_to(Domain.COMPLIANCE)
    for owner_table in ("stock_move", "stock_picking", "account_move", "sale_order"):
        assert owner_table in vis


def test_coverage_buckets(tmp_path: Path) -> None:
    p = _write_yaml(tmp_path / "domains.yaml", _minimal_yaml())
    m = load_domain_mapping(p)
    all_tables = {
        "stock_move", "stock_quant", "stock_picking",
        "purchase_order", "account_move", "sale_order",
        "product_product", "product_template",
        "mail_message", "ir_model",        # excluded
        "change_password_wizard",          # wizard
        "stock_route_rel",                 # join table (matches stock_ prefix → inventory)
        "weird_unmapped_table",
    }
    rep = m.coverage(all_tables)
    assert rep.summary()["unmapped"] == 1
    assert "weird_unmapped_table" in rep.unmapped
    assert "mail_message" in rep.excluded_present
    assert "change_password_wizard" in rep.wizard_present
    assert "product_product" in rep.shared_known


def test_unknown_domain_key_raises(tmp_path: Path) -> None:
    body = _minimal_yaml()
    body["domains"]["unknown_domain"] = {"primary": ["x"]}
    p = _write_yaml(tmp_path / "domains.yaml", body)
    with pytest.raises(ValueError):
        load_domain_mapping(p)


def test_unknown_domain_in_prefix_rules_raises(tmp_path: Path) -> None:
    body = _minimal_yaml()
    body["prefix_rules"]["unknown_domain"] = ["x_"]
    p = _write_yaml(tmp_path / "domains.yaml", body)
    with pytest.raises(ValueError):
        load_domain_mapping(p)


def test_real_yaml_loads_and_validates() -> None:
    """The actual domains.yaml shipped with the project must parse cleanly."""
    m = load_domain_mapping()
    assert len(m.domains) == 5
    for d in Domain:
        assert d in m.domains
    assert m.shared, "expected shared groups to be defined"
    assert m.prefix_rules, "expected prefix_rules to be defined"

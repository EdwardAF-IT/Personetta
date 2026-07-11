from __future__ import annotations

from pathlib import Path

import pytest

from generator.loader import load_merge_config
from generator.merge.strategies import merge_roles, parse_field_strategies

pytestmark = [pytest.mark.unit, pytest.mark.core, pytest.mark.readonly]


def test_repo_merge_config_includes_verification_strategy(real_project: Path) -> None:
    cfg = load_merge_config(real_project)
    strategies, union_keys = parse_field_strategies(cfg)
    assert strategies.get("verification") == "union-by-key"
    assert union_keys.get("verification") == "check"


def test_parse_field_strategies_yaml_overrides_default() -> None:
    cfg = {
        "field_strategies": {
            "tone": {"strategy": "union"},
        },
    }
    strategies, _ = parse_field_strategies(cfg)
    assert strategies["tone"] == "union"
    assert strategies["verification"] == "union-by-key"


def test_parse_field_strategies_union_by_key_custom_field() -> None:
    cfg = {
        "field_strategies": {
            "widgets": {"strategy": "union-by-key", "key": "id"},
        },
    }
    _, union_keys = parse_field_strategies(cfg)
    assert union_keys.get("widgets") == "id"


def test_merge_roles_respects_yaml_union_by_key_field_name() -> None:
    cfg = {
        "field_strategies": {
            "widgets": {"strategy": "union-by-key", "key": "id"},
        },
    }
    roles = [
        {"widgets": [{"id": "a", "v": 1}]},
        {"widgets": [{"id": "a", "v": 2}, {"id": "b", "v": 3}]},
    ]
    out = merge_roles(roles, cfg)
    assert len(out["widgets"]) == 2
    assert out["widgets"][0]["id"] == "a"
    assert out["widgets"][1]["id"] == "b"

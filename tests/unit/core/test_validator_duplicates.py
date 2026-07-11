"""Corpus checks: duplicate tool names within a single role file."""

from __future__ import annotations

import yaml
from pathlib import Path

import pytest

from generator.validator import duplicate_tool_name_errors, validate_all

pytestmark = [pytest.mark.unit, pytest.mark.core, pytest.mark.readonly]


def test_duplicate_tool_name_errors_finds_case_insensitive_dup() -> None:
    role = {
        "name": "dup-test",
        "description": "1234567890",
        "version": "1.0.0",
        "type": "layer",
        "responsibilities": ["Do something"],
        "tools": [
            {"name": "pytest", "purpose": "Run unit tests"},
            {"name": "  Pytest ", "purpose": "Duplicate entry"},
        ],
    }
    errors = duplicate_tool_name_errors(role)
    assert len(errors) == 1
    assert "duplicate tool name" in errors[0]


def test_duplicate_tool_name_errors_allows_distinct_names() -> None:
    role = {
        "name": "ok-test",
        "description": "1234567890",
        "version": "1.0.0",
        "type": "layer",
        "responsibilities": ["Do something"],
        "tools": [
            {"name": "pytest", "purpose": "Tests"},
            {"name": "ruff", "purpose": "Lint"},
        ],
    }
    assert duplicate_tool_name_errors(role) == []


def test_duplicate_tool_name_errors_ignores_missing_tools() -> None:
    role = {
        "name": "no-tools",
        "description": "1234567890",
        "version": "1.0.0",
        "type": "layer",
        "responsibilities": ["Do something"],
    }
    assert duplicate_tool_name_errors(role) == []


def test_validate_all_reports_duplicates_on_role_file(project_layout) -> None:
    """Full validate_all includes duplicate check alongside JSON Schema."""
    # Navigate from tests/unit/core/ to root, then to data/schemas
    schemas = Path(__file__).resolve().parent.parent.parent.parent / "data" / "schemas"
    project_layout.schemas.mkdir(parents=True)
    import shutil

    shutil.copy(
        schemas / "base-role.schema.json",
        project_layout.schemas / "base-role.schema.json",
    )
    shutil.copy(
        schemas / "recipe.schema.json",
        project_layout.schemas / "recipe.schema.json",
    )

    (project_layout.base / "layer").mkdir(parents=True)
    bad = {
        "name": "bad-layer",
        "description": "1234567890",
        "version": "1.0.0",
        "type": "layer",
        "responsibilities": ["x"],
        "tools": [
            {"name": "curl", "purpose": "HTTP"},
            {"name": "CURL", "purpose": "dup"},
        ],
    }
    with open(
        project_layout.base / "layer" / "bad-layer.yaml", "w", encoding="utf-8"
    ) as f:
        yaml.dump(bad, f, default_flow_style=False, sort_keys=False)

    results = validate_all(project_layout.root)
    expected_file = Path("data") / "base" / "layer" / "bad-layer.yaml"
    result_paths = {Path(k) for k in results}
    assert expected_file in result_paths
    msgs = " ".join(next(v for k, v in results.items() if Path(k) == expected_file))
    assert "duplicate tool name" in msgs


def test_real_project_roles_have_no_duplicate_tools(real_project: Path) -> None:
    results = validate_all(real_project)
    for path, errors in results.items():
        for err in errors:
            assert "duplicate tool name" not in err, f"{path}: {err}"

"""Unit tests: validate_all id checks, and Claude user-cache fallback for worktrees."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from generator.project_layout import ProjectLayout
from generator.claude_layout import find_cached_claude_recipe, set_active_claude
from generator.routing.strategies import ClaudeRoutingStrategy
from generator.validator import validate_all

pytestmark = [pytest.mark.unit]

ROLE = """name: {name}
description: A test role used for validation
version: "1.0.0"
type: layer
responsibilities:
  - r
guidelines:
{guidelines}
"""


@pytest.fixture
def tree(project_layout, real_project) -> Path:
    shutil.copytree(real_project / "data" / "schemas", project_layout.schemas)
    project_layout.base.mkdir(parents=True)
    return project_layout.root


def _role(tree: Path, name: str, guidelines: str) -> None:
    path = ProjectLayout(tree).base / f"{name}.yaml"
    path.write_text(ROLE.format(name=name, guidelines=guidelines), encoding="utf-8")


def test_validate_all_flags_missing_and_duplicate_ids(tree):
    _role(tree, "one", "  - id: T-1\n    text: a\n  - id: T-1\n    text: b\n  - plain")
    _role(tree, "two", "  - id: T-1\n    text: c")
    results = validate_all(tree)
    one = " ".join([v for k, v in results.items() if k.endswith("one.yaml")][0])
    assert "duplicate id" in one and "missing id" in one
    two = [v for k, v in results.items() if k.endswith("two.yaml")][0]
    assert any("already used in" in e for e in two)


def test_validate_all_accepts_unique_ids(tree):
    _role(tree, "ok", "  - id: OK-1\n    text: a\n  - id: OK-2\n    text: b")
    assert not [k for k in validate_all(tree) if k.endswith("ok.yaml")]


def test_validate_all_flags_non_mapping_role(tree):
    (ProjectLayout(tree).base / "bad.yaml").write_text("- a\n- b\n", encoding="utf-8")
    results = validate_all(tree)
    assert any(v == ["Not a valid YAML mapping"] for v in results.values())


@pytest.fixture
def two_homes(tmp_path, monkeypatch):
    home = tmp_path / "home"
    cache = home / ".personetta" / "claude-recipes"
    cache.mkdir(parents=True)
    (cache / "implement-python.md").write_text("# body\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    project = tmp_path / "proj"
    project.mkdir()
    return home, project


def test_find_cached_recipe_strict_vs_fallback(two_homes):
    _home, project = two_homes
    assert find_cached_claude_recipe(project, "implement-python") is None
    found = find_cached_claude_recipe(
        project, "implement-python", user_cache_fallback=True
    )
    assert found is not None and found.name == "implement-python.md"
    assert find_cached_claude_recipe(project, "nope", user_cache_fallback=True) is None


def test_set_active_claude_fallback_writes_project_file(two_homes, tmp_path):
    home, project = two_homes
    with pytest.raises(FileNotFoundError):
        set_active_claude(tmp_path, project, "implement-python")
    dest = set_active_claude(
        tmp_path, project, "implement-python", user_cache_fallback=True
    )
    assert dest.is_relative_to(project) and dest.read_text(encoding="utf-8") == "# body\n"


def test_claude_strategy_with_fallback_sees_user_cache(two_homes, tmp_path):
    _home, project = two_homes
    strict, loose = ClaudeRoutingStrategy(), ClaudeRoutingStrategy(
        user_cache_fallback=True
    )
    assert not strict.is_cached(project, "implement-python")
    assert loose.is_cached(project, "implement-python")
    assert loose.recipe_body(project, "implement-python") == "# body\n"
    assert loose.active_file(project).name == "personetta-active.md"
    loose.switch(project, "implement-python", tmp_path)
    assert loose.current_active(project) == "implement-python"

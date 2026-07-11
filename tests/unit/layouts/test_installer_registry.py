"""Installer paths and registry stay aligned (data-driven output formats)."""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.installer import get_install_path, get_source_dir, install_output
from generator.loader import load_merge_config, load_recipe, load_recipe_roles
from generator.merger import compose_recipe
from generator.output_formats import (
    FORMAT_NAMES,
    format_role,
    get_format_spec,
    iter_specs,
)

pytestmark = [pytest.mark.unit, pytest.mark.layouts]


@pytest.mark.parametrize("fmt", list(FORMAT_NAMES))
def test_get_install_path_matches_spec_install_file(tmp_path: Path, fmt: str) -> None:
    root = tmp_path / "install-root"
    spec = get_format_spec(fmt)
    expected = spec.install_file(root, "my-recipe")
    assert get_install_path(fmt, "my-recipe", root) == expected


@pytest.mark.parametrize("fmt", list(FORMAT_NAMES))
def test_get_source_dir_matches_spec_install_dir(tmp_path: Path, fmt: str) -> None:
    base = tmp_path / "base"
    spec = get_format_spec(fmt)
    assert get_source_dir(fmt, base) == spec.install_dir(base)


def test_copilot_install_path_varies_by_recipe_name(tmp_path: Path) -> None:
    root = tmp_path
    a = get_install_path("copilot", "recipe-a", root)
    b = get_install_path("copilot", "recipe-b", root)
    assert a != b
    assert a == root / ".personetta" / "copilot-recipes" / "recipe-a.md"
    assert b == root / ".personetta" / "copilot-recipes" / "recipe-b.md"


@pytest.mark.parametrize("fmt", list(FORMAT_NAMES))
def test_install_output_writes_to_get_install_path(
    populated_project: Path,
    tmp_path: Path,
    fmt: str,
) -> None:
    target = tmp_path / "out"
    recipe_name = "test-recipe"
    recipe = load_recipe(recipe_name, populated_project)
    compose_roles, mixin_roles = load_recipe_roles(recipe, populated_project)
    merge_config = load_merge_config(populated_project)
    composed, _ = compose_recipe(recipe, compose_roles, mixin_roles, merge_config)
    body = format_role(composed, fmt)
    expected = get_install_path(fmt, recipe_name, target)
    dest = install_output(body, fmt, recipe_name, target)
    assert dest == expected
    assert dest.is_file()
    assert dest.read_text(encoding="utf-8") == body


def test_iter_specs_order_matches_format_names() -> None:
    assert tuple(s.name for s in iter_specs()) == FORMAT_NAMES

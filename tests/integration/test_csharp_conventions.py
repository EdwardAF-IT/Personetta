"""Item 3 — verify the dotnet/skills conventions were re-authored natively into Personetta.

These lock in the authored content: the new C# language roles exist, validate as
language roles, and are wired into the intended recipes, and the recipes still
compose without conflicts.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.loader import load_recipe, load_recipe_roles, load_role
from generator.merger import compose_recipe

pytestmark = [pytest.mark.integration]


@pytest.mark.parametrize("name", ["csharp-data", "csharp-aspnet"])
def test_new_csharp_language_roles_exist(project_root: Path, name: str) -> None:
    role = load_role("language-specific/csharp/{0}".format(name), project_root)
    assert role["type"] == "language"
    assert role["name"] == name
    assert role["responsibilities"]
    assert role["guidelines"]


def test_database_recipe_composes_data_role(project_root: Path) -> None:
    recipe = load_recipe("implement-csharp-database", project_root)
    assert "language-specific/csharp/csharp-data" in recipe["compose"]


def test_backend_recipe_composes_aspnet_role(project_root: Path) -> None:
    recipe = load_recipe("implement-csharp-backend", project_root)
    assert "language-specific/csharp/csharp-aspnet" in recipe["compose"]


@pytest.mark.parametrize(
    "name", ["implement-csharp-database", "implement-csharp-backend"]
)
def test_csharp_recipes_compose_without_conflicts(project_root: Path, name: str) -> None:
    recipe = load_recipe(name, project_root)
    compose_roles, mixin_roles = load_recipe_roles(recipe, project_root)
    composed, warnings = compose_recipe(recipe, compose_roles, mixin_roles)
    # EF/data + ASP.NET conventions surface in the merged guidelines.
    assert composed["guidelines"]
    errors = [w for w in warnings if getattr(w, "severity", "") == "error"]
    assert not errors


def test_developer_role_gained_build_and_diagnostics_conventions(
    project_root: Path,
) -> None:
    role = load_role("language-specific/csharp/csharp-developer", project_root)
    blob = " ".join(role["guidelines"]).lower()
    assert "central package management" in blob or "directory.packages.props" in blob
    assert "dotnet-trace" in blob or "dotnet-counters" in blob

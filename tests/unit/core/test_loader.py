from __future__ import annotations

import pytest
from pathlib import Path

from generator.loader import (
    load_yaml,
    resolve_role_path,
    load_role,
    load_recipe,
    load_recipe_roles,
    load_merge_config,
    list_roles,
    list_recipes,
    LoadError,
)
from tests.conftest import write_yaml

pytestmark = [pytest.mark.unit, pytest.mark.core, pytest.mark.readonly]


class TestLoadYaml:
    def test_load_valid_yaml(self, tmp_path: Path):
        data = {"name": "test", "value": 42}
        path = write_yaml(tmp_path / "test.yaml", data)
        result = load_yaml(path)
        assert result == data

    def test_load_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(LoadError, match="File not found"):
            load_yaml(tmp_path / "missing.yaml")

    def test_load_invalid_yaml_raises(self, tmp_path: Path):
        path = tmp_path / "bad.yaml"
        path.write_text(":\n  - :\n    bad: [", encoding="utf-8")
        with pytest.raises(LoadError, match="Invalid YAML"):
            load_yaml(path)

    def test_load_non_mapping_raises(self, tmp_path: Path):
        path = tmp_path / "list.yaml"
        path.write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(LoadError, match="Expected a YAML mapping"):
            load_yaml(path)


class TestResolveRolePath:
    def test_full_path_with_slashes(self, project_layout):
        # Create src directory for dev mode detection
        (project_layout.root / "src").mkdir()
        result = resolve_role_path("base/lifecycle/architect", project_layout.root)
        assert result == project_layout.base / "lifecycle" / "architect.yaml"

    def test_language_specific_path(self, project_layout):
        # Create src directory for dev mode detection
        (project_layout.root / "src").mkdir()
        result = resolve_role_path(
            "language-specific/python/python-developer", project_layout.root
        )
        assert (
            result
            == project_layout.language_specific / "python" / "python-developer.yaml"
        )

    def test_short_name_resolves_to_mixins(self, project_layout):
        # Create src directory for dev mode detection
        (project_layout.root / "src").mkdir()
        result = resolve_role_path("security-aware", project_layout.root)
        assert result == project_layout.base / "mixins" / "security-aware.yaml"

    def test_short_name_no_slashes(self, project_layout):
        # Create src directory for dev mode detection
        (project_layout.root / "src").mkdir()
        result = resolve_role_path("performance-focused", project_layout.root)
        assert result == project_layout.base / "mixins" / "performance-focused.yaml"


class TestLoadRole:
    def test_load_valid_role(self, populated_project: Path):
        role = load_role("base/lifecycle/test-developer", populated_project)
        assert role["name"] == "test-developer"
        assert role["type"] == "lifecycle"
        assert len(role["responsibilities"]) == 2

    def test_load_mixin_by_short_name(self, populated_project: Path):
        role = load_role("test-security", populated_project)
        assert role["name"] == "test-security"
        assert role["type"] == "mixin"

    def test_load_missing_role_raises(self, populated_project: Path):
        with pytest.raises(LoadError, match="File not found"):
            load_role("base/lifecycle/nonexistent", populated_project)

    def test_load_role_missing_name_raises(self, project_layout):
        data = {"responsibilities": ["do stuff"]}
        write_yaml(project_layout.base / "mixins" / "bad.yaml", data)
        with pytest.raises(LoadError, match="missing required field 'name'"):
            load_role("bad", project_layout.root)

    def test_load_role_missing_responsibilities_raises(self, project_layout):
        data = {"name": "bad-role", "type": "mixin"}
        write_yaml(project_layout.base / "mixins" / "incomplete.yaml", data)
        with pytest.raises(LoadError, match="missing required field 'responsibilities'"):
            load_role("incomplete", project_layout.root)


class TestLoadRecipe:
    def test_load_by_name(self, populated_project: Path):
        recipe = load_recipe("test-recipe", populated_project)
        assert recipe["name"] == "test-recipe"
        assert len(recipe["compose"]) == 3

    def test_load_by_path(self, populated_project: Path):
        recipe = load_recipe("data/recipes/test-recipe.yaml", populated_project)
        assert recipe["name"] == "test-recipe"

    def test_load_missing_recipe_raises(self, populated_project: Path):
        with pytest.raises(LoadError, match="File not found"):
            load_recipe("nonexistent-recipe", populated_project)

    def test_load_recipe_missing_compose_raises(self, project_layout):
        data = {"name": "bad-recipe"}
        write_yaml(project_layout.recipes / "bad.yaml", data)
        with pytest.raises(LoadError, match="missing or empty 'compose'"):
            load_recipe("bad", project_layout.root)


class TestLoadRecipeRoles:
    def test_loads_compose_and_mixin_roles(self, populated_project: Path):
        recipe = load_recipe("test-recipe", populated_project)
        compose_roles, mixin_roles = load_recipe_roles(recipe, populated_project)
        assert len(compose_roles) == 3
        assert len(mixin_roles) == 1
        assert compose_roles[0]["name"] == "test-developer"
        assert mixin_roles[0]["name"] == "test-security"

    def test_recipe_with_no_mixins(self, populated_project: Path):
        recipe = {
            "name": "no-mixins",
            "compose": ["base/lifecycle/test-developer"],
        }
        write_yaml(populated_project / "recipes" / "no-mixins.yaml", recipe)
        compose_roles, mixin_roles = load_recipe_roles(recipe, populated_project)
        assert len(compose_roles) == 1
        assert len(mixin_roles) == 0

    def test_missing_compose_role_raises(self, populated_project: Path):
        recipe = {
            "name": "broken",
            "compose": ["base/lifecycle/nonexistent"],
        }
        with pytest.raises(LoadError, match="File not found"):
            load_recipe_roles(recipe, populated_project)


class TestLoadMergeConfig:
    def test_loads_config(self, populated_project: Path):
        config = load_merge_config(populated_project)
        assert config["philosophy"] == "pragmatic"
        assert "field_strategies" in config


class TestListRoles:
    def test_lists_all_roles(self, populated_project: Path):
        roles = list_roles(populated_project)
        names = {r["name"] for r in roles}
        assert "test-developer" in names
        assert "test-backend" in names
        assert "test-python" in names
        assert "test-security" in names

    def test_role_entries_have_required_fields(self, populated_project: Path):
        roles = list_roles(populated_project)
        for role in roles:
            assert "name" in role
            assert "type" in role
            assert "path" in role


class TestListRecipes:
    def test_lists_all_recipes(self, populated_project: Path):
        recipes = list_recipes(populated_project)
        names = {r["name"] for r in recipes}
        assert "test-recipe" in names

    def test_recipe_entries_have_required_fields(self, populated_project: Path):
        recipes = list_recipes(populated_project)
        for recipe in recipes:
            assert "name" in recipe
            assert "compose" in recipe
            assert "path" in recipe
            assert "activation_phrases" in recipe
            assert isinstance(recipe["activation_phrases"], list)

    def test_activation_phrases_on_real_recipe(self, real_project: Path):
        recipes = {r["name"]: r for r in list_recipes(real_project)}
        cs = recipes.get("implement-csharp-backend")
        assert cs is not None
        assert len(cs["activation_phrases"]) >= 1
        assert any("C#" in p for p in cs["activation_phrases"])

from __future__ import annotations


import pytest


from generator.loader import (
    load_recipe,
    load_recipe_roles,
    load_merge_config,
    list_recipes,
)
from generator.merger import compose_recipe
from generator.output_formats import FORMAT_NAMES, format_role

pytestmark = pytest.mark.integration


class TestEndToEnd:
    """Test the full pipeline: recipe -> load -> merge -> format."""

    def test_full_pipeline_cursor(self, populated_project):
        recipe = load_recipe("test-recipe", populated_project)
        compose_roles, mixin_roles = load_recipe_roles(recipe, populated_project)
        config = load_merge_config(populated_project)
        composed, warnings = compose_recipe(recipe, compose_roles, mixin_roles, config)
        output = format_role(composed, "cursor")

        assert "# Test Recipe" in output
        assert "## Responsibilities" in output
        assert "- Write clean code" in output
        assert "- Identify injection risks" in output
        assert "## Tone" in output
        assert "Pragmatic And Clean" in output
        assert "## Tools" in output
        assert "**pytest**" in output

        error_warnings = [w for w in warnings if w.severity == "error"]
        assert len(error_warnings) == 0

    def test_full_pipeline_copilot(self, populated_project):
        recipe = load_recipe("test-recipe", populated_project)
        compose_roles, mixin_roles = load_recipe_roles(recipe, populated_project)
        config = load_merge_config(populated_project)
        composed, warnings = compose_recipe(recipe, compose_roles, mixin_roles, config)
        output = format_role(composed, "copilot")

        assert "## You Should" in output
        assert "- Write clean code" in output

    def test_full_pipeline_claude(self, populated_project):
        recipe = load_recipe("test-recipe", populated_project)
        compose_roles, mixin_roles = load_recipe_roles(recipe, populated_project)
        config = load_merge_config(populated_project)
        composed, warnings = compose_recipe(recipe, compose_roles, mixin_roles, config)
        output = format_role(composed, "claude")

        # Claude uses markdown format (same as Copilot per REQUIREMENTS.md)
        assert "## You Should" in output
        assert "- Write clean code" in output

    def test_full_pipeline_cline(self, populated_project):
        recipe = load_recipe("test-recipe", populated_project)
        compose_roles, mixin_roles = load_recipe_roles(recipe, populated_project)
        config = load_merge_config(populated_project)
        composed, warnings = compose_recipe(recipe, compose_roles, mixin_roles, config)
        output = format_role(composed, "cline")

        assert "## You Should" in output
        assert "- Write clean code" in output
        assert output == format_role(composed, "copilot")

        error_warnings = [w for w in warnings if w.severity == "error"]
        assert len(error_warnings) == 0

    def test_mixin_adds_without_overriding_tone(self, populated_project):
        recipe = load_recipe("test-recipe", populated_project)
        compose_roles, mixin_roles = load_recipe_roles(recipe, populated_project)
        config = load_merge_config(populated_project)
        composed, _ = compose_recipe(recipe, compose_roles, mixin_roles, config)

        assert composed["tone"] == "pragmatic-and-clean"
        assert "Identify injection risks" in composed["responsibilities"]

    def test_guideline_deduplication(self, populated_project):
        recipe = load_recipe("test-recipe", populated_project)
        compose_roles, mixin_roles = load_recipe_roles(recipe, populated_project)
        config = load_merge_config(populated_project)
        composed, _ = compose_recipe(recipe, compose_roles, mixin_roles, config)

        occurrences = composed["guidelines"].count("Never trust client input")
        assert occurrences == 1


class TestEndToEndWithRealData:
    """Test against the actual project roles and recipes."""

    def test_real_recipe_generates_without_errors(self, real_project):
        recipe = load_recipe("implement-csharp-backend", real_project)
        compose_roles, mixin_roles = load_recipe_roles(recipe, real_project)
        config = load_merge_config(real_project)
        composed, warnings = compose_recipe(recipe, compose_roles, mixin_roles, config)
        output = format_role(composed, "cursor")

        error_warnings = [w for w in warnings if w.severity == "error"]
        assert len(error_warnings) == 0
        assert len(output) > 500
        assert "## Responsibilities" in output

    def test_all_real_recipes_generate_without_errors(self, real_project):
        recipes = list_recipes(real_project)
        assert len(recipes) > 0

        for recipe_info in recipes:
            recipe = load_recipe(recipe_info["name"], real_project)
            compose_roles, mixin_roles = load_recipe_roles(recipe, real_project)
            config = load_merge_config(real_project)
            composed, warnings = compose_recipe(
                recipe, compose_roles, mixin_roles, config
            )

            error_warnings = [w for w in warnings if w.severity == "error"]
            assert (
                len(error_warnings) == 0
            ), f"Recipe '{recipe_info['name']}' has conflicts: " + "; ".join(
                w.message for w in error_warnings
            )

            for fmt in FORMAT_NAMES:
                output = format_role(composed, fmt)
                assert (
                    len(output) > 100
                ), f"Recipe '{recipe_info['name']}' produced suspiciously short {fmt} output"

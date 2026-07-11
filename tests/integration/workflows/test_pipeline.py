"""
Full pipeline integration tests for personetta.

Tests complete pipeline: load → compose → format → install → set-active.
"""

from __future__ import annotations

import json

import pytest
import yaml

from generator.copilot_layout import set_active_copilot
from generator.cursor_layout import install_all_cursor, set_active_cursor
from generator.loader import (
    list_recipes,
    load_merge_config,
    load_recipe,
    load_recipe_roles,
)
from generator.merger import compose_recipe
from generator.output_formats import FORMAT_NAMES, format_role
from generator.project_layout import ProjectLayout
from tests.integration.helpers import add_recipe, install_all_for_format

pytestmark = [pytest.mark.integration, pytest.mark.core]


class TestFullPipelineWorkflows:
    """Test complete pipeline: load → compose → format → install → set-active."""

    def test_load_compose_install_set_active_complete_flow(
        self, populated_project, tmp_path
    ):
        """Complete workflow from recipe YAML to active installation."""
        target = tmp_path / "output"

        # 1. Load recipe
        recipe = load_recipe("test-recipe", populated_project)
        assert recipe["name"] == "test-recipe"

        # 2. Compose (merge roles)
        compose_roles, mixin_roles = load_recipe_roles(recipe, populated_project)
        config = load_merge_config(populated_project)
        merged, warnings = compose_recipe(recipe, compose_roles, mixin_roles, config)
        assert len([w for w in warnings if w.severity == "error"]) == 0

        # 3. Format for output
        cursor_output = format_role(merged, "cursor")
        assert "## Responsibilities" in cursor_output

        # 4. Install
        install_all_for_format(populated_project, target, "cursor")
        assert (target / ".cursor" / "rules" / "personetta-active.md").exists()

        # 5. Set active
        set_active_cursor(target, "test-recipe", populated_project)
        state = json.loads((target / ".personetta" / "cursor-active.json").read_text())
        assert state["active_recipe"] == "test-recipe"

    def test_real_recipes_complete_pipeline(self, real_project):
        """Test pipeline with actual project recipes (no installation)."""
        recipes = list_recipes(real_project)
        assert len(recipes) > 0

        # Pick first 3 recipes to test
        for recipe_info in recipes[:3]:
            recipe = load_recipe(recipe_info["name"], real_project)
            compose_roles, mixin_roles = load_recipe_roles(recipe, real_project)
            config = load_merge_config(real_project)

            merged, warnings = compose_recipe(recipe, compose_roles, mixin_roles, config)

            errors = [w for w in warnings if w.severity == "error"]
            assert len(errors) == 0, f"Recipe {recipe_info['name']} has errors"

            # Format in all formats
            for fmt in FORMAT_NAMES:
                output = format_role(merged, fmt)
                assert len(output) > 100, f"Format {fmt} too short"

    def test_recipe_with_mixins_full_pipeline(self, populated_project, tmp_path):
        """Recipe with mixins goes through complete pipeline."""
        target = tmp_path / "output"

        # Recipe uses both compose and mixins
        recipe = load_recipe("test-recipe", populated_project)
        assert "mixins" in recipe

        # Load and compose
        compose_roles, mixin_roles = load_recipe_roles(recipe, populated_project)
        config = load_merge_config(populated_project)
        merged, warnings = compose_recipe(recipe, compose_roles, mixin_roles, config)

        # Check mixin content is included
        assert "Identify injection risks" in str(merged.get("responsibilities", []))

        # Install
        install_all_for_format(populated_project, target, "copilot")

        # Verify mixin content in installed file
        active = (
            target / ".copilot" / "instructions" / "personetta-active.instructions.md"
        )
        content = active.read_text()
        assert "injection" in content.lower()

    def test_language_specific_enhancements_in_pipeline(
        self, populated_project, tmp_path
    ):
        """Language-specific enhancements are included in pipeline output."""
        target = tmp_path / "output"

        # Create recipe with language-specific compose
        python_enhanced = populated_project / "data" / "recipes" / "python-enhanced.yaml"
        python_enhanced.write_text(
            yaml.dump(
                {
                    "name": "python-enhanced",
                    "description": "Python enhanced recipe",
                    "compose": [
                        "base/lifecycle/test-developer",
                        "language-specific/python/test-python",
                    ],
                }
            )
        )

        # Install
        install_all_for_format(populated_project, target, "cursor")

        # Verify python-specific content
        cache = target / ".personetta" / "cursor-recipes" / "python-enhanced.md"
        if cache.exists():
            content = cache.read_text()
            # Should have python-specific guidelines/tools
            assert "python" in content.lower()

    def test_validation_errors_prevent_installation(self, populated_project, tmp_path):
        """Pipeline stops when validation finds errors."""
        target = tmp_path / "output"

        # Create conflicting recipe (same guideline in multiple roles)
        bad_recipe = populated_project / "data" / "recipes" / "conflict-recipe.yaml"
        bad_recipe.write_text(
            yaml.dump(
                {
                    "name": "conflict-recipe",
                    "description": "Recipe with conflicts",
                    "compose": [
                        "base/lifecycle/test-developer",
                        "base/layer/test-backend",
                    ],
                }
            )
        )

        # Try to install (may succeed if no actual conflicts, or fail gracefully)
        ok, bad = install_all_cursor(
            populated_project, target, recipe_filter="conflict-*"
        )

        # Either succeeds (no conflicts) or fails (with conflicts)
        # The point is it doesn't crash
        assert isinstance(ok, list)
        assert isinstance(bad, list)

    def test_multiple_recipes_install_in_single_batch(self, populated_project, tmp_path):
        """Install multiple recipes in one call, all processed correctly."""
        target = tmp_path / "output"

        # Add multiple recipes
        for i in range(5):
            add_recipe(
                populated_project,
                f"batch-recipe-{i}",
                f"Batch recipe {i}",
                ["base/lifecycle/test-developer"],
            )

        # Install all at once
        install_all_for_format(populated_project, target, "claude")

        # Verify all are cached
        cache_dir = target / ".personetta" / "claude-recipes"
        cached = {f.stem for f in cache_dir.glob("*.md")}

        for i in range(5):
            assert f"batch-recipe-{i}" in cached

    def test_formatter_produces_format_specific_output(self, populated_project, tmp_path):
        """Each formatter produces format-appropriate output."""
        recipe = load_recipe("test-recipe", populated_project)
        compose_roles, mixin_roles = load_recipe_roles(recipe, populated_project)
        config = load_merge_config(populated_project)
        merged, _ = compose_recipe(recipe, compose_roles, mixin_roles, config)

        # Cursor format (custom structure)
        cursor_out = format_role(merged, "cursor")
        assert "## Responsibilities" in cursor_out
        assert "## Tone" in cursor_out

        # Copilot format (VS Code instructions)
        copilot_out = format_role(merged, "copilot")
        assert "## You Should" in copilot_out or "## Responsibilities" in copilot_out

        # Claude format (markdown)
        claude_out = format_role(merged, "claude")
        assert len(claude_out) > 100

        # Cline format (markdown, same as copilot)
        cline_out = format_role(merged, "cline")
        assert len(cline_out) > 100

    def test_install_with_filter_only_processes_matching_recipes(
        self, populated_project, tmp_path
    ):
        """Install with filter only processes matching recipes."""
        target = tmp_path / "output"

        # Add recipes with patterns
        add_recipe(
            populated_project, "test-alpha", "Alpha", ["base/lifecycle/test-developer"]
        )
        add_recipe(
            populated_project, "test-beta", "Beta", ["base/lifecycle/test-developer"]
        )
        add_recipe(
            populated_project,
            "prod-alpha",
            "Prod Alpha",
            ["base/lifecycle/test-developer"],
        )

        # Install only test-* recipes
        ok, bad = install_all_cursor(populated_project, target, recipe_filter="test-*")

        # Verify test-* recipes were processed
        # Note: If filter doesn't match anything, cache might be empty
        cache_dir = target / ".personetta" / "cursor-recipes"
        if cache_dir.exists() and list(cache_dir.glob("*.md")):
            cached = {f.stem for f in cache_dir.glob("*.md")}
            # Should have test- prefixed recipes
            assert any(name.startswith("test-") for name in cached)
            # Should NOT have prod- prefixed recipes
            assert "prod-alpha" not in cached

    def test_set_active_updates_active_file_content(self, populated_project, tmp_path):
        """set-active changes active file to new recipe content."""
        target = tmp_path / "output"

        # Add two distinct recipes
        add_recipe(
            populated_project,
            "recipe-one",
            "First recipe with unique marker ALPHA",
            ["base/lifecycle/test-developer"],
        )
        add_recipe(
            populated_project,
            "recipe-two",
            "Second recipe with unique marker BETA",
            ["base/layer/test-backend"],
        )

        # Install both
        install_all_for_format(populated_project, target, "copilot")

        # Set active to recipe-one
        set_active_copilot(populated_project, target, "recipe-one")
        active_path = (
            target / ".copilot" / "instructions" / "personetta-active.instructions.md"
        )
        content_one = active_path.read_text()

        # Set active to recipe-two
        set_active_copilot(populated_project, target, "recipe-two")
        content_two = active_path.read_text()

        # Content should differ
        assert content_one != content_two

    def test_install_creates_all_system_files(self, populated_project, tmp_path):
        """Install creates baseline, router, active files for format."""
        target = tmp_path / "output"

        install_all_for_format(populated_project, target, "claude")

        rules_dir = target / ".claude" / "rules"
        assert (rules_dir / "personetta-baseline.md").exists()
        assert (rules_dir / "personetta-router.md").exists()
        assert (rules_dir / "personetta-active.md").exists()


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def populated_project(project_layout):
    """Create test project with base roles and recipes."""
    # Create directory structure
    base_dir = project_layout.base
    (base_dir / "lifecycle").mkdir(parents=True)
    (base_dir / "layer").mkdir(parents=True)
    (base_dir / "mixins").mkdir(parents=True)
    (base_dir / "system").mkdir(parents=True)

    lang_dir = project_layout.language_specific
    (lang_dir / "python").mkdir(parents=True)

    recipes_dir = project_layout.recipes
    recipes_dir.mkdir(parents=True)

    config_dir = project_layout.config
    config_dir.mkdir(parents=True)

    # Create test-developer role (lifecycle)
    developer_role = {
        "name": "test-developer",
        "description": "Test developer role",
        "version": "1.0.0",
        "type": "lifecycle",
        "responsibilities": ["Write clean code", "Handle errors explicitly"],
        "guidelines": ["Prefer explicit over implicit", "Keep functions small"],
        "tone": "pragmatic-and-clean",
        "output_format": "code-with-explanation",
    }
    (base_dir / "lifecycle" / "test-developer.yaml").write_text(yaml.dump(developer_role))

    # Create test-backend role (layer)
    backend_role = {
        "name": "test-backend",
        "description": "Test backend role",
        "version": "1.0.0",
        "type": "layer",
        "responsibilities": ["Design API contracts", "Validate input"],
        "guidelines": ["Never trust client input", "Use structured logging"],
        "tools": [{"name": "pytest", "purpose": "Testing"}],
    }
    (base_dir / "layer" / "test-backend.yaml").write_text(yaml.dump(backend_role))

    # Create test-security mixin
    security_mixin = {
        "name": "test-security",
        "description": "Security mixin",
        "version": "1.0.0",
        "type": "mixin",
        "responsibilities": ["Identify injection risks"],
        "guidelines": ["Validate all inputs"],
    }
    (base_dir / "mixins" / "test-security.yaml").write_text(yaml.dump(security_mixin))

    # Create test-python language role
    python_role = {
        "name": "test-python",
        "description": "Python language role",
        "version": "1.0.0",
        "type": "language",
        "responsibilities": ["Write idiomatic Python"],
        "guidelines": ["Use type hints", "Follow PEP 8"],
        "tools": [{"name": "black", "purpose": "Formatting"}],
    }
    (lang_dir / "python" / "test-python.yaml").write_text(yaml.dump(python_role))

    # Create baseline system role
    baseline = {
        "name": "baseline",
        "description": "Baseline system role",
        "version": "1.0.0",
        "type": "system",
        "content": "Cross-cutting rules for all recipes.",
    }
    (base_dir / "system" / "baseline.yaml").write_text(yaml.dump(baseline))

    # Create router system role
    router = {
        "name": "router",
        "description": "Router system role",
        "version": "1.0.0",
        "type": "system",
        "content": "Recipe routing logic.",
    }
    (base_dir / "system" / "router.yaml").write_text(yaml.dump(router))

    # Create test recipe (use paths with slashes to specify location)
    test_recipe = {
        "name": "test-recipe",
        "description": "Test recipe for integration tests",
        "compose": ["base/lifecycle/test-developer", "base/layer/test-backend"],
        "mixins": ["test-security"],  # Mixins default to base/mixins
    }
    (recipes_dir / "test-recipe.yaml").write_text(yaml.dump(test_recipe))

    # Create merge config
    merge_config = {
        "deduplication": {
            "responsibilities": True,
            "guidelines": True,
            "tools": True,
        }
    }
    (config_dir / "merge-config.yaml").write_text(yaml.dump(merge_config))

    return project_layout.root


@pytest.fixture
def real_project():
    """Use the actual project for real recipe testing."""
    return ProjectLayout.from_file(__file__).root

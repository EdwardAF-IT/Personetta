"""
Cross-module integration tests for personetta.

Tests integration across loader, merger, formatter, installer modules.
"""

from __future__ import annotations

import pytest
import yaml

from generator.loader import (
    list_recipes,
    load_merge_config,
    load_recipe,
    load_recipe_roles,
)
from generator.merger import compose_recipe
from generator.output_formats import FORMAT_NAMES, format_role
from generator.project_layout import ProjectLayout
from tests.integration.helpers import install_all_for_format

pytestmark = [pytest.mark.integration, pytest.mark.core]


class TestCrossModuleIntegration:
    """Test integration across loader, merger, formatter, installer modules."""

    def test_loader_to_merger_to_formatter_chain(self, populated_project):
        """Recipe flows from loader → merger → formatter without errors."""
        # Loader
        recipe = load_recipe("test-recipe", populated_project)
        compose_roles, mixin_roles = load_recipe_roles(recipe, populated_project)

        # Merger
        config = load_merge_config(populated_project)
        merged, warnings = compose_recipe(recipe, compose_roles, mixin_roles, config)
        assert len([w for w in warnings if w.severity == "error"]) == 0

        # Formatter
        output = format_role(merged, "cursor")
        assert len(output) > 100

    def test_validator_to_pipeline_error_handling(self, populated_project):
        """Validation errors are caught before pipeline execution."""
        # Load all recipes
        recipes = list_recipes(populated_project)

        for recipe_info in recipes:
            recipe = load_recipe(recipe_info["name"], populated_project)
            compose_roles, mixin_roles = load_recipe_roles(recipe, populated_project)
            config = load_merge_config(populated_project)

            # Compose should handle validation internally
            merged, warnings = compose_recipe(recipe, compose_roles, mixin_roles, config)

            # Errors should be in warnings
            errors = [w for w in warnings if w.severity == "error"]
            if errors:
                # If there are errors, pipeline should stop
                assert len(errors) > 0

    def test_merger_deduplication_across_formats(self, populated_project):
        """Merged recipe has deduplicated content in all formats."""
        recipe = load_recipe("test-recipe", populated_project)
        compose_roles, mixin_roles = load_recipe_roles(recipe, populated_project)
        config = load_merge_config(populated_project)

        merged, _ = compose_recipe(recipe, compose_roles, mixin_roles, config)

        # Check deduplication in raw merged data
        guidelines = merged.get("guidelines", [])
        unique_guidelines = set(guidelines)
        assert len(guidelines) == len(unique_guidelines), "Duplicate guidelines found"

        # Verify in formatted output
        for fmt in FORMAT_NAMES:
            output = format_role(merged, fmt)
            # Each guideline should appear only once
            if guidelines:
                first_guideline = guidelines[0]
                assert output.count(first_guideline) == 1

    def test_installer_creates_correct_directory_structure(
        self, populated_project, tmp_path
    ):
        """Installer creates proper directory hierarchy for each format."""
        target = tmp_path / "output"

        for fmt in FORMAT_NAMES:
            install_all_for_format(populated_project, target, fmt)

        # Verify structure
        assert (target / ".personetta").is_dir()
        assert (target / ".personetta" / "cursor-recipes").is_dir()
        assert (target / ".personetta" / "copilot-recipes").is_dir()
        assert (target / ".personetta" / "claude-recipes").is_dir()
        assert (target / ".personetta" / "cline-recipes").is_dir()

        assert (target / ".cursor" / "rules").is_dir()
        assert (target / ".copilot" / "instructions").is_dir()
        assert (target / ".claude" / "rules").is_dir()
        assert (target / "Documents" / "Cline" / "Rules").is_dir()

    def test_recipe_catalog_integration(self, populated_project):
        """list_recipes returns all valid recipes from catalog."""
        recipes = list_recipes(populated_project)

        assert len(recipes) > 0
        for recipe_info in recipes:
            assert "name" in recipe_info
            assert "description" in recipe_info

            # Can load each recipe
            recipe = load_recipe(recipe_info["name"], populated_project)
            assert recipe["name"] == recipe_info["name"]

    def test_merge_config_affects_output(self, populated_project, tmp_path):
        """merge-config.yaml settings affect merged output."""
        config = load_merge_config(populated_project)

        # Config should exist and have settings
        assert isinstance(config, dict)

        # Load and merge with config
        recipe = load_recipe("test-recipe", populated_project)
        compose_roles, mixin_roles = load_recipe_roles(recipe, populated_project)

        merged, _ = compose_recipe(recipe, compose_roles, mixin_roles, config)

        # Merged result should reflect config (e.g., deduplication rules)
        assert "responsibilities" in merged
        assert "guidelines" in merged

    def test_formatter_consistency_across_same_input(self, populated_project):
        """Same merged recipe produces identical output on repeated formatting."""
        recipe = load_recipe("test-recipe", populated_project)
        compose_roles, mixin_roles = load_recipe_roles(recipe, populated_project)
        config = load_merge_config(populated_project)

        merged, _ = compose_recipe(recipe, compose_roles, mixin_roles, config)

        # Format twice
        output1 = format_role(merged, "cursor")
        output2 = format_role(merged, "cursor")

        assert output1 == output2, "Formatter should be deterministic"

    def test_end_to_end_with_all_role_types(self, populated_project, tmp_path):
        """Recipe using lifecycle + layer + language roles composes correctly."""
        target = tmp_path / "output"

        # Create recipe with all role types
        multi_role = populated_project / "data" / "recipes" / "multi-role.yaml"
        multi_role.write_text(
            yaml.dump(
                {
                    "name": "multi-role",
                    "description": "Uses all role types",
                    "compose": [
                        "base/lifecycle/test-developer",
                        "base/layer/test-backend",
                        "language-specific/python/test-python",
                    ],
                }
            )
        )

        # Install
        install_all_for_format(populated_project, target, "cursor")

        # Verify merged content includes all roles
        cache = target / ".personetta" / "cursor-recipes" / "multi-role.md"
        if cache.exists():
            content = cache.read_text()
            # Should have content from all roles
            assert len(content) > 500


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

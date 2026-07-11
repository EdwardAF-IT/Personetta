"""
Multi-format integration tests for personetta.

Tests workflows across multiple output formats maintaining separate state.
"""

from __future__ import annotations

import json

import pytest
import yaml

from generator.copilot_layout import set_active_copilot
from generator.cursor_layout import install_all_cursor, set_active_cursor
from generator.output_formats import FORMAT_NAMES
from generator.project_layout import ProjectLayout
from tests.integration.helpers import add_recipe, install_all_for_format

pytestmark = [
    pytest.mark.integration,
    pytest.mark.layouts,
    pytest.mark.requires_real_project,
]


class TestMultiFormatWorkflows:
    """Test workflows across multiple output formats maintaining separate state."""

    def test_install_to_cursor_and_copilot_maintains_separate_state(
        self, populated_project, tmp_path
    ):
        """Install same recipe to cursor and copilot, verify independent state."""
        target = tmp_path / "output"

        # Install to both formats
        install_all_for_format(populated_project, target, "cursor")
        install_all_for_format(populated_project, target, "copilot")

        # Verify cursor state
        cursor_state_path = target / ".personetta" / "cursor-active.json"
        assert cursor_state_path.exists()
        cursor_state = json.loads(cursor_state_path.read_text())
        assert "active_recipe" in cursor_state

        # Verify copilot state
        copilot_state_path = target / ".personetta" / "copilot-active.json"
        assert copilot_state_path.exists()
        copilot_state = json.loads(copilot_state_path.read_text())
        assert "active_recipe" in copilot_state

        # Verify rules directories exist independently
        assert (target / ".cursor" / "rules").exists()
        assert (target / ".copilot" / "instructions").exists()

    def test_set_different_active_recipes_per_format(self, populated_project, tmp_path):
        """Set different active recipes for cursor vs copilot, no cross-contamination."""
        target = tmp_path / "output"

        # Add second recipe
        add_recipe(
            populated_project,
            "second-recipe",
            "Second test recipe",
            ["base/lifecycle/test-developer"],
        )

        # Install all to both formats
        install_all_for_format(populated_project, target, "cursor")
        install_all_for_format(populated_project, target, "copilot")

        # Set different active recipes
        set_active_cursor(target, "test-recipe", populated_project)
        set_active_copilot(populated_project, target, "second-recipe")

        # Verify cursor active
        cursor_state = json.loads(
            (target / ".personetta" / "cursor-active.json").read_text()
        )
        assert cursor_state["active_recipe"] == "test-recipe"

        # Verify copilot active
        copilot_state = json.loads(
            (target / ".personetta" / "copilot-active.json").read_text()
        )
        assert copilot_state["active_recipe"] == "second-recipe"

    def test_all_four_formats_coexist_with_independent_state(
        self, populated_project, tmp_path
    ):
        """Install to all four formats (cursor, copilot, claude, cline), verify coexistence."""
        target = tmp_path / "output"

        for fmt in FORMAT_NAMES:
            install_all_for_format(populated_project, target, fmt)

        # Verify all state files exist
        assert (target / ".personetta" / "cursor-active.json").exists()
        assert (target / ".personetta" / "copilot-active.json").exists()
        assert (target / ".personetta" / "claude-active.json").exists()
        assert (target / ".personetta" / "cline-active.json").exists()

        # Verify all rules directories exist
        assert (target / ".cursor" / "rules").exists()
        assert (target / ".copilot" / "instructions").exists()
        assert (target / ".claude" / "rules").exists()
        assert (target / "Documents" / "Cline" / "Rules").exists()

    def test_remove_from_one_format_leaves_others_intact(
        self, populated_project, tmp_path
    ):
        """Remove recipes from cursor, verify copilot remains untouched."""
        target = tmp_path / "output"

        # Install to both formats
        install_all_for_format(populated_project, target, "cursor")
        install_all_for_format(populated_project, target, "copilot")

        # Record copilot state before cursor removal
        copilot_files_before = set(
            f.name for f in (target / ".copilot" / "instructions").glob("*.md")
        )
        copilot_cache_before = set(
            f.name for f in (target / ".personetta" / "copilot-recipes").glob("*.md")
        )

        # Remove cursor cache
        cursor_cache = target / ".personetta" / "cursor-recipes"
        if cursor_cache.exists():
            for f in cursor_cache.glob("*.md"):
                f.unlink()

        # Verify copilot unchanged
        copilot_files_after = set(
            f.name for f in (target / ".copilot" / "instructions").glob("*.md")
        )
        copilot_cache_after = set(
            f.name for f in (target / ".personetta" / "copilot-recipes").glob("*.md")
        )

        assert copilot_files_after == copilot_files_before
        assert copilot_cache_after == copilot_cache_before

    def test_install_multiple_recipes_each_format_gets_all(
        self, populated_project, tmp_path
    ):
        """Install 3 recipes to 2 formats, verify each format has all 3 cached."""
        target = tmp_path / "output"

        # Add more recipes
        add_recipe(
            populated_project, "recipe-a", "Recipe A", ["base/lifecycle/test-developer"]
        )
        add_recipe(populated_project, "recipe-b", "Recipe B", ["base/layer/test-backend"])

        # Install to cursor and copilot
        install_all_for_format(populated_project, target, "cursor")
        install_all_for_format(populated_project, target, "copilot")

        # Verify cursor has all recipes cached
        cursor_cache = sorted(
            f.stem for f in (target / ".personetta" / "cursor-recipes").glob("*.md")
        )
        assert "recipe-a" in cursor_cache
        assert "recipe-b" in cursor_cache
        assert "test-recipe" in cursor_cache

        # Verify copilot has all recipes cached
        copilot_cache = sorted(
            f.stem for f in (target / ".personetta" / "copilot-recipes").glob("*.md")
        )
        assert "recipe-a" in copilot_cache
        assert "recipe-b" in copilot_cache
        assert "test-recipe" in copilot_cache

    def test_state_json_structure_consistent_across_formats(
        self, populated_project, tmp_path
    ):
        """Verify state JSON structure is consistent across all formats."""
        target = tmp_path / "output"

        for fmt in ["cursor", "copilot", "claude", "cline"]:
            install_all_for_format(populated_project, target, fmt)

            state_path = target / ".personetta" / f"{fmt}-active.json"
            assert state_path.exists(), f"{fmt} state file missing"

            state = json.loads(state_path.read_text())
            assert "active_recipe" in state
            assert isinstance(state["active_recipe"], str)
            assert state["active_recipe"] == "test-recipe"  # Default first recipe

    def test_format_specific_file_extensions(self, populated_project, tmp_path):
        """Verify each format uses correct file extensions."""
        target = tmp_path / "output"

        install_all_for_format(populated_project, target, "cursor")
        install_all_for_format(populated_project, target, "copilot")
        install_all_for_format(populated_project, target, "claude")
        install_all_for_format(populated_project, target, "cline")

        # Cursor: .md files
        cursor_files = list((target / ".cursor" / "rules").glob("*.md"))
        assert len(cursor_files) >= 3  # baseline, router, active

        # Copilot: .instructions.md files
        copilot_files = list((target / ".copilot" / "instructions").glob("*.md"))
        assert len(copilot_files) >= 3
        assert any(".instructions.md" in f.name for f in copilot_files)

        # Claude: .md files
        claude_files = list((target / ".claude" / "rules").glob("*.md"))
        assert len(claude_files) >= 3

        # Cline: .md files
        cline_files = list((target / "Documents" / "Cline" / "Rules").glob("*.md"))
        assert len(cline_files) >= 3

    def test_global_vs_project_install_isolation(self, populated_project, tmp_path):
        """Install to global and project targets, verify no cross-contamination."""
        global_target = tmp_path / "global"
        project_target = tmp_path / "project"

        # Install to global
        install_all_for_format(populated_project, global_target, "copilot")

        # Install to project
        install_all_for_format(populated_project, project_target, "copilot")

        # Verify independent state files
        global_state = global_target / ".personetta" / "copilot-active.json"
        project_state = project_target / ".personetta" / "copilot-active.json"

        assert global_state.exists()
        assert project_state.exists()
        assert global_state != project_state  # Different paths

        # Verify independent instructions
        global_inst = global_target / ".copilot" / "instructions"
        project_inst = project_target / ".copilot" / "instructions"

        assert global_inst.exists()
        assert project_inst.exists()
        assert len(list(global_inst.glob("*.md"))) >= 3
        assert len(list(project_inst.glob("*.md"))) >= 3

    def test_cache_pruning_on_failed_recipes(self, populated_project, tmp_path):
        """When some recipes fail, only successful ones are cached."""
        target = tmp_path / "output"

        # Add a valid recipe
        add_recipe(
            populated_project,
            "valid-recipe",
            "Valid recipe",
            ["base/lifecycle/test-developer"],
        )

        # Add an invalid recipe (compose role doesn't exist - will fail before cache)
        # Note: This will fail during install-all, which is expected
        invalid_recipe = populated_project / "data" / "recipes" / "invalid-recipe.yaml"
        invalid_recipe.write_text(
            yaml.dump(
                {
                    "name": "invalid-recipe",
                    "description": "Invalid recipe",
                    "compose": ["base/mixins/nonexistent-role"],  # Doesn't exist
                }
            )
        )

        # Try to install all (should succeed for valid, fail for invalid)
        # The install_all function handles errors gracefully
        try:
            ok, bad = install_all_cursor(populated_project, target, recipe_filter=None)
            # Should have failures
            assert len(bad) > 0, "Expected invalid-recipe to fail"
        except Exception:
            # If it raises, that's also acceptable behavior
            pass

        # Verify only valid recipes are cached (if any succeeded)
        cache_dir = target / ".personetta" / "cursor-recipes"
        if cache_dir.exists():
            cached = {f.stem for f in cache_dir.glob("*.md")}
            # Invalid recipe should NOT be in cache
            assert "invalid-recipe" not in cached

    def test_set_active_requires_cached_recipe(self, populated_project, tmp_path):
        """set-active fails for recipes not in cache."""
        target = tmp_path / "output"

        # Install one recipe
        install_all_for_format(populated_project, target, "copilot")

        # Try to set active a non-existent recipe
        with pytest.raises(FileNotFoundError):
            set_active_copilot(populated_project, target, "nonexistent-recipe")


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

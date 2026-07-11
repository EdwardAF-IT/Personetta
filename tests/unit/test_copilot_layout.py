"""
Unit tests for generator/copilot_layout.py - GitHub Copilot layout strategy.

Tests CopilotLayout class and module-level functions for Copilot-specific
installation patterns, state management, and file cleanup.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from generator.copilot_layout import (
    CopilotLayout,
    write_copilot_state,
    read_copilot_state,
    set_active_copilot,
    install_single_copilot_recipe_to_cache,
    list_cached_copilot_recipes,
    ensure_copilot_baseline_router,
    copilot_recipe_cache_dir,
    copilot_state_path,
    copilot_instructions_dir,
    wrap_copilot_instructions,
)
from generator.constants import (
    COPILOT_STATE_FILE,
    COPILOT_BASELINE_STEM,
    COPILOT_ROUTER_STEM,
    COPILOT_ACTIVE_STEM,
    COPILOT_INSTRUCTIONS_SUFFIX,
)


@pytest.fixture
def copilot_layout():
    """Create CopilotLayout instance."""
    return CopilotLayout()


@pytest.fixture
def sample_recipe():
    """Sample recipe metadata."""
    return {
        "name": "test-recipe",
        "description": "Test recipe for unit tests",
    }


class TestCopilotLayout:
    """Test CopilotLayout class methods."""

    def test_format_name(self, copilot_layout):
        """CopilotLayout.format_name returns 'copilot'."""
        assert copilot_layout.format_name == "copilot"

    def test_recipes_subdir(self, copilot_layout):
        """CopilotLayout.recipes_subdir returns 'copilot-recipes'."""
        assert copilot_layout.recipes_subdir == "copilot-recipes"

    def test_rules_dir(self, copilot_layout, tmp_path):
        """CopilotLayout.rules_dir returns .copilot/instructions."""
        result = copilot_layout.rules_dir(tmp_path)
        assert result == tmp_path / ".copilot" / "instructions"

    def test_state_file(self, copilot_layout):
        """CopilotLayout.state_file returns copilot-active.json."""
        assert copilot_layout.state_file == COPILOT_STATE_FILE

    def test_wrap_output(self, copilot_layout, sample_recipe):
        """CopilotLayout.wrap_output adds frontmatter with name and description."""
        content = "# Recipe content\n\nSome text"

        result = copilot_layout.wrap_output(content, sample_recipe)

        assert result.startswith("---\n")
        assert "name: 'test-recipe'" in result
        assert "description: 'Test recipe for unit tests'" in result
        assert "applyTo: '**'" in result
        assert "---\n\n" in result
        assert "# Recipe content" in result

    def test_wrap_output_escapes_single_quotes(self, copilot_layout):
        """CopilotLayout.wrap_output escapes single quotes in description."""
        recipe = {
            "name": "test",
            "description": "It's a test with 'quotes'",
        }

        result = copilot_layout.wrap_output("content", recipe)

        assert "description: 'It''s a test with ''quotes'''" in result

    def test_wrap_output_strips_leading_newlines(self, copilot_layout, sample_recipe):
        """CopilotLayout.wrap_output strips leading newlines from content."""
        content = "\n\n\n# Recipe content"

        result = copilot_layout.wrap_output(content, sample_recipe)

        # Should have frontmatter, then content without extra newlines
        lines = result.split("\n")
        assert lines[0] == "---"
        # Find where content starts (after closing ---)
        content_start = None
        for i, line in enumerate(lines):
            if i > 0 and line == "---":
                content_start = i + 1
                break
        assert lines[content_start] == ""  # One newline after ---
        assert lines[content_start + 1] == "# Recipe content"

    def test_cleanup_on_zero_successes_removes_all_files(self, copilot_layout, tmp_path):
        """CopilotLayout.cleanup_on_zero_successes removes baseline, router, active, cache, and state files."""
        # Create directory structure
        inst_dir = tmp_path / ".copilot" / "instructions"
        inst_dir.mkdir(parents=True)
        cache_dir = tmp_path / ".personetta" / "copilot-recipes"
        cache_dir.mkdir(parents=True)

        # Create files
        baseline = inst_dir / (COPILOT_BASELINE_STEM + COPILOT_INSTRUCTIONS_SUFFIX)
        router = inst_dir / (COPILOT_ROUTER_STEM + COPILOT_INSTRUCTIONS_SUFFIX)
        active = inst_dir / (COPILOT_ACTIVE_STEM + COPILOT_INSTRUCTIONS_SUFFIX)
        state = tmp_path / ".personetta" / COPILOT_STATE_FILE
        cache_file = cache_dir / "recipe.md"

        baseline.write_text("baseline content")
        router.write_text("router content")
        active.write_text("active content")
        state.write_text('{"active_recipe": "test"}')
        cache_file.write_text("cached recipe")

        # Run cleanup
        copilot_layout.cleanup_on_zero_successes(tmp_path)

        # Verify all files removed
        assert not baseline.exists()
        assert not router.exists()
        assert not active.exists()
        assert not state.exists()
        assert not cache_file.exists()

    def test_cleanup_on_zero_successes_removes_empty_instructions_dir(
        self, copilot_layout, tmp_path
    ):
        """CopilotLayout.cleanup_on_zero_successes removes empty instructions directory."""
        inst_dir = tmp_path / ".copilot" / "instructions"
        inst_dir.mkdir(parents=True)

        # Create only instruction files (no other files in directory)
        baseline = inst_dir / (COPILOT_BASELINE_STEM + COPILOT_INSTRUCTIONS_SUFFIX)
        baseline.write_text("content")

        copilot_layout.cleanup_on_zero_successes(tmp_path)

        # Directory should be removed since it's now empty
        assert not inst_dir.exists()

    def test_cleanup_on_zero_successes_keeps_non_empty_instructions_dir(
        self, copilot_layout, tmp_path
    ):
        """CopilotLayout.cleanup_on_zero_successes preserves non-empty instructions directory."""
        inst_dir = tmp_path / ".copilot" / "instructions"
        inst_dir.mkdir(parents=True)

        # Create instruction files AND an extra file
        baseline = inst_dir / (COPILOT_BASELINE_STEM + COPILOT_INSTRUCTIONS_SUFFIX)
        other_file = inst_dir / "user-custom.instructions.md"
        baseline.write_text("content")
        other_file.write_text("user content")

        copilot_layout.cleanup_on_zero_successes(tmp_path)

        # Directory should remain because of other_file
        assert inst_dir.exists()
        assert not baseline.exists()
        assert other_file.exists()

    def test_cleanup_on_zero_successes_handles_missing_files(
        self, copilot_layout, tmp_path
    ):
        """CopilotLayout.cleanup_on_zero_successes handles missing files gracefully."""
        # Don't create any files - should not raise error
        copilot_layout.cleanup_on_zero_successes(tmp_path)

        # Should complete without error
        assert True

    @patch("generator.copilot_layout.load_recipe")
    def test_write_active_from_cache(self, mock_load_recipe, copilot_layout, tmp_path):
        """CopilotLayout._write_active_from_cache writes active file from cache."""
        # Setup
        cache_dir = tmp_path / ".personetta" / "copilot-recipes"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "test-recipe.md"
        cache_file.write_text("# Cached recipe content")

        mock_load_recipe.return_value = {
            "name": "test-recipe",
            "description": "Test description for active file",
        }

        # Execute
        result = copilot_layout._write_active_from_cache(
            tmp_path, "test-recipe", tmp_path
        )

        # Verify
        assert result.exists()
        assert result.name == COPILOT_ACTIVE_STEM + COPILOT_INSTRUCTIONS_SUFFIX
        content = result.read_text()
        assert "# Cached recipe content" in content
        assert "name: 'Personetta - active persona (test-recipe)'" in content
        assert "description: 'Test description for active file'" in content

    @patch("generator.copilot_layout.load_recipe")
    def test_write_active_from_cache_truncates_long_description(
        self, mock_load_recipe, copilot_layout, tmp_path
    ):
        """CopilotLayout._write_active_from_cache truncates description to 200 chars."""
        cache_dir = tmp_path / ".personetta" / "copilot-recipes"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "test-recipe.md"
        cache_file.write_text("content")

        long_desc = "x" * 300  # 300 character description
        mock_load_recipe.return_value = {
            "name": "test-recipe",
            "description": long_desc,
        }

        result = copilot_layout._write_active_from_cache(
            tmp_path, "test-recipe", tmp_path
        )

        content = result.read_text()
        # Should be truncated to 200 chars
        assert "description: '" + ("x" * 200) + "'" in content
        assert "description: '" + long_desc + "'" not in content

    @patch("generator.copilot_layout.load_recipe")
    def test_write_active_from_cache_creates_instructions_dir(
        self, mock_load_recipe, copilot_layout, tmp_path
    ):
        """CopilotLayout._write_active_from_cache creates instructions directory if missing."""
        cache_dir = tmp_path / ".personetta" / "copilot-recipes"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "test-recipe.md"
        cache_file.write_text("content")

        mock_load_recipe.return_value = {"name": "test", "description": "test"}

        # Instructions dir doesn't exist yet
        inst_dir = tmp_path / ".copilot" / "instructions"
        assert not inst_dir.exists()

        copilot_layout._write_active_from_cache(tmp_path, "test-recipe", tmp_path)

        # Should be created
        assert inst_dir.exists()

    @patch("generator.copilot_layout.load_recipe")
    @patch("generator.copilot_layout.list_recipes")
    @patch("generator.copilot_layout.collect_recipe_router_rows")
    @patch("generator.copilot_layout.format_router_for_plain")
    @patch("generator.copilot_layout.format_baseline_for_plain")
    @patch("generator.copilot_layout.load_system_role")
    def test_write_baseline_router_active(
        self,
        mock_load_system_role,
        mock_format_baseline,
        mock_format_router,
        mock_collect_rows,
        mock_list_recipes,
        mock_load_recipe,
        copilot_layout,
        tmp_path,
    ):
        """CopilotLayout.write_baseline_router_active writes all three files."""
        # Setup mocks
        mock_load_system_role.side_effect = [
            {"name": "baseline"},  # baseline role
            {"name": "router"},  # router role
        ]
        mock_collect_rows.return_value = [
            {"name": "recipe-a", "description": "A"},
            {"name": "recipe-b", "description": "B"},
        ]
        mock_format_router.return_value = "# Router content"
        mock_format_baseline.return_value = "# Baseline content"
        mock_list_recipes.return_value = [
            {"name": "recipe-a", "description": "Recipe A description"},
            {"name": "recipe-b", "description": "Recipe B description"},
        ]
        mock_load_recipe.return_value = {
            "name": "recipe-a",
            "description": "Recipe A description",
        }

        # Create cache with recipe files
        cache_dir = tmp_path / ".personetta" / "copilot-recipes"
        cache_dir.mkdir(parents=True)
        (cache_dir / "recipe-a.md").write_text("# Recipe A content")
        (cache_dir / "recipe-b.md").write_text("# Recipe B content")

        # Execute
        copilot_layout.write_baseline_router_active(
            tmp_path,
            ["recipe-b", "recipe-a"],  # Unsorted input
            tmp_path,
        )

        # Verify all three files created
        inst_dir = tmp_path / ".copilot" / "instructions"
        assert inst_dir.exists()

        router = inst_dir / (COPILOT_ROUTER_STEM + COPILOT_INSTRUCTIONS_SUFFIX)
        baseline = inst_dir / (COPILOT_BASELINE_STEM + COPILOT_INSTRUCTIONS_SUFFIX)
        active = inst_dir / (COPILOT_ACTIVE_STEM + COPILOT_INSTRUCTIONS_SUFFIX)

        assert router.exists()
        assert baseline.exists()
        assert active.exists()

        # Verify router content
        router_content = router.read_text()
        assert "# Router content" in router_content
        assert "name: 'Personetta - recipe router'" in router_content

        # Verify baseline content
        baseline_content = baseline.read_text()
        assert "# Baseline content" in baseline_content
        assert "name: 'Personetta - baseline'" in baseline_content

        # Verify active content (should use first recipe alphabetically = recipe-a)
        active_content = active.read_text()
        assert "# Recipe A content" in active_content
        assert "name: 'Personetta - active persona (recipe-a)'" in active_content

        # Verify state file created with first recipe alphabetically
        state_path = tmp_path / ".personetta" / COPILOT_STATE_FILE
        assert state_path.exists()
        state = json.loads(state_path.read_text())
        assert state["active_recipe"] == "recipe-a"


class TestModuleLevelFunctions:
    """Test module-level public API functions."""

    def test_personetta_root(self, tmp_path):
        """personetta_root returns .personetta directory."""
        from generator.copilot_layout import personetta_root

        result = personetta_root(tmp_path)
        assert result == tmp_path / ".personetta"

    def test_copilot_recipe_cache_dir(self, tmp_path):
        """copilot_recipe_cache_dir returns correct path."""
        result = copilot_recipe_cache_dir(tmp_path)
        assert result == tmp_path / ".personetta" / "copilot-recipes"

    def test_copilot_state_path(self, tmp_path):
        """copilot_state_path returns correct path."""
        result = copilot_state_path(tmp_path)
        assert result == tmp_path / ".personetta" / COPILOT_STATE_FILE

    def test_copilot_instructions_dir(self, tmp_path):
        """copilot_instructions_dir returns correct path."""
        result = copilot_instructions_dir(tmp_path)
        assert result == tmp_path / ".copilot" / "instructions"

    def test_wrap_copilot_instructions(self):
        """wrap_copilot_instructions wraps content with frontmatter."""
        result = wrap_copilot_instructions("Test Name", "Test Description", "# Content")

        assert "---\n" in result
        assert "name: 'Test Name'" in result
        assert "description: 'Test Description'" in result
        assert "applyTo: '**'" in result
        assert "# Content" in result

    def test_wrap_copilot_instructions_custom_apply_to(self):
        """wrap_copilot_instructions accepts custom applyTo but always uses **."""
        # Note: apply_to parameter is accepted but not used (legacy function)
        result = wrap_copilot_instructions("Test", "Desc", "content", apply_to="*.py")

        # Function still uses ** (not the custom apply_to)
        assert "applyTo: '**'" in result

    def test_write_copilot_state(self, tmp_path):
        """write_copilot_state writes JSON state file."""
        write_copilot_state(tmp_path, "test-recipe")

        state_path = tmp_path / ".personetta" / COPILOT_STATE_FILE
        assert state_path.exists()

        data = json.loads(state_path.read_text())
        assert data["active_recipe"] == "test-recipe"
        assert data["format"] == "copilot"

    def test_read_copilot_state(self, tmp_path):
        """read_copilot_state reads JSON state file."""
        state_path = tmp_path / ".personetta" / COPILOT_STATE_FILE
        state_path.parent.mkdir(parents=True)
        state_path.write_text('{"active_recipe": "my-recipe", "format": "copilot"}')

        result = read_copilot_state(tmp_path)

        assert result is not None
        assert result["active_recipe"] == "my-recipe"
        assert result["format"] == "copilot"

    def test_read_copilot_state_missing_file(self, tmp_path):
        """read_copilot_state returns None when file doesn't exist."""
        result = read_copilot_state(tmp_path)
        assert result is None

    def test_read_copilot_state_invalid_json(self, tmp_path):
        """read_copilot_state returns None for invalid JSON."""
        state_path = tmp_path / ".personetta" / COPILOT_STATE_FILE
        state_path.parent.mkdir(parents=True)
        state_path.write_text("not valid json {{{")

        result = read_copilot_state(tmp_path)
        assert result is None

    @patch("generator.copilot_layout._copilot_layout._write_active_from_cache")
    @patch("generator.copilot_layout._copilot_layout.write_state")
    def test_set_active_copilot_success(
        self, mock_write_state, mock_write_active, tmp_path
    ):
        """set_active_copilot sets active recipe when cache exists."""
        # Create cache file
        cache_dir = tmp_path / ".personetta" / "copilot-recipes"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "test-recipe.md"
        cache_file.write_text("cached content")

        mock_write_active.return_value = (
            tmp_path / ".copilot" / "instructions" / "personetta-active.instructions.md"
        )

        result = set_active_copilot(tmp_path, tmp_path, "test-recipe")

        mock_write_active.assert_called_once_with(tmp_path, "test-recipe", tmp_path)
        mock_write_state.assert_called_once_with(tmp_path, "test-recipe")
        assert result == mock_write_active.return_value

    def test_set_active_copilot_missing_cache(self, tmp_path):
        """set_active_copilot raises FileNotFoundError when cache doesn't exist."""
        with pytest.raises(FileNotFoundError) as exc_info:
            set_active_copilot(tmp_path, tmp_path, "missing-recipe")

        error_msg = str(exc_info.value)
        assert "No cached Copilot recipe 'missing-recipe'" in error_msg
        assert "personetta install '*' --format copilot" in error_msg

    def test_list_cached_copilot_recipes(self, tmp_path):
        """list_cached_copilot_recipes returns sorted recipe names."""
        cache_dir = tmp_path / ".personetta" / "copilot-recipes"
        cache_dir.mkdir(parents=True)

        (cache_dir / "recipe-c.md").write_text("c")
        (cache_dir / "recipe-a.md").write_text("a")
        (cache_dir / "recipe-b.md").write_text("b")

        result = list_cached_copilot_recipes(tmp_path)

        assert result == ["recipe-a", "recipe-b", "recipe-c"]

    def test_list_cached_copilot_recipes_empty(self, tmp_path):
        """list_cached_copilot_recipes returns empty list when cache doesn't exist."""
        result = list_cached_copilot_recipes(tmp_path)
        assert result == []

    @patch("generator.copilot_layout.build_plain_baseline_markdown")
    @patch("generator.copilot_layout.build_plain_router_markdown")
    @patch("generator.copilot_layout.collect_recipe_router_rows")
    def test_ensure_copilot_baseline_router_when_baseline_exists(
        self, mock_collect, mock_build_router, mock_build_baseline, tmp_path
    ):
        """ensure_copilot_baseline_router does nothing when baseline exists."""
        inst_dir = tmp_path / ".copilot" / "instructions"
        inst_dir.mkdir(parents=True)
        baseline = inst_dir / (COPILOT_BASELINE_STEM + COPILOT_INSTRUCTIONS_SUFFIX)
        baseline.write_text("existing baseline")

        ensure_copilot_baseline_router(tmp_path, tmp_path)

        # Should not create anything new
        mock_collect.assert_not_called()
        mock_build_router.assert_not_called()
        mock_build_baseline.assert_not_called()

    @patch("generator.copilot_layout.build_plain_baseline_markdown")
    @patch("generator.copilot_layout.build_plain_router_markdown")
    @patch("generator.copilot_layout.collect_recipe_router_rows")
    def test_ensure_copilot_baseline_router_when_cache_empty(
        self, mock_collect, mock_build_router, mock_build_baseline, tmp_path
    ):
        """ensure_copilot_baseline_router does nothing when cache is empty."""
        ensure_copilot_baseline_router(tmp_path, tmp_path)

        # Should not create files if no cached recipes
        mock_collect.assert_not_called()

    @patch("generator.copilot_layout.build_plain_baseline_markdown")
    @patch("generator.copilot_layout.build_plain_router_markdown")
    @patch("generator.copilot_layout.collect_recipe_router_rows")
    def test_ensure_copilot_baseline_router_creates_files(
        self, mock_collect, mock_build_router, mock_build_baseline, tmp_path
    ):
        """ensure_copilot_baseline_router creates baseline and router when needed."""
        # Create cache with recipes
        cache_dir = tmp_path / ".personetta" / "copilot-recipes"
        cache_dir.mkdir(parents=True)
        (cache_dir / "recipe-a.md").write_text("a")
        (cache_dir / "recipe-b.md").write_text("b")

        mock_collect.return_value = [
            {"name": "recipe-a", "description": "A"},
            {"name": "recipe-b", "description": "B"},
        ]
        mock_build_router.return_value = "# Router content"
        mock_build_baseline.return_value = "# Baseline content"

        ensure_copilot_baseline_router(tmp_path, tmp_path)

        # Should create both files
        inst_dir = tmp_path / ".copilot" / "instructions"
        router = inst_dir / (COPILOT_ROUTER_STEM + COPILOT_INSTRUCTIONS_SUFFIX)
        baseline = inst_dir / (COPILOT_BASELINE_STEM + COPILOT_INSTRUCTIONS_SUFFIX)

        assert router.exists()
        assert baseline.exists()
        assert "# Router content" in router.read_text()
        assert "# Baseline content" in baseline.read_text()

        # Verify correct arguments passed
        mock_collect.assert_called_once_with(tmp_path, ["recipe-a", "recipe-b"])
        mock_build_router.assert_called_once()
        mock_build_baseline.assert_called_once()

    @patch("generator.copilot_layout._copilot_layout.read_state")
    @patch("generator.copilot_layout._copilot_layout._write_active_from_cache")
    @patch("generator.copilot_layout._copilot_layout.install_single_recipe_to_cache")
    @patch("generator.copilot_layout.ensure_copilot_baseline_router")
    def test_install_single_copilot_recipe_to_cache(
        self, mock_ensure, mock_install, mock_write_active, mock_read_state, tmp_path
    ):
        """install_single_copilot_recipe_to_cache installs recipe and refreshes active if needed."""
        # Setup: recipe is the active one
        mock_read_state.return_value = {
            "active_recipe": "test-recipe",
            "format": "copilot",
        }
        mock_install.return_value = (
            tmp_path / ".personetta" / "copilot-recipes" / "test-recipe.md"
        )

        result = install_single_copilot_recipe_to_cache(tmp_path, tmp_path, "test-recipe")

        # Should ensure baseline exists
        mock_ensure.assert_called_once_with(tmp_path, tmp_path)

        # Should install to cache
        mock_install.assert_called_once_with("test-recipe", tmp_path, tmp_path)

        # Should refresh active file since recipe is active
        mock_write_active.assert_called_once_with(tmp_path, "test-recipe", tmp_path)

        assert result == tmp_path / ".personetta" / "copilot-recipes" / "test-recipe.md"

    @patch("generator.copilot_layout._copilot_layout.read_state")
    @patch("generator.copilot_layout._copilot_layout._write_active_from_cache")
    @patch("generator.copilot_layout._copilot_layout.install_single_recipe_to_cache")
    @patch("generator.copilot_layout.ensure_copilot_baseline_router")
    def test_install_single_copilot_recipe_to_cache_not_active(
        self, mock_ensure, mock_install, mock_write_active, mock_read_state, tmp_path
    ):
        """install_single_copilot_recipe_to_cache doesn't refresh active if recipe not active."""
        # Setup: different recipe is active
        mock_read_state.return_value = {
            "active_recipe": "other-recipe",
            "format": "copilot",
        }
        mock_install.return_value = (
            tmp_path / ".personetta" / "copilot-recipes" / "test-recipe.md"
        )

        install_single_copilot_recipe_to_cache(tmp_path, tmp_path, "test-recipe")

        # Should NOT refresh active file
        mock_write_active.assert_not_called()

    @patch("generator.copilot_layout._copilot_layout.read_state")
    @patch("generator.copilot_layout._copilot_layout._write_active_from_cache")
    @patch("generator.copilot_layout._copilot_layout.install_single_recipe_to_cache")
    @patch("generator.copilot_layout.ensure_copilot_baseline_router")
    def test_install_single_copilot_recipe_to_cache_no_state(
        self, mock_ensure, mock_install, mock_write_active, mock_read_state, tmp_path
    ):
        """install_single_copilot_recipe_to_cache handles missing state file."""
        # Setup: no state file
        mock_read_state.return_value = None
        mock_install.return_value = (
            tmp_path / ".personetta" / "copilot-recipes" / "test-recipe.md"
        )

        install_single_copilot_recipe_to_cache(tmp_path, tmp_path, "test-recipe")

        # Should NOT refresh active file when state is missing
        mock_write_active.assert_not_called()

    def test_cleanup_copilot_on_zero_successes(self, tmp_path):
        """_cleanup_copilot_on_zero_successes delegates to layout cleanup method."""
        from generator.copilot_layout import _cleanup_copilot_on_zero_successes

        # Create files to be cleaned up
        inst_dir = tmp_path / ".copilot" / "instructions"
        inst_dir.mkdir(parents=True)
        baseline = inst_dir / (COPILOT_BASELINE_STEM + COPILOT_INSTRUCTIONS_SUFFIX)
        baseline.write_text("test")

        _cleanup_copilot_on_zero_successes(tmp_path)

        # Verify cleanup happened
        assert not baseline.exists()

    @patch("generator.copilot_layout._copilot_layout.install_all")
    def test_install_all_copilot_with_filter(self, mock_install_all, tmp_path):
        """install_all_copilot delegates to layout install_all with filter."""
        from generator.copilot_layout import install_all_copilot

        mock_install_all.return_value = (["recipe-a"], [])

        result = install_all_copilot(tmp_path, tmp_path, recipe_filter="test")

        mock_install_all.assert_called_once_with(
            tmp_path, tmp_path, recipe_filter="test", recipe_list=None
        )
        assert result == (["recipe-a"], [])

    @patch("generator.copilot_layout._copilot_layout.install_all")
    def test_install_all_copilot_with_list(self, mock_install_all, tmp_path):
        """install_all_copilot delegates to layout install_all with recipe list."""
        from generator.copilot_layout import install_all_copilot

        mock_install_all.return_value = (["recipe-a", "recipe-b"], [])

        result = install_all_copilot(
            tmp_path, tmp_path, recipe_list=["recipe-a", "recipe-b"]
        )

        mock_install_all.assert_called_once_with(
            tmp_path, tmp_path, recipe_filter=None, recipe_list=["recipe-a", "recipe-b"]
        )
        assert result == (["recipe-a", "recipe-b"], [])

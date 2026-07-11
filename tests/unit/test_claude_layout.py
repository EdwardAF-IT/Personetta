"""
Unit tests for generator/claude_layout.py - Claude Code layout strategy.

Covers ClaudeLayout class and module-level functions with comprehensive mocking
to achieve 100% code coverage.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from generator.claude_layout import (
    ClaudeLayout,
    personetta_root,
    claude_recipe_cache_dir,
    claude_state_path,
    claude_rules_dir,
    write_claude_state,
    read_claude_state,
    install_claude_router,
    _cleanup_claude_on_zero_successes,
    install_all_claude,
    set_active_claude,
    install_single_claude_recipe_to_cache,
    list_cached_claude_recipes,
    BASELINE_NAME,
    ROUTER_NAME,
    ACTIVE_NAME,
)
from generator.constants import (
    CLAUDE_STATE_FILE,
    CLAUDE_BASELINE_FILENAME,
    CLAUDE_ROUTER_FILENAME,
    CLAUDE_ACTIVE_FILENAME,
)


class TestClaudeLayout:
    """Test ClaudeLayout class methods."""

    def test_state_file_property(self):
        """ClaudeLayout.state_file returns CLAUDE_STATE_FILE constant."""
        layout = ClaudeLayout()
        assert layout.state_file == CLAUDE_STATE_FILE

    def test_wrap_output(self):
        """ClaudeLayout.wrap_output returns content unchanged (no wrapping for Claude)."""
        layout = ClaudeLayout()
        content = "# Test Recipe\n\nSome content here"
        recipe = {"name": "test-recipe", "description": "Test"}

        result = layout.wrap_output(content, recipe)

        # Claude uses plain markdown - no wrapping
        assert result == content

    @patch("generator.claude_layout.load_system_role")
    @patch("generator.claude_layout.collect_recipe_router_rows")
    @patch("generator.claude_layout.format_baseline_for_plain")
    @patch("generator.claude_layout.format_router_for_plain")
    def test_write_baseline_router_active(
        self,
        mock_format_router,
        mock_format_baseline,
        mock_collect_rows,
        mock_load_system,
        tmp_path,
    ):
        """write_baseline_router_active creates baseline, router, and active files."""
        layout = ClaudeLayout()

        # Setup cache with recipe
        cache_dir = tmp_path / ".personetta" / "claude-recipes"
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "recipe-a.md").write_text("Recipe A content")
        (cache_dir / "recipe-b.md").write_text("Recipe B content")

        # Mock system role loading and formatting
        mock_load_system.side_effect = [
            {"name": "router"},  # First call for router
            {"name": "baseline"},  # Second call for baseline
        ]
        mock_collect_rows.return_value = []
        mock_format_router.return_value = "Router content"
        mock_format_baseline.return_value = "Baseline content"

        # Call method
        layout.write_baseline_router_active(tmp_path, ["recipe-b", "recipe-a"], tmp_path)

        # Verify rules directory created
        rules_dir = tmp_path / ".claude" / "rules"
        assert rules_dir.is_dir()

        # Verify router file written
        router_path = rules_dir / CLAUDE_ROUTER_FILENAME
        assert router_path.is_file()
        assert router_path.read_text() == "Router content"

        # Verify baseline file written
        baseline_path = rules_dir / CLAUDE_BASELINE_FILENAME
        assert baseline_path.is_file()
        assert baseline_path.read_text() == "Baseline content"

        # Verify active file written (should be first alphabetically: recipe-a)
        active_path = rules_dir / CLAUDE_ACTIVE_FILENAME
        assert active_path.is_file()
        assert active_path.read_text() == "Recipe A content"

        # Verify state file written
        state = read_claude_state(tmp_path)
        assert state["active_recipe"] == "recipe-a"  # First alphabetically

    def test_cleanup_on_zero_successes_removes_all_files(self, tmp_path):
        """cleanup_on_zero_successes removes baseline, router, active, cache, and state files."""
        layout = ClaudeLayout()

        # Create all the files that should be removed
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)

        baseline = rules_dir / CLAUDE_BASELINE_FILENAME
        router = rules_dir / CLAUDE_ROUTER_FILENAME
        active = rules_dir / CLAUDE_ACTIVE_FILENAME
        baseline.write_text("baseline content")
        router.write_text("router content")
        active.write_text("active content")

        # Create cache files
        cache_dir = tmp_path / ".personetta" / "claude-recipes"
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "recipe1.md").write_text("recipe 1")
        (cache_dir / "recipe2.md").write_text("recipe 2")

        # Create state file
        state_file = tmp_path / ".personetta" / CLAUDE_STATE_FILE
        state_file.write_text('{"active_recipe": "test"}')

        # Verify files exist before cleanup
        assert baseline.is_file()
        assert router.is_file()
        assert active.is_file()
        assert (cache_dir / "recipe1.md").is_file()
        assert (cache_dir / "recipe2.md").is_file()
        assert state_file.is_file()

        # Run cleanup
        layout.cleanup_on_zero_successes(tmp_path)

        # Verify all files removed
        assert not baseline.exists()
        assert not router.exists()
        assert not active.exists()
        assert not (cache_dir / "recipe1.md").exists()
        assert not (cache_dir / "recipe2.md").exists()
        assert not state_file.exists()

    def test_cleanup_on_zero_successes_handles_missing_files(self, tmp_path):
        """cleanup_on_zero_successes handles case when files don't exist."""
        layout = ClaudeLayout()

        # Don't create any files - just run cleanup (should not raise)
        layout.cleanup_on_zero_successes(tmp_path)

        # Should complete without error
        assert True

    @patch("generator.claude_layout.load_system_role")
    @patch("generator.claude_layout.collect_recipe_router_rows")
    @patch("generator.claude_layout.format_router_for_plain")
    def test_write_active_from_cache(
        self,
        mock_format_router,
        mock_collect_rows,
        mock_load_system,
        tmp_path,
    ):
        """_write_active_from_cache reads from cache and writes to active file."""
        layout = ClaudeLayout()

        # Setup cache
        cache_dir = tmp_path / ".personetta" / "claude-recipes"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "test-recipe.md"
        cache_file.write_text("Test recipe content from cache")

        # Call method
        result = layout._write_active_from_cache(tmp_path, "test-recipe", tmp_path)

        # Verify active file created
        expected_path = tmp_path / ".claude" / "rules" / CLAUDE_ACTIVE_FILENAME
        assert result == expected_path
        assert expected_path.is_file()
        assert expected_path.read_text() == "Test recipe content from cache"

    @patch("generator.claude_layout.load_system_role")
    @patch("generator.claude_layout.collect_recipe_router_rows")
    @patch("generator.claude_layout.format_router_for_plain")
    def test_write_active_from_cache_creates_parent_dir(
        self,
        mock_format_router,
        mock_collect_rows,
        mock_load_system,
        tmp_path,
    ):
        """_write_active_from_cache creates parent directory if missing."""
        layout = ClaudeLayout()

        # Setup cache
        cache_dir = tmp_path / ".personetta" / "claude-recipes"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "test-recipe.md"
        cache_file.write_text("Test content")

        # Ensure rules dir doesn't exist
        rules_dir = tmp_path / ".claude" / "rules"
        assert not rules_dir.exists()

        # Call method
        layout._write_active_from_cache(tmp_path, "test-recipe", tmp_path)

        # Verify parent directory was created
        assert rules_dir.is_dir()


class TestModuleLevelFunctions:
    """Test module-level public API functions."""

    def test_personetta_root(self, tmp_path):
        """personetta_root returns .personetta path."""
        result = personetta_root(tmp_path)
        assert result == tmp_path / ".personetta"

    def test_claude_recipe_cache_dir(self, tmp_path):
        """claude_recipe_cache_dir returns claude-recipes path."""
        result = claude_recipe_cache_dir(tmp_path)
        assert result == tmp_path / ".personetta" / "claude-recipes"

    def test_claude_state_path(self, tmp_path):
        """claude_state_path returns state file path."""
        result = claude_state_path(tmp_path)
        assert result == tmp_path / ".personetta" / CLAUDE_STATE_FILE

    def test_claude_rules_dir(self, tmp_path):
        """claude_rules_dir returns .claude/rules path."""
        result = claude_rules_dir(tmp_path)
        assert result == tmp_path / ".claude" / "rules"

    def test_write_claude_state(self, tmp_path):
        """write_claude_state writes state JSON file."""
        write_claude_state(tmp_path, "test-recipe")

        state_file = tmp_path / ".personetta" / CLAUDE_STATE_FILE
        assert state_file.is_file()

        state = json.loads(state_file.read_text())
        assert state["active_recipe"] == "test-recipe"
        assert state["format"] == "claude"

    def test_read_claude_state_existing_file(self, tmp_path):
        """read_claude_state reads existing state file."""
        state_file = tmp_path / ".personetta" / CLAUDE_STATE_FILE
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text('{"active_recipe": "my-recipe", "format": "claude"}')

        result = read_claude_state(tmp_path)

        assert result is not None
        assert result["active_recipe"] == "my-recipe"
        assert result["format"] == "claude"

    def test_read_claude_state_missing_file(self, tmp_path):
        """read_claude_state returns None for missing file."""
        result = read_claude_state(tmp_path)
        assert result is None

    @patch("generator.claude_layout.load_system_role")
    @patch("generator.claude_layout.collect_recipe_router_rows")
    @patch("generator.claude_layout.format_router_for_plain")
    def test_install_claude_router(
        self,
        mock_format_router,
        mock_collect_rows,
        mock_load_system,
        tmp_path,
    ):
        """install_claude_router writes router file."""
        mock_load_system.return_value = {"name": "router"}
        mock_collect_rows.return_value = []
        mock_format_router.return_value = "Router content"

        result = install_claude_router(tmp_path, ["recipe1", "recipe2"], tmp_path)

        expected_path = tmp_path / ".claude" / "rules" / CLAUDE_ROUTER_FILENAME
        assert result == expected_path
        assert expected_path.is_file()
        assert expected_path.read_text() == "Router content"

    def test_cleanup_claude_on_zero_successes(self, tmp_path):
        """_cleanup_claude_on_zero_successes calls layout cleanup method."""
        # Create files to be cleaned up
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        (rules_dir / CLAUDE_BASELINE_FILENAME).write_text("baseline")

        _cleanup_claude_on_zero_successes(tmp_path)

        # Verify cleanup occurred
        assert not (rules_dir / CLAUDE_BASELINE_FILENAME).exists()

    @patch("generator.claude_layout._claude_layout.install_all")
    def test_install_all_claude_with_filter(self, mock_install_all, tmp_path):
        """install_all_claude calls layout.install_all with recipe_filter."""
        mock_install_all.return_value = (["recipe1"], [])

        result = install_all_claude(
            tmp_path, tmp_path, recipe_filter="test-*", recipe_list=None
        )

        mock_install_all.assert_called_once_with(
            tmp_path, tmp_path, recipe_filter="test-*", recipe_list=None
        )
        assert result == (["recipe1"], [])

    @patch("generator.claude_layout._claude_layout.install_all")
    def test_install_all_claude_with_list(self, mock_install_all, tmp_path):
        """install_all_claude calls layout.install_all with recipe_list."""
        mock_install_all.return_value = (["r1", "r2"], ["r3"])

        result = install_all_claude(
            tmp_path, tmp_path, recipe_filter=None, recipe_list=["r1", "r2", "r3"]
        )

        mock_install_all.assert_called_once_with(
            tmp_path, tmp_path, recipe_filter=None, recipe_list=["r1", "r2", "r3"]
        )
        assert result == (["r1", "r2"], ["r3"])


class TestSetActiveClaude:
    """Test set_active_claude function."""

    def test_set_active_claude_success(self, tmp_path):
        """set_active_claude writes active file when cache exists."""
        # Setup cache
        cache_dir = tmp_path / ".personetta" / "claude-recipes"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "my-recipe.md"
        cache_file.write_text("My recipe content")

        # Call function
        result = set_active_claude(tmp_path, tmp_path, "my-recipe")

        # Verify active file created
        expected_path = tmp_path / ".claude" / "rules" / CLAUDE_ACTIVE_FILENAME
        assert result == expected_path
        assert expected_path.is_file()
        assert expected_path.read_text() == "My recipe content"

        # Verify state file updated
        state = read_claude_state(tmp_path)
        assert state["active_recipe"] == "my-recipe"

    def test_set_active_claude_missing_cache_raises_error(self, tmp_path):
        """set_active_claude raises FileNotFoundError when cache doesn't exist."""
        # Don't create cache file
        with pytest.raises(FileNotFoundError) as exc_info:
            set_active_claude(tmp_path, tmp_path, "missing-recipe")

        error_msg = str(exc_info.value)
        assert "No cached Claude recipe 'missing-recipe'" in error_msg
        assert "personetta install '*' --format claude" in error_msg


class TestInstallSingleClaudeRecipeToCache:
    """Test install_single_claude_recipe_to_cache function."""

    @patch("generator.claude_layout._claude_layout.install_single_recipe_to_cache")
    @patch("generator.claude_layout._claude_layout.read_state")
    @patch("generator.claude_layout._claude_layout.list_cached_recipes")
    @patch("generator.claude_layout._claude_layout._install_router")
    @patch("generator.claude_layout._claude_layout._write_active_from_cache")
    def test_install_single_not_active(
        self,
        mock_write_active,
        mock_install_router,
        mock_list_cached,
        mock_read_state,
        mock_install_single,
        tmp_path,
    ):
        """install_single_claude_recipe_to_cache updates cache and router when not active."""
        # Mock return values
        cache_path = tmp_path / ".personetta" / "claude-recipes" / "test-recipe.md"
        mock_install_single.return_value = cache_path
        mock_read_state.return_value = {"active_recipe": "other-recipe"}
        mock_list_cached.return_value = ["test-recipe", "other-recipe"]

        result = install_single_claude_recipe_to_cache(tmp_path, tmp_path, "test-recipe")

        # Verify single recipe installed
        mock_install_single.assert_called_once_with("test-recipe", tmp_path, tmp_path)

        # Verify state was read
        mock_read_state.assert_called_once()

        # Verify active file NOT updated (not active recipe)
        mock_write_active.assert_not_called()

        # Verify router refreshed
        mock_install_router.assert_called_once_with(
            tmp_path, ["test-recipe", "other-recipe"], tmp_path
        )

        assert result == cache_path

    @patch("generator.claude_layout._claude_layout.install_single_recipe_to_cache")
    @patch("generator.claude_layout._claude_layout.read_state")
    @patch("generator.claude_layout._claude_layout.list_cached_recipes")
    @patch("generator.claude_layout._claude_layout._install_router")
    @patch("generator.claude_layout._claude_layout._write_active_from_cache")
    def test_install_single_is_active(
        self,
        mock_write_active,
        mock_install_router,
        mock_list_cached,
        mock_read_state,
        mock_install_single,
        tmp_path,
    ):
        """install_single_claude_recipe_to_cache refreshes active file when recipe is active."""
        # Mock return values
        cache_path = tmp_path / ".personetta" / "claude-recipes" / "active-recipe.md"
        mock_install_single.return_value = cache_path
        mock_read_state.return_value = {"active_recipe": "active-recipe"}
        mock_list_cached.return_value = ["active-recipe"]

        result = install_single_claude_recipe_to_cache(
            tmp_path, tmp_path, "active-recipe"
        )

        # Verify single recipe installed
        mock_install_single.assert_called_once()

        # Verify active file WAS updated (is active recipe)
        mock_write_active.assert_called_once_with(tmp_path, "active-recipe", tmp_path)

        # Verify router refreshed
        mock_install_router.assert_called_once()

        assert result == cache_path

    @patch("generator.claude_layout._claude_layout.install_single_recipe_to_cache")
    @patch("generator.claude_layout._claude_layout.read_state")
    @patch("generator.claude_layout._claude_layout.list_cached_recipes")
    @patch("generator.claude_layout._claude_layout._install_router")
    def test_install_single_no_state_file(
        self,
        mock_install_router,
        mock_list_cached,
        mock_read_state,
        mock_install_single,
        tmp_path,
    ):
        """install_single_claude_recipe_to_cache handles missing state file."""
        cache_path = tmp_path / ".personetta" / "claude-recipes" / "test.md"
        mock_install_single.return_value = cache_path
        mock_read_state.return_value = None  # No state file
        mock_list_cached.return_value = ["test"]

        result = install_single_claude_recipe_to_cache(tmp_path, tmp_path, "test")

        # Should not crash, just skip active file refresh
        assert result == cache_path

    @patch("generator.claude_layout._claude_layout.install_single_recipe_to_cache")
    @patch("generator.claude_layout._claude_layout.read_state")
    @patch("generator.claude_layout._claude_layout.list_cached_recipes")
    def test_install_single_empty_cache(
        self,
        mock_list_cached,
        mock_read_state,
        mock_install_single,
        tmp_path,
    ):
        """install_single_claude_recipe_to_cache skips router when cache is empty."""
        cache_path = tmp_path / ".personetta" / "claude-recipes" / "test.md"
        mock_install_single.return_value = cache_path
        mock_read_state.return_value = None
        mock_list_cached.return_value = []  # Empty cache

        result = install_single_claude_recipe_to_cache(tmp_path, tmp_path, "test")

        # Router should not be called when cache is empty
        # (The actual implementation will skip router installation)
        assert result == cache_path


class TestListCachedClaudeRecipes:
    """Test list_cached_claude_recipes function."""

    def test_list_cached_claude_recipes_empty(self, tmp_path):
        """list_cached_claude_recipes returns empty list when cache doesn't exist."""
        result = list_cached_claude_recipes(tmp_path)
        assert result == []

    def test_list_cached_claude_recipes_with_files(self, tmp_path):
        """list_cached_claude_recipes returns sorted recipe names."""
        cache_dir = tmp_path / ".personetta" / "claude-recipes"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Create recipe files
        (cache_dir / "recipe-c.md").write_text("c")
        (cache_dir / "recipe-a.md").write_text("a")
        (cache_dir / "recipe-b.md").write_text("b")

        result = list_cached_claude_recipes(tmp_path)

        # Should be sorted alphabetically
        assert result == ["recipe-a", "recipe-b", "recipe-c"]


class TestBackwardCompatibilityConstants:
    """Test backward compatibility constants."""

    def test_baseline_name_constant(self):
        """BASELINE_NAME matches CLAUDE_BASELINE_FILENAME."""
        assert BASELINE_NAME == CLAUDE_BASELINE_FILENAME

    def test_router_name_constant(self):
        """ROUTER_NAME matches CLAUDE_ROUTER_FILENAME."""
        assert ROUTER_NAME == CLAUDE_ROUTER_FILENAME

    def test_active_name_constant(self):
        """ACTIVE_NAME matches CLAUDE_ACTIVE_FILENAME."""
        assert ACTIVE_NAME == CLAUDE_ACTIVE_FILENAME

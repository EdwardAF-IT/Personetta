"""
Unit tests for generator/cline_layout.py - Cline layout strategy.

Covers ClineLayout class and module-level functions with comprehensive mocking
to achieve 100% coverage including all error paths.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from generator.cline_layout import (
    ClineLayout,
    cline_global_rules_dir,
    personetta_root,
    cline_recipe_cache_dir,
    cline_state_path,
    write_cline_state,
    read_cline_state,
    _cleanup_cline_on_zero_successes,
    install_all_cline,
    set_active_cline,
    install_cline_router,
    install_single_cline_recipe_to_cache,
    list_cached_cline_recipes,
)
from generator.constants import (
    FORMAT_CLINE,
    CLINE_RECIPES_SUBDIR,
    CLINE_STATE_FILE,
    CLINE_BASELINE_FILENAME,
    CLINE_ROUTER_FILENAME,
    CLINE_ACTIVE_FILENAME,
)


class TestClineLayout:
    """Test ClineLayout class methods."""

    def test_format_name(self):
        """ClineLayout.format_name returns 'cline'."""
        layout = ClineLayout()
        assert layout.format_name == FORMAT_CLINE

    def test_recipes_subdir(self):
        """ClineLayout.recipes_subdir returns correct subdirectory name."""
        layout = ClineLayout()
        assert layout.recipes_subdir == CLINE_RECIPES_SUBDIR

    def test_rules_dir(self, tmp_path):
        """ClineLayout.rules_dir returns Documents/Cline/Rules path."""
        layout = ClineLayout()
        result = layout.rules_dir(tmp_path)
        assert result == tmp_path / "Documents" / "Cline" / "Rules"

    def test_state_file(self):
        """ClineLayout.state_file returns correct state file name."""
        layout = ClineLayout()
        assert layout.state_file == CLINE_STATE_FILE

    def test_wrap_output(self):
        """ClineLayout.wrap_output returns content unchanged (no wrapping)."""
        layout = ClineLayout()
        content = "# Test Content\n\nSome markdown text."
        recipe = {"name": "test-recipe"}
        result = layout.wrap_output(content, recipe)
        assert result == content

    def test_cleanup_on_zero_successes_handles_missing_files(self, tmp_path):
        """ClineLayout.cleanup_on_zero_successes handles missing files gracefully."""
        layout = ClineLayout()
        # No files exist - should not raise error
        layout.cleanup_on_zero_successes(tmp_path)

    def test_write_active_from_cache(self, tmp_path):
        """ClineLayout._write_active_from_cache writes active file from cache."""
        layout = ClineLayout()
        rules_dir = tmp_path / "Documents" / "Cline" / "Rules"
        cache_dir = tmp_path / ".personetta" / "cline-recipes"
        base_dir = tmp_path / "base"

        # Create cache directory and recipe
        cache_dir.mkdir(parents=True, exist_ok=True)
        recipe_file = cache_dir / "test-recipe.md"
        recipe_content = "# Test Recipe\n\nRecipe content here."
        recipe_file.write_text(recipe_content, encoding="utf-8")

        result = layout._write_active_from_cache(tmp_path, "test-recipe", base_dir)

        assert result == rules_dir / CLINE_ACTIVE_FILENAME
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert content == recipe_content

    @patch("generator.cline_layout.load_system_role")
    @patch("generator.cline_layout.format_baseline_for_plain")
    @patch("generator.cline_layout.collect_recipe_router_rows")
    @patch("generator.cline_layout.format_router_for_plain")
    def test_write_baseline_router_active_real_files(
        self,
        mock_format_router,
        mock_collect_rows,
        mock_format_baseline,
        mock_load_system,
        tmp_path,
    ):
        """ClineLayout.write_baseline_router_active creates all files with actual I/O."""
        layout = ClineLayout()
        cache_dir = tmp_path / ".personetta" / "cline-recipes"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Create test recipe files
        (cache_dir / "recipe-a.md").write_text("Recipe A content", encoding="utf-8")
        (cache_dir / "recipe-b.md").write_text("Recipe B content", encoding="utf-8")

        # Mock the formatting functions
        mock_load_system.return_value = {"name": "baseline"}
        mock_format_baseline.return_value = "Baseline content"
        mock_collect_rows.return_value = []
        mock_format_router.return_value = "Router content"

        layout.write_baseline_router_active(tmp_path, ["recipe-b", "recipe-a"], tmp_path)

        # Verify all files created
        rules_dir = tmp_path / "Documents" / "Cline" / "Rules"
        assert (rules_dir / CLINE_BASELINE_FILENAME).exists()
        assert (rules_dir / CLINE_ROUTER_FILENAME).exists()
        assert (rules_dir / CLINE_ACTIVE_FILENAME).exists()

        # Verify content
        assert (rules_dir / CLINE_BASELINE_FILENAME).read_text(
            encoding="utf-8"
        ) == "Baseline content"
        assert (rules_dir / CLINE_ROUTER_FILENAME).read_text(
            encoding="utf-8"
        ) == "Router content"
        # Active should be first alphabetically = recipe-a
        assert (rules_dir / CLINE_ACTIVE_FILENAME).read_text(
            encoding="utf-8"
        ) == "Recipe A content"

    def test_cleanup_on_zero_successes_real_files(self, tmp_path):
        """ClineLayout.cleanup_on_zero_successes removes all files (real I/O)."""
        layout = ClineLayout()
        rules_dir = tmp_path / "Documents" / "Cline" / "Rules"
        rules_dir.mkdir(parents=True)
        cache_dir = tmp_path / ".personetta" / "cline-recipes"
        cache_dir.mkdir(parents=True)

        # Create files
        (rules_dir / CLINE_BASELINE_FILENAME).write_text("baseline", encoding="utf-8")
        (rules_dir / CLINE_ROUTER_FILENAME).write_text("router", encoding="utf-8")
        (rules_dir / CLINE_ACTIVE_FILENAME).write_text("active", encoding="utf-8")
        (cache_dir / "recipe1.md").write_text("recipe1", encoding="utf-8")
        (cache_dir / "recipe2.md").write_text("recipe2", encoding="utf-8")
        state_path = tmp_path / ".personetta" / CLINE_STATE_FILE
        state_path.write_text('{"active_recipe": "test"}', encoding="utf-8")

        layout.cleanup_on_zero_successes(tmp_path)

        # Verify all removed
        assert not (rules_dir / CLINE_BASELINE_FILENAME).exists()
        assert not (rules_dir / CLINE_ROUTER_FILENAME).exists()
        assert not (rules_dir / CLINE_ACTIVE_FILENAME).exists()
        assert not (cache_dir / "recipe1.md").exists()
        assert not (cache_dir / "recipe2.md").exists()
        assert not state_path.exists()

    @patch("generator.cline_layout.load_system_role")
    @patch("generator.cline_layout.collect_recipe_router_rows")
    @patch("generator.cline_layout.format_router_for_plain")
    def test_install_router_real_files(
        self, mock_format_router, mock_collect_rows, mock_load_system, tmp_path
    ):
        """ClineLayout._install_router writes router file (real I/O)."""
        layout = ClineLayout()

        mock_load_system.return_value = {"name": "router"}
        mock_collect_rows.return_value = []
        mock_format_router.return_value = "Router markdown content"

        result = layout._install_router(tmp_path, ["recipe1"], tmp_path)

        rules_dir = tmp_path / "Documents" / "Cline" / "Rules"
        assert result == rules_dir / CLINE_ROUTER_FILENAME
        assert result.exists()
        assert result.read_text(encoding="utf-8") == "Router markdown content"


class TestModuleLevelFunctions:
    """Test module-level API functions."""

    def test_cline_global_rules_dir(self, tmp_path):
        """cline_global_rules_dir returns Documents/Cline/Rules path."""
        result = cline_global_rules_dir(tmp_path)
        assert result == tmp_path / "Documents" / "Cline" / "Rules"

    def test_personetta_root(self, tmp_path):
        """personetta_root returns .personetta directory."""
        result = personetta_root(tmp_path)
        assert result == tmp_path / ".personetta"

    def test_cline_recipe_cache_dir(self, tmp_path):
        """cline_recipe_cache_dir returns cache directory path."""
        result = cline_recipe_cache_dir(tmp_path)
        assert result == tmp_path / ".personetta" / "cline-recipes"

    def test_cline_state_path(self, tmp_path):
        """cline_state_path returns state file path."""
        result = cline_state_path(tmp_path)
        assert result == tmp_path / ".personetta" / "cline-active.json"

    def test_write_cline_state(self, tmp_path):
        """write_cline_state writes state JSON file."""
        write_cline_state(tmp_path, "test-recipe")

        state_path = tmp_path / ".personetta" / "cline-active.json"
        assert state_path.exists()

        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert state["active_recipe"] == "test-recipe"
        assert state["format"] == FORMAT_CLINE

    def test_read_cline_state(self, tmp_path):
        """read_cline_state reads state JSON file."""
        state_path = tmp_path / ".personetta" / "cline-active.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps({"active_recipe": "test", "format": "cline"}), encoding="utf-8"
        )

        result = read_cline_state(tmp_path)
        assert result is not None
        assert result["active_recipe"] == "test"

    def test_read_cline_state_missing_file(self, tmp_path):
        """read_cline_state returns None when file doesn't exist."""
        result = read_cline_state(tmp_path)
        assert result is None

    def test_cleanup_cline_on_zero_successes(self, tmp_path):
        """_cleanup_cline_on_zero_successes delegates to layout cleanup."""
        rules_dir = tmp_path / "Documents" / "Cline" / "Rules"
        rules_dir.mkdir(parents=True, exist_ok=True)

        baseline = rules_dir / CLINE_BASELINE_FILENAME
        baseline.write_text("content", encoding="utf-8")
        assert baseline.exists()

        _cleanup_cline_on_zero_successes(tmp_path)

        assert not baseline.exists()

    @patch("generator.cline_layout._cline_layout.install_all")
    def test_install_all_cline(self, mock_install_all, tmp_path):
        """install_all_cline delegates to layout.install_all."""
        base_dir = tmp_path / "base"
        target_root = tmp_path / "target"
        mock_install_all.return_value = (["recipe1"], [])

        result = install_all_cline(
            base_dir, target_root, recipe_filter="test*", recipe_list=["recipe1"]
        )

        assert result == (["recipe1"], [])
        mock_install_all.assert_called_once_with(
            base_dir, target_root, recipe_filter="test*", recipe_list=["recipe1"]
        )

    def test_set_active_cline_success(self, tmp_path):
        """set_active_cline switches active recipe when cache exists."""
        base_dir = tmp_path / "base"
        cache_dir = tmp_path / ".personetta" / "cline-recipes"

        # Create cache directory and recipe
        cache_dir.mkdir(parents=True, exist_ok=True)
        recipe_file = cache_dir / "test-recipe.md"
        recipe_file.write_text("Recipe content", encoding="utf-8")

        result = set_active_cline(base_dir, tmp_path, "test-recipe")

        assert result.exists()

        # Verify state was written
        state_path = tmp_path / ".personetta" / "cline-active.json"
        assert state_path.exists()
        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert state["active_recipe"] == "test-recipe"

    def test_set_active_cline_missing_cache(self, tmp_path):
        """set_active_cline raises FileNotFoundError when cache missing."""
        base_dir = tmp_path / "base"

        with pytest.raises(FileNotFoundError) as exc_info:
            set_active_cline(base_dir, tmp_path, "missing-recipe")

        error_msg = str(exc_info.value)
        assert "No cached Cline recipe 'missing-recipe'" in error_msg

    @patch("generator.cline_layout._cline_layout._install_router")
    def test_install_cline_router(self, mock_install_router, tmp_path):
        """install_cline_router delegates to layout._install_router."""
        base_dir = tmp_path / "base"
        expected_path = tmp_path / "Documents" / "Cline" / "Rules" / "router.md"
        mock_install_router.return_value = expected_path

        result = install_cline_router(tmp_path, ["recipe1"], base_dir)

        assert result == expected_path
        mock_install_router.assert_called_once_with(tmp_path, ["recipe1"], base_dir)

    @patch("generator.cline_layout._cline_layout.install_single_recipe_to_cache")
    @patch("generator.cline_layout._cline_layout.read_state")
    @patch("generator.cline_layout._cline_layout._write_active_from_cache")
    @patch("generator.cline_layout._cline_layout.list_cached_recipes")
    @patch("generator.cline_layout._cline_layout._install_router")
    def test_install_single_cline_recipe_to_cache_not_active(
        self,
        mock_install_router,
        mock_list_cached,
        mock_write_active,
        mock_read_state,
        mock_install_single,
        tmp_path,
    ):
        """install_single_cline_recipe_to_cache when recipe is not active."""
        base_dir = tmp_path / "base"
        cache_path = tmp_path / ".personetta" / "cline-recipes" / "test-recipe.md"

        # Recipe is not active
        mock_read_state.return_value = {"active_recipe": "other-recipe"}
        mock_list_cached.return_value = ["test-recipe", "other-recipe"]
        mock_install_single.return_value = cache_path

        result = install_single_cline_recipe_to_cache(base_dir, tmp_path, "test-recipe")

        assert result == cache_path
        mock_install_single.assert_called_once_with("test-recipe", base_dir, tmp_path)
        # Should not refresh active file
        mock_write_active.assert_not_called()
        # Should refresh router
        mock_install_router.assert_called_once()

    @patch("generator.cline_layout._cline_layout.install_single_recipe_to_cache")
    @patch("generator.cline_layout._cline_layout.read_state")
    @patch("generator.cline_layout._cline_layout._write_active_from_cache")
    @patch("generator.cline_layout._cline_layout.list_cached_recipes")
    @patch("generator.cline_layout._cline_layout._install_router")
    def test_install_single_cline_recipe_to_cache_is_active(
        self,
        mock_install_router,
        mock_list_cached,
        mock_write_active,
        mock_read_state,
        mock_install_single,
        tmp_path,
    ):
        """install_single_cline_recipe_to_cache when recipe IS active (refreshes active file)."""
        base_dir = tmp_path / "base"
        cache_path = tmp_path / ".personetta" / "cline-recipes" / "test-recipe.md"

        # Recipe IS active
        mock_read_state.return_value = {"active_recipe": "test-recipe"}
        mock_list_cached.return_value = ["test-recipe"]
        mock_install_single.return_value = cache_path

        result = install_single_cline_recipe_to_cache(base_dir, tmp_path, "test-recipe")

        assert result == cache_path
        # Should refresh active file since recipe is active
        mock_write_active.assert_called_once_with(tmp_path, "test-recipe", base_dir)
        # Should refresh router
        mock_install_router.assert_called_once()

    @patch("generator.cline_layout._cline_layout.list_cached_recipes")
    def test_list_cached_cline_recipes(self, mock_list_cached, tmp_path):
        """list_cached_cline_recipes delegates to layout.list_cached_recipes."""
        mock_list_cached.return_value = ["recipe1", "recipe2"]

        result = list_cached_cline_recipes(tmp_path)

        assert result == ["recipe1", "recipe2"]
        mock_list_cached.assert_called_once_with(tmp_path)

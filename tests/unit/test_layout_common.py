"""Unit tests for generator/layout_common.py.

Tests shared layout utilities for recipe router and baseline generation.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch


from generator.layout_common import (
    build_plain_baseline_markdown,
    build_plain_router_markdown,
    collect_recipe_router_rows,
    set_active_cli_lines,
)


class TestSetActiveCliLines:
    """Test CLI command line generation."""

    def test_generates_cli_command(self):
        """Should generate personetta command."""
        py, rf = set_active_cli_lines("test-recipe", "copilot")

        # Both should be the same now - using personetta
        assert rf == "personetta set-active test-recipe --format copilot"
        # py is kept for backwards compat but should also use personetta
        assert "personetta" in py or "set-active test-recipe --format copilot" in py

    def test_different_formats(self):
        """Should handle different format values."""
        py, rf = set_active_cli_lines("my-recipe", "claude")

        assert "my-recipe --format claude" in rf

    def test_recipe_id_with_hyphens(self):
        """Should handle recipe IDs with multiple hyphens."""
        py, rf = set_active_cli_lines("implement-python-backend-secure", "cursor")

        assert "implement-python-backend-secure" in py
        assert "implement-python-backend-secure" in rf


class TestCollectRecipeRouterRows:
    """Test recipe router row collection."""

    @patch("generator.layout_common.load_recipe")
    def test_collects_all_recipes(self, mock_load_recipe, tmp_path: Path):
        """Should collect all recipe names."""
        mock_load_recipe.side_effect = [
            {"description": "Recipe A description", "activation_phrases": ["phrase a"]},
            {"description": "Recipe B description", "activation_phrases": []},
        ]

        recipe_names = ["recipe-a", "recipe-b"]

        rows = collect_recipe_router_rows(tmp_path, recipe_names)

        assert len(rows) == 2
        assert rows[0]["name"] == "recipe-a"
        assert rows[1]["name"] == "recipe-b"

    @patch("generator.layout_common.load_recipe")
    def test_extracts_first_line_of_description(self, mock_load_recipe, tmp_path: Path):
        """Should extract first line from multi-line description."""
        mock_load_recipe.return_value = {
            "description": "First line\nSecond line\nThird line",
            "activation_phrases": [],
        }

        rows = collect_recipe_router_rows(tmp_path, ["test"])

        assert rows[0]["description"] == "First line"

    @patch("generator.layout_common.load_recipe")
    def test_handles_missing_description(self, mock_load_recipe, tmp_path: Path):
        """Should handle missing description gracefully."""
        mock_load_recipe.return_value = {
            "activation_phrases": [],
        }

        rows = collect_recipe_router_rows(tmp_path, ["test"])

        assert rows[0]["description"] == ""

    @patch("generator.layout_common.load_recipe")
    def test_includes_activation_phrases(self, mock_load_recipe, tmp_path: Path):
        """Should include activation phrases from recipe."""
        mock_load_recipe.return_value = {
            "description": "Test",
            "activation_phrases": ["phrase 1", "phrase 2"],
        }

        rows = collect_recipe_router_rows(tmp_path, ["test"])

        assert rows[0]["activation_phrases"] == ["phrase 1", "phrase 2"]

    @patch("generator.layout_common.load_recipe")
    def test_sorts_recipes(self, mock_load_recipe, tmp_path: Path):
        """Should sort recipes alphabetically by name."""
        mock_load_recipe.side_effect = [
            {"description": "C", "activation_phrases": []},
            {"description": "A", "activation_phrases": []},
            {"description": "B", "activation_phrases": []},
        ]

        rows = collect_recipe_router_rows(tmp_path, ["recipe-c", "recipe-a", "recipe-b"])

        # Should be sorted: a, b, c
        assert rows[0]["name"] == "recipe-a"
        assert rows[1]["name"] == "recipe-b"
        assert rows[2]["name"] == "recipe-c"


class TestBuildPlainRouterMarkdown:
    """Test plain router markdown generation."""

    def test_basic_structure(self):
        """Should generate basic router structure."""
        recipe_rows = [
            {
                "name": "test-recipe",
                "description": "Test description",
                "activation_phrases": [],
            }
        ]

        result = build_plain_router_markdown(
            "copilot",
            recipe_rows,
            cache_glob="~/.personetta/copilot-recipes/",
            active_filename="personetta-active.instructions.md",
        )

        assert "# Personetta — recipe router" in result
        assert "test-recipe" in result
        assert "Test description" in result
        assert "personetta-active.instructions.md" in result
        assert "~/.personetta/copilot-recipes/" in result

    def test_includes_mismatch_detection_section(self):
        """Should include mismatch detection section."""
        result = build_plain_router_markdown(
            "copilot",
            [],
            cache_glob="~/.personetta/copilot-recipes/",
            active_filename="personetta-active.instructions.md",
        )

        assert "⚠️ ACTIVE PERSONA MISMATCH DETECTION" in result
        assert "STOP immediately" in result
        assert "Do NOT silently work in the wrong persona" in result

    def test_includes_set_active_commands(self):
        """Should include set-active commands for each recipe."""
        recipe_rows = [
            {"name": "recipe-a", "description": "A", "activation_phrases": []},
            {"name": "recipe-b", "description": "B", "activation_phrases": []},
        ]

        result = build_plain_router_markdown(
            "claude",
            recipe_rows,
            cache_glob="~/.personetta/claude-recipes/",
            active_filename="personetta-active.md",
        )

        assert "personetta set-active recipe-a --format claude" in result
        assert "personetta set-active recipe-b --format claude" in result

    def test_includes_recipe_index(self):
        """Should include detailed recipe index."""
        recipe_rows = [
            {
                "name": "test-recipe",
                "description": "Test description",
                "activation_phrases": ["phrase 1", "phrase 2"],
            }
        ]

        result = build_plain_router_markdown(
            "copilot",
            recipe_rows,
            cache_glob="~/.personetta/copilot-recipes/",
            active_filename="personetta-active.instructions.md",
        )

        assert "## Recipe index" in result
        assert "### `test-recipe`" in result
        assert "**Summary:** Test description" in result
        assert "**Activation phrases**" in result
        assert "phrase 1" in result
        assert "phrase 2" in result

    def test_handles_multiline_description(self):
        """Should handle multi-line descriptions in index."""
        recipe_rows = [
            {
                "name": "test",
                "description": "Line 1\nLine 2\nLine 3",
                "activation_phrases": [],
            }
        ]

        result = build_plain_router_markdown(
            "copilot",
            recipe_rows,
            cache_glob="~/.personetta/copilot-recipes/",
            active_filename="personetta-active.instructions.md",
        )

        # Should replace newlines with spaces
        assert "Line 1 Line 2 Line 3" in result


class TestBuildPlainBaselineMarkdown:
    """Test plain baseline markdown generation."""

    def test_basic_structure(self):
        """Should generate basic baseline structure."""
        result = build_plain_baseline_markdown(
            "copilot",
            host_product="GitHub Copilot in VS Code",
            cache_glob="~/.personetta/copilot-recipes/",
            active_filename="personetta-active.instructions.md",
            router_filename="personetta-router.instructions.md",
        )

        assert "# Personetta — baseline" in result
        assert "*Host tool:* GitHub Copilot in VS Code" in result
        assert "personetta-active.instructions.md" in result
        assert "personetta-router.instructions.md" in result

    def test_includes_preflight_checklist(self):
        """Should include mandatory preflight checklist."""
        result = build_plain_baseline_markdown(
            "copilot",
            host_product="Test",
            cache_glob="~/.personetta/",
            active_filename="active.md",
            router_filename="router.md",
        )

        assert "⚡ MANDATORY PRE-FLIGHT CHECKLIST ⚡" in result
        assert "Check if the active persona defines" in result
        assert "VERIFY WORK ALIGNMENT" in result

    def test_includes_work_alignment_examples(self):
        """Should include work alignment examples."""
        result = build_plain_baseline_markdown(
            "claude",
            host_product="Claude Code",
            cache_glob="~/.personetta/",
            active_filename="active.md",
            router_filename="router.md",
        )

        assert "🔍 WORK ALIGNMENT EXAMPLES" in result
        assert "MISMATCH — Must warn:" in result
        assert "MATCH — Proceed:" in result
        assert (
            "personetta set-active implement-python-backend-perf --format claude"
            in result
        )

    def test_includes_postflight_checklist(self):
        """Should include mandatory postflight checklist."""
        result = build_plain_baseline_markdown(
            "copilot",
            host_product="Test",
            cache_glob="~/.personetta/",
            active_filename="active.md",
            router_filename="router.md",
        )

        assert "📋 MANDATORY POST-FLIGHT CHECKLIST 📋" in result
        assert "### Role compliance" in result
        assert "**Verification**" in result
        assert "**Guidelines applied**" in result
        assert "**Guidelines skipped**" in result

    def test_includes_cross_cutting_rules(self):
        """Should include cross-cutting rules."""
        result = build_plain_baseline_markdown(
            "copilot",
            host_product="Test",
            cache_glob="~/.personetta/",
            active_filename="active.md",
            router_filename="router.md",
        )

        assert "## Cross-cutting rules" in result
        assert "**Active file first**" in result
        assert "**Tools and verification**" in result
        assert "**One persona**" in result
        assert "**Router**" in result
        assert "**Cache**" in result

    def test_includes_extra_notes(self):
        """Should include extra notes when provided."""
        result = build_plain_baseline_markdown(
            "copilot",
            host_product="Test",
            cache_glob="~/.personetta/",
            active_filename="active.md",
            router_filename="router.md",
            extra_notes=("Note 1", "Note 2"),
        )

        assert "Note 1" in result
        assert "Note 2" in result

    def test_format_specific_cache_glob(self):
        """Should use correct format in cache instructions."""
        result = build_plain_baseline_markdown(
            "cursor",
            host_product="Cursor",
            cache_glob="~/.cursor/rules/",
            active_filename="personetta-active.mdrules",
            router_filename="personetta-router.mdrules",
        )

        assert "~/.cursor/rules/" in result
        assert "personetta set-active <recipe-id> --format cursor" in result

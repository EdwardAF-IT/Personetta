"""Unit tests for generator/cli/commands/list_skills.py.

Tests skill listing command functionality including
refresh, filtering, and formatting.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

from generator.cli.commands.list_skills import (
    _count_total_skills,
    _format_description,
    _get_formats_to_show,
    _print_skill_details,
    _print_skill_header,
    _print_skill_info,
    _print_skills_for_format,
    _refresh_catalog_if_requested,
    cmd_list_skills,
)


@pytest.fixture
def mock_args():
    """Create mock arguments namespace."""
    args = argparse.Namespace()
    args.refresh = False
    args.format = None
    return args


@pytest.fixture
def sample_catalog():
    """Create sample catalog data."""
    return {
        "version": "1.0",
        "last_updated": "2024-01-01T00:00:00",
        "skills": {
            "copilot": {
                "test-skill": {
                    "name": "test-skill",
                    "description": "Test skill description",
                    "source_recipes": ["recipe-a", "recipe-b"],
                    "has_scripts": True,
                    "script_count": 3,
                    "path": "/path/to/skill",
                }
            },
            "claude": {
                "claude-skill": {
                    "name": "claude-skill",
                    "description": "Claude skill description",
                    "source_recipes": ["recipe-c"],
                    "has_scripts": False,
                    "path": "/path/to/claude-skill",
                }
            },
        },
    }


class TestRefreshCatalogIfRequested:
    """Test catalog refresh logic."""

    @patch("generator.skill_catalog.refresh_catalog")
    def test_refresh_not_requested(self, mock_refresh, mock_args):
        """Should not refresh when flag not set."""
        mock_args.refresh = False

        _refresh_catalog_if_requested(mock_args)

        mock_refresh.assert_not_called()

    @patch("generator.skill_catalog.refresh_catalog")
    def test_refresh_specific_format(self, mock_refresh, mock_args):
        """Should refresh specific format when provided."""
        mock_args.refresh = True
        mock_args.format = "copilot"

        _refresh_catalog_if_requested(mock_args)

        mock_refresh.assert_called_once_with("copilot")

    @patch("generator.skill_catalog.refresh_all_catalogs")
    def test_refresh_all_formats(self, mock_refresh_all, mock_args):
        """Should refresh all formats when no format specified."""
        mock_args.refresh = True
        mock_args.format = None

        _refresh_catalog_if_requested(mock_args)

        mock_refresh_all.assert_called_once()


class TestGetFormatsToShow:
    """Test format filtering logic."""

    def test_specific_format(self, mock_args):
        """Should return single format when specified."""
        mock_args.format = "copilot"

        result = _get_formats_to_show(mock_args)

        assert result == ["copilot"]

    def test_all_formats(self, mock_args):
        """Should return all formats when none specified."""
        mock_args.format = None

        result = _get_formats_to_show(mock_args)

        assert result == ["copilot", "claude", "cursor", "cline"]


class TestCountTotalSkills:
    """Test skill counting logic."""

    def test_count_all_formats(self, sample_catalog):
        """Should count skills across all formats."""
        formats = ["copilot", "claude", "cursor", "cline"]

        total = _count_total_skills(sample_catalog, formats)

        assert total == 2  # 1 copilot + 1 claude

    def test_count_specific_format(self, sample_catalog):
        """Should count skills for specific format."""
        formats = ["copilot"]

        total = _count_total_skills(sample_catalog, formats)

        assert total == 1

    def test_count_missing_format(self, sample_catalog):
        """Should handle missing format gracefully."""
        formats = ["missing-format"]

        total = _count_total_skills(sample_catalog, formats)

        assert total == 0

    def test_count_empty_catalog(self):
        """Should return 0 for empty catalog."""
        catalog = {"skills": {}}

        total = _count_total_skills(catalog, ["copilot"])

        assert total == 0


class TestPrintSkillHeader:
    """Test skill header printing."""

    def test_prints_skill_count(self, sample_catalog, capsys):
        """Should print total skill count."""
        catalog_path = Path("/path/to/catalog.json")

        _print_skill_header(5, catalog_path, sample_catalog)

        captured = capsys.readouterr()
        assert "Installed Skills (5 total):" in captured.out

    def test_prints_catalog_path(self, sample_catalog, capsys):
        """Should print catalog path."""
        catalog_path = Path("/test/catalog.json")

        _print_skill_header(1, catalog_path, sample_catalog)

        captured = capsys.readouterr()
        assert str(catalog_path) in captured.out

    def test_prints_last_updated(self, sample_catalog, capsys):
        """Should print last updated timestamp."""
        catalog_path = Path("/path/catalog.json")

        _print_skill_header(1, catalog_path, sample_catalog)

        captured = capsys.readouterr()
        assert "Last updated: 2024-01-01T00:00:00" in captured.out

    def test_handles_missing_last_updated(self, capsys):
        """Should handle missing last_updated field."""
        catalog = {}
        catalog_path = Path("/path/catalog.json")

        _print_skill_header(0, catalog_path, catalog)

        captured = capsys.readouterr()
        assert "Last updated: unknown" in captured.out


class TestFormatDescription:
    """Test description formatting."""

    def test_short_description_unchanged(self):
        """Should not truncate short descriptions."""
        desc = "Short description"

        result = _format_description(desc)

        assert result == "Short description"

    def test_long_description_truncated(self):
        """Should truncate long descriptions."""
        desc = "A" * 100

        result = _format_description(desc, max_length=50)

        assert len(result) == 50
        assert result.endswith("...")
        assert result == ("A" * 47) + "..."

    def test_custom_max_length(self):
        """Should respect custom max_length."""
        desc = "B" * 200

        result = _format_description(desc, max_length=30)

        assert len(result) == 30
        assert result.endswith("...")


class TestPrintSkillDetails:
    """Test skill details printing."""

    def test_prints_recipes(self, capsys):
        """Should print source recipes."""
        skill_info = {
            "source_recipes": ["recipe-a", "recipe-b"],
            "has_scripts": False,
            "path": "/path/to/skill",
        }

        _print_skill_details(skill_info)

        captured = capsys.readouterr()
        assert "Recipes: recipe-a, recipe-b" in captured.out

    def test_prints_scripts_count(self, capsys):
        """Should print script count when has_scripts is True."""
        skill_info = {
            "source_recipes": ["recipe-a"],
            "has_scripts": True,
            "script_count": 5,
            "path": "/path/to/skill",
        }

        _print_skill_details(skill_info)

        captured = capsys.readouterr()
        assert "Scripts: 5 bundled" in captured.out

    def test_prints_path(self, capsys):
        """Should print skill path."""
        skill_info = {
            "source_recipes": [],
            "has_scripts": False,
            "path": "/custom/path",
        }

        _print_skill_details(skill_info)

        captured = capsys.readouterr()
        assert "Path: /custom/path" in captured.out

    def test_no_recipes_no_output(self, capsys):
        """Should handle missing recipes gracefully."""
        skill_info = {
            "has_scripts": False,
            "path": "/path",
        }

        _print_skill_details(skill_info)

        captured = capsys.readouterr()
        # Should still print path even without recipes
        assert "Path:" in captured.out


class TestPrintSkillInfo:
    """Test full skill info printing."""

    def test_prints_skill_name(self, capsys):
        """Should print skill name."""
        skill_info = {
            "description": "Test description",
            "source_recipes": [],
            "path": "/path",
        }

        _print_skill_info("my-skill", skill_info)

        captured = capsys.readouterr()
        assert "my-skill" in captured.out

    def test_prints_description(self, capsys):
        """Should print formatted description."""
        skill_info = {
            "description": "Short description",
            "source_recipes": [],
            "path": "/path",
        }

        _print_skill_info("test", skill_info)

        captured = capsys.readouterr()
        assert "Short description" in captured.out

    def test_uses_default_description(self, capsys):
        """Should use default when description missing."""
        skill_info = {
            "source_recipes": [],
            "path": "/path",
        }

        _print_skill_info("test", skill_info)

        captured = capsys.readouterr()
        assert "No description" in captured.out


class TestPrintSkillsForFormat:
    """Test format-specific skill printing."""

    def test_prints_format_header(self, capsys):
        """Should print format header."""
        skills = {
            "skill-a": {
                "description": "Skill A",
                "source_recipes": [],
                "path": "/path/a",
            }
        }

        _print_skills_for_format("copilot", skills)

        captured = capsys.readouterr()
        assert "== COPILOT ==" in captured.out

    def test_prints_all_skills(self, capsys):
        """Should print all skills in format."""
        skills = {
            "skill-b": {"description": "B", "source_recipes": [], "path": "/b"},
            "skill-a": {"description": "A", "source_recipes": [], "path": "/a"},
        }

        _print_skills_for_format("claude", skills)

        captured = capsys.readouterr()
        # Should be sorted
        assert "skill-a" in captured.out
        assert "skill-b" in captured.out


class TestCmdListSkills:
    """Test main command function."""

    @patch("generator.skill_catalog.load_catalog")
    @patch("generator.skill_catalog.get_catalog_path")
    def test_no_skills_returns_zero(self, mock_get_path, mock_load, mock_args, capsys):
        """Should return 0 when no skills found."""
        mock_get_path.return_value = Path("/catalog.json")
        mock_load.return_value = {"skills": {}}

        result = cmd_list_skills(mock_args)

        assert result == 0
        captured = capsys.readouterr()
        assert "No skills found" in captured.out

    @patch("generator.skill_catalog.load_catalog")
    @patch("generator.skill_catalog.get_catalog_path")
    def test_lists_all_formats(
        self, mock_get_path, mock_load, mock_args, sample_catalog, capsys
    ):
        """Should list all formats when none specified."""
        mock_get_path.return_value = Path("/catalog.json")
        mock_load.return_value = sample_catalog
        mock_args.format = None

        result = cmd_list_skills(mock_args)

        assert result == 0
        captured = capsys.readouterr()
        assert "== COPILOT ==" in captured.out
        assert "== CLAUDE ==" in captured.out

    @patch("generator.skill_catalog.load_catalog")
    @patch("generator.skill_catalog.get_catalog_path")
    def test_filters_by_format(
        self, mock_get_path, mock_load, mock_args, sample_catalog, capsys
    ):
        """Should filter by specified format."""
        mock_get_path.return_value = Path("/catalog.json")
        mock_load.return_value = sample_catalog
        mock_args.format = "copilot"

        result = cmd_list_skills(mock_args)

        assert result == 0
        captured = capsys.readouterr()
        assert "== COPILOT ==" in captured.out
        assert "== CLAUDE ==" not in captured.out

    @patch("generator.skill_catalog.refresh_catalog")
    @patch("generator.skill_catalog.load_catalog")
    @patch("generator.skill_catalog.get_catalog_path")
    def test_refreshes_catalog_when_requested(
        self, mock_get_path, mock_load, mock_refresh, mock_args
    ):
        """Should refresh catalog when --refresh flag set."""
        mock_get_path.return_value = Path("/catalog.json")
        mock_load.return_value = {"skills": {}}
        mock_args.refresh = True
        mock_args.format = "copilot"

        cmd_list_skills(mock_args)

        mock_refresh.assert_called_once_with("copilot")

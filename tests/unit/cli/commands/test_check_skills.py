"""Tests for check_skills command."""

from __future__ import annotations

import argparse

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.cli, pytest.mark.readonly]


def create_mock_args(**kwargs) -> argparse.Namespace:
    """Create mock Namespace with default values."""
    defaults = {
        "name": None,
        "format": "copilot",
        "target": None,
        "whatif": False,
        "yes": False,
        "output": None,
        "install": False,
        "patterns": None,
        "roles": False,
        "recipes": False,
        "backend": None,
        "prompt": None,
        "compact_prompt": None,
        "force": False,
        "all": False,
        "refresh": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class TestCheckSkillsCommand:
    """Tests for check_skills command."""

    def test_check_skills_no_stale_skills(self, tmp_path, monkeypatch):
        """Test check_skills when all skills are up to date."""
        from generator.cli.commands.check_skills import cmd_check_skills

        args = create_mock_args()
        monkeypatch.setattr(
            "generator.cli.commands.check_skills._collect_stale_skills", lambda *a: []
        )

        exit_code = cmd_check_skills(args)
        assert exit_code == 0

    def test_check_skills_with_stale_skills(self, tmp_path, capsys, monkeypatch):
        """Test check_skills when stale skills are found."""
        from generator.cli.commands.check_skills import cmd_check_skills

        stale = [
            {
                "skill_name": "test-skill",
                "format": "copilot",
                "reason": "Recipe updated",
                "source_recipes": ["test-python"],
                "skill_dir": tmp_path / "skill",
            }
        ]

        args = create_mock_args()
        monkeypatch.setattr(
            "generator.cli.commands.check_skills._collect_stale_skills", lambda *a: stale
        )

        exit_code = cmd_check_skills(args)
        assert exit_code == 1

        captured = capsys.readouterr()
        assert "test-skill" in captured.out
        assert "update-skill" in captured.out

    def test_check_skills_specific_format(self, tmp_path, monkeypatch):
        """Test check_skills with specific format."""
        from generator.cli.commands.check_skills import _resolve_formats_to_check

        args = create_mock_args(format="copilot")
        formats = _resolve_formats_to_check(args)

        assert formats == ["copilot"]

    def test_check_skills_all_formats(self, tmp_path, monkeypatch):
        """Test check_skills defaults to all formats."""
        from generator.cli.commands.check_skills import _resolve_formats_to_check

        # Create args without format attribute or with None
        args = argparse.Namespace()
        formats = _resolve_formats_to_check(args)

        assert formats == ["copilot", "claude", "cursor", "cline"]

    def test_check_skills_loads_all_recipes(self, tmp_path, monkeypatch):
        """Test that check_skills loads all recipes."""
        from generator.cli.commands.check_skills import _load_all_recipes

        monkeypatch.setattr(
            "generator.cli.commands.check_skills.list_recipes",
            lambda base_dir: [{"name": "test-recipe"}],
        )
        monkeypatch.setattr(
            "generator.cli.commands.check_skills.load_recipe",
            lambda name, base_dir: {"name": name, "version": "1.0"},
        )

        recipes = _load_all_recipes()
        assert "test-recipe" in recipes

    def test_check_skills_handles_missing_skills_dir(self, tmp_path, monkeypatch):
        """Test check_skills when skills directory doesn't exist."""
        from generator.cli.commands.check_skills import _get_skills_base_dir

        # Non-existent path should return None
        result = _get_skills_base_dir("copilot", tmp_path / "nonexistent")
        assert result is None

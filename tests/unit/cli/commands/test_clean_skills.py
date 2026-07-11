"""Tests for clean_skills command."""

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


class TestCleanSkillsCommand:
    """Tests for clean_skills command."""

    def test_clean_skills_no_orphans(self, tmp_path, capsys, monkeypatch):
        """Test clean_skills when no orphans exist."""
        from generator.cli.commands.clean_skills import cmd_clean_skills

        args = create_mock_args()
        monkeypatch.setattr(
            "generator.cli.commands.clean_skills._scan_all_formats_for_orphans",
            lambda *a: ({}, 0, 0),
        )

        exit_code = cmd_clean_skills(args)
        assert exit_code == 0

        captured = capsys.readouterr()
        assert "No orphaned skills" in captured.out

    def test_clean_skills_with_orphans_cancelled(self, tmp_path, capsys, monkeypatch):
        """Test clean_skills cancelled by user."""
        from generator.cli.commands.clean_skills import cmd_clean_skills

        orphans = {
            "copilot": {
                "orphaned_directories": [tmp_path / "old-skill"],
                "orphaned_entries": ["missing-skill"],
            }
        }

        args = create_mock_args()
        monkeypatch.setattr(
            "generator.cli.commands.clean_skills._scan_all_formats_for_orphans",
            lambda *a: (orphans, 1, 1),
        )
        monkeypatch.setattr("builtins.input", lambda _: "no")

        exit_code = cmd_clean_skills(args)
        assert exit_code == 0

        captured = capsys.readouterr()
        assert "Cleanup cancelled" in captured.out

    def test_clean_skills_force_flag_skips_confirmation(self, tmp_path, monkeypatch):
        """Test clean_skills --force skips confirmation."""
        from generator.cli.commands.clean_skills import cmd_clean_skills

        orphans = {}

        args = create_mock_args(force=True)
        monkeypatch.setattr(
            "generator.cli.commands.clean_skills._scan_all_formats_for_orphans",
            lambda *a: (orphans, 0, 0),
        )
        monkeypatch.setattr(
            "generator.cli.commands.clean_skills._clean_all_orphans",
            lambda *a: (0, 0),  # Returns tuple of (dirs_removed, entries_removed)
        )

        # Should not prompt for input
        exit_code = cmd_clean_skills(args)
        assert exit_code == 0

    def test_clean_skills_specific_format(self, monkeypatch):
        """Test clean_skills with specific format."""
        from generator.cli.commands.clean_skills import _get_formats_to_clean

        args = create_mock_args(format="claude")
        formats = _get_formats_to_clean(args)

        assert formats == ["claude"]

    def test_clean_skills_all_formats(self, monkeypatch):
        """Test clean_skills defaults to all formats."""
        from generator.cli.commands.clean_skills import _get_formats_to_clean

        # Create args with format set to None (not missing)
        args = argparse.Namespace(format=None)
        formats = _get_formats_to_clean(args)

        assert formats == ["copilot", "claude", "cursor", "cline"]

    def test_clean_skills_whatif_mode(self, tmp_path, capsys, monkeypatch):
        """Test clean_skills in whatif mode."""
        from generator.cli.commands.clean_skills import cmd_clean_skills

        orphans = {}

        args = create_mock_args(whatif=True)
        monkeypatch.setattr(
            "generator.cli.commands.clean_skills._scan_all_formats_for_orphans",
            lambda *a: (orphans, 0, 0),
        )

        exit_code = cmd_clean_skills(args)
        assert exit_code == 0

        captured = capsys.readouterr()
        assert "No orphaned skills" in captured.out

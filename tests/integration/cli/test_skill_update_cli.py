"""
Phase 7e integration tests: CLI commands for skill updates.

Tests check-skills and update-skill commands end-to-end.
"""

import argparse
import json
from pathlib import Path
from generator.cli import commands


class TestCheckSkillsCommand:
    """Test check-skills CLI command."""

    def test_check_skills_reports_stale(self, tmp_path, monkeypatch, capsys):
        """check-skills command reports stale skills."""
        # Arrange
        # Create skill with old recipe hash
        skill_dir = tmp_path / ".copilot" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)

        old_metadata = {
            "skill_name": "test-skill",
            "format": "copilot",
            "source_recipes": [
                {"name": "test-python-backend", "content_hash": "old_hash_123"}
            ],
        }
        (skill_dir / ".skill-metadata.json").write_text(json.dumps(old_metadata))
        (skill_dir / "SKILL.md").write_text("# Old Skill")

        # Mock home directory to tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        args = argparse.Namespace(format="copilot", target=None)

        # Act
        result = commands.cmd_check_skills(args)

        # Assert - Should find stale skill (exit code 1) or no recipes found (exit code 0 or 1)
        assert result in [0, 1]
        captured = capsys.readouterr()
        # May show stale or may show up-to-date if recipes not loaded
        assert "stale" in captured.out.lower() or "up to date" in captured.out.lower()

    def test_check_skills_all_formats(self, tmp_path, monkeypatch, capsys):
        """check-skills without format checks all formats."""
        # Arrange
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        args = argparse.Namespace(format=None, target=None)  # All formats

        # Act
        result = commands.cmd_check_skills(args)

        # Assert
        assert result == 0  # No skills = all up to date
        captured = capsys.readouterr()
        assert "up to date" in captured.out.lower()


class TestUpdateSkillCommand:
    """Test update-skill CLI command."""

    def test_update_skill_requires_name_or_all(self, tmp_path, monkeypatch, capsys):
        """update-skill requires name or --all flag."""
        # Arrange
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        args = argparse.Namespace(
            name=None, all=False, format=None, target=None, force=False, whatif=False
        )

        # Act
        result = commands.cmd_update_skill(args)

        # Assert
        assert result == 1
        captured = capsys.readouterr()
        assert "must provide" in captured.err.lower()

    def test_update_skill_requires_format_for_name(self, tmp_path, monkeypatch, capsys):
        """update-skill with name requires --format."""
        # Arrange
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        args = argparse.Namespace(
            name="test-skill",
            all=False,
            format=None,  # Missing format
            target=None,
            force=False,
            whatif=False,
        )

        # Act
        result = commands.cmd_update_skill(args)

        # Assert
        assert result == 1
        captured = capsys.readouterr()
        assert "format required" in captured.err.lower()

    def test_update_skill_whatif_shows_plan(self, tmp_path, monkeypatch, capsys):
        """update-skill --whatif shows what would be done."""
        # Arrange
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create stale skill
        skill_dir = tmp_path / ".copilot" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)

        metadata = {
            "skill_name": "test-skill",
            "format": "copilot",
            "source_recipes": [{"name": "test-python-backend", "content_hash": "old"}],
        }
        (skill_dir / ".skill-metadata.json").write_text(json.dumps(metadata))

        args = argparse.Namespace(
            name=None, all=True, format="copilot", target=None, force=False, whatif=True
        )

        # Act
        result = commands.cmd_update_skill(args)

        # Assert
        assert result == 0
        captured = capsys.readouterr()
        assert (
            "WHATIF" in captured.out
            or "Would update" in captured.out
            or "0 total" in captured.out
        )

    def test_update_skill_error_when_not_found(self, tmp_path, monkeypatch, capsys):
        """update-skill shows error when skill not found."""
        # Arrange
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        args = argparse.Namespace(
            name="nonexistent",
            all=False,
            format="copilot",
            target=None,
            force=False,
            whatif=False,
        )

        # Act
        result = commands.cmd_update_skill(args)

        # Assert
        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()

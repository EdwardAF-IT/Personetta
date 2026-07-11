"""
Phase 7f: CLI Integration Tests

Integration tests for remove-skill and clean-skills CLI commands.
"""

import json
from unittest.mock import patch

import pytest

from generator.cli.commands import cmd_clean_skills, cmd_remove_skill
from generator.skill_catalog import update_catalog_entry


class TestRemoveSkillCommand:
    """Integration tests for remove-skill command."""

    @pytest.fixture
    def mock_args_copilot(self):
        """Mock args for remove-skill command."""

        class Args:
            skill_name = "python-testing"
            format = "copilot"
            force = False
            target = None

        return Args()

    def test_remove_skill_with_confirmation_yes(
        self, tmp_path, mock_args_copilot, monkeypatch
    ):
        """Remove skill when user confirms (y)."""
        # Arrange
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        copilot_dir = tmp_path / ".copilot" / "skills"
        copilot_dir.mkdir(parents=True)

        # Create skill directory
        skill_dir = copilot_dir / "python-testing"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Python Testing")

        # Create skill metadata (required for valid skill)
        metadata = {
            "skill_name": "python-testing",
            "generated_at": "2026-04-14T10:00:00Z",
            "personetta_version": "1.0.0",
            "format": "copilot",
            "source_recipes": [{"name": "test-python", "content_hash": "abc123"}],
        }
        (skill_dir / ".skill-metadata.json").write_text(json.dumps(metadata, indent=2))

        # Create catalog entry (without explicit path - uses monkeypatched home)
        update_catalog_entry("python-testing", "copilot", skill_dir)

        # Mock user input (yes)
        with patch("builtins.input", return_value="y"):
            # Act
            cmd_remove_skill(mock_args_copilot)

        # Assert - skill directory removed
        assert not skill_dir.exists()

        # Assert - catalog entry removed
        catalog_file = tmp_path / ".personetta" / "skills-catalog.json"
        catalog_data = json.loads(catalog_file.read_text())
        assert "python-testing" not in catalog_data["skills"].get("copilot", {})

    def test_remove_skill_with_confirmation_no(
        self, tmp_path, mock_args_copilot, monkeypatch
    ):
        """Don't remove skill when user declines (n)."""
        # Arrange
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        copilot_dir = tmp_path / ".copilot" / "skills"
        copilot_dir.mkdir(parents=True)

        skill_dir = copilot_dir / "python-testing"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Python Testing")

        # Create skill metadata (required for valid skill)
        metadata = {
            "skill_name": "python-testing",
            "generated_at": "2026-04-14T10:00:00Z",
            "personetta_version": "1.0.0",
            "format": "copilot",
            "source_recipes": [{"name": "test-python", "content_hash": "abc123"}],
        }
        (skill_dir / ".skill-metadata.json").write_text(json.dumps(metadata, indent=2))

        update_catalog_entry("python-testing", "copilot", skill_dir)

        # Mock user input (no)
        with patch("builtins.input", return_value="n"):
            # Act
            cmd_remove_skill(mock_args_copilot)

        # Assert - skill still exists
        assert skill_dir.exists()

        # Assert - catalog entry still exists
        catalog_file = tmp_path / ".personetta" / "skills-catalog.json"
        catalog_data = json.loads(catalog_file.read_text())
        assert "python-testing" in catalog_data["skills"]["copilot"]

    def test_remove_skill_with_force_flag(self, tmp_path, mock_args_copilot, monkeypatch):
        """Remove skill without confirmation when --force used."""
        # Arrange
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        copilot_dir = tmp_path / ".copilot" / "skills"
        copilot_dir.mkdir(parents=True)

        skill_dir = copilot_dir / "python-testing"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Python Testing")

        # Create skill metadata (required for valid skill)
        metadata = {
            "skill_name": "python-testing",
            "generated_at": "2026-04-14T10:00:00Z",
            "personetta_version": "1.0.0",
            "format": "copilot",
            "source_recipes": [{"name": "test-python", "content_hash": "abc123"}],
        }
        (skill_dir / ".skill-metadata.json").write_text(json.dumps(metadata, indent=2))

        update_catalog_entry("python-testing", "copilot", skill_dir)

        # Set force flag
        mock_args_copilot.force = True

        # Act (no input mock needed)
        cmd_remove_skill(mock_args_copilot)

        # Assert - skill removed without prompt
        assert not skill_dir.exists()

        # Assert - catalog entry removed
        catalog_file = tmp_path / ".personetta" / "skills-catalog.json"
        catalog_data = json.loads(catalog_file.read_text())
        assert "python-testing" not in catalog_data["skills"].get("copilot", {})

    def test_remove_nonexistent_skill(
        self, tmp_path, mock_args_copilot, monkeypatch, capsys
    ):
        """Removing nonexistent skill shows error."""
        # Arrange
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        copilot_dir = tmp_path / ".copilot" / "skills"
        copilot_dir.mkdir(parents=True)

        # Act
        cmd_remove_skill(mock_args_copilot)

        # Assert - error message printed to stderr
        captured = capsys.readouterr()
        assert (
            "not found" in captured.err.lower()
            or "does not exist" in captured.err.lower()
        )

    def test_remove_skill_directory_only(self, tmp_path, mock_args_copilot, monkeypatch):
        """Remove skill that exists as directory but not in catalog."""
        # Arrange
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        copilot_dir = tmp_path / ".copilot" / "skills"
        copilot_dir.mkdir(parents=True)

        skill_dir = copilot_dir / "python-testing"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Python Testing")

        # No catalog entry created

        mock_args_copilot.force = True

        # Act
        cmd_remove_skill(mock_args_copilot)

        # Assert - directory removed even without catalog entry
        assert not skill_dir.exists()

    def test_remove_skill_catalog_only(self, tmp_path, mock_args_copilot, monkeypatch):
        """Remove skill that exists in catalog but directory missing."""
        # Arrange
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        copilot_dir = tmp_path / ".copilot" / "skills"
        copilot_dir.mkdir(parents=True)

        # Create catalog entry without directory
        catalog_file = tmp_path / ".personetta" / "skills-catalog.json"
        catalog_file.parent.mkdir(parents=True, exist_ok=True)
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {
                "copilot": {
                    "python-testing": {
                        "name": "python-testing",
                        "path": str(copilot_dir / "python-testing"),
                    }
                }
            },
        }
        catalog_file.write_text(json.dumps(catalog_data, indent=2))

        mock_args_copilot.force = True

        # Act
        cmd_remove_skill(mock_args_copilot)

        # Assert - catalog entry removed
        updated_catalog = json.loads(catalog_file.read_text())
        assert "python-testing" not in updated_catalog["skills"].get("copilot", {})


class TestCleanSkillsCommand:
    """Integration tests for clean-skills command."""

    @pytest.fixture
    def mock_args(self):
        """Mock args for clean-skills command."""

        class Args:
            format = None  # None means all formats
            force = False

        return Args()

    def test_clean_skills_all_formats(self, tmp_path, mock_args, monkeypatch):
        """Clean orphaned skills across all formats."""
        # Arrange
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        # Create orphaned Copilot skill
        copilot_dir = tmp_path / ".copilot" / "skills"
        copilot_dir.mkdir(parents=True)
        orphaned_copilot = copilot_dir / "orphaned-copilot"
        orphaned_copilot.mkdir()
        (orphaned_copilot / "SKILL.md").write_text("# Test")

        # Create orphaned Claude skill
        claude_dir = tmp_path / ".claude" / "skills"
        claude_dir.mkdir(parents=True)
        orphaned_claude = claude_dir / "orphaned-claude"
        orphaned_claude.mkdir()
        (orphaned_claude / "SKILL.md").write_text("# Test")

        # Create catalogs without these skills
        catalog_file = tmp_path / ".personetta" / "skills-catalog.json"
        catalog_file.parent.mkdir(parents=True, exist_ok=True)
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {"copilot": {}, "claude": {}},
        }
        catalog_file.write_text(json.dumps(catalog_data, indent=2))

        mock_args.force = True

        # Act
        cmd_clean_skills(mock_args)

        # Assert - both orphaned directories removed
        assert not orphaned_copilot.exists()
        assert not orphaned_claude.exists()

    def test_clean_skills_specific_format(self, tmp_path, mock_args, monkeypatch):
        """Clean orphaned skills for specific format only."""
        # Arrange
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        copilot_dir = tmp_path / ".copilot" / "skills"
        copilot_dir.mkdir(parents=True)
        orphaned_copilot = copilot_dir / "orphaned-copilot"
        orphaned_copilot.mkdir()
        (orphaned_copilot / "SKILL.md").write_text("# Test")

        claude_dir = tmp_path / ".claude" / "skills"
        claude_dir.mkdir(parents=True)
        orphaned_claude = claude_dir / "orphaned-claude"
        orphaned_claude.mkdir()
        (orphaned_claude / "SKILL.md").write_text("# Test")

        # Create empty catalogs
        catalog_file = tmp_path / ".personetta" / "skills-catalog.json"
        catalog_file.parent.mkdir(parents=True, exist_ok=True)
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {"copilot": {}, "claude": {}},
        }
        catalog_file.write_text(json.dumps(catalog_data, indent=2))

        mock_args.format = "copilot"
        mock_args.force = True

        # Act
        cmd_clean_skills(mock_args)

        # Assert - only Copilot orphan removed
        assert not orphaned_copilot.exists()
        assert orphaned_claude.exists()  # Claude orphan untouched

    def test_clean_skills_with_confirmation(self, tmp_path, mock_args, monkeypatch):
        """Clean shows preview and requires confirmation."""
        # Arrange
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        copilot_dir = tmp_path / ".copilot" / "skills"
        copilot_dir.mkdir(parents=True)
        orphaned = copilot_dir / "orphaned-skill"
        orphaned.mkdir()
        (orphaned / "SKILL.md").write_text("# Test")

        catalog_file = tmp_path / ".personetta" / "skills-catalog.json"
        catalog_file.parent.mkdir(parents=True, exist_ok=True)
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {"copilot": {}},
        }
        catalog_file.write_text(json.dumps(catalog_data, indent=2))

        mock_args.format = "copilot"

        # Mock user confirmation (yes)
        with patch("builtins.input", return_value="y"):
            # Act
            cmd_clean_skills(mock_args)

        # Assert - orphan removed
        assert not orphaned.exists()

    def test_clean_skills_decline_confirmation(self, tmp_path, mock_args, monkeypatch):
        """Clean aborts when user declines."""
        # Arrange
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        copilot_dir = tmp_path / ".copilot" / "skills"
        copilot_dir.mkdir(parents=True)
        orphaned = copilot_dir / "orphaned-skill"
        orphaned.mkdir()
        (orphaned / "SKILL.md").write_text("# Test")

        catalog_file = tmp_path / ".personetta" / "skills-catalog.json"
        catalog_file.parent.mkdir(parents=True, exist_ok=True)
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {"copilot": {}},
        }
        catalog_file.write_text(json.dumps(catalog_data, indent=2))

        mock_args.format = "copilot"

        # Mock user decline (no)
        with patch("builtins.input", return_value="n"):
            # Act
            cmd_clean_skills(mock_args)

        # Assert - orphan still exists
        assert orphaned.exists()

    def test_clean_skills_no_orphans(self, tmp_path, mock_args, monkeypatch, capsys):
        """Clean reports when no orphans found."""
        # Arrange
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        copilot_dir = tmp_path / ".copilot" / "skills"
        copilot_dir.mkdir(parents=True)

        catalog_file = tmp_path / ".personetta" / "skills-catalog.json"
        catalog_file.parent.mkdir(parents=True, exist_ok=True)
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {"copilot": {}},
        }
        catalog_file.write_text(json.dumps(catalog_data, indent=2))

        mock_args.format = "copilot"
        mock_args.force = True

        # Act
        cmd_clean_skills(mock_args)

        # Assert - message about no orphans
        captured = capsys.readouterr()
        assert (
            "no orphaned" in captured.out.lower()
            or "nothing to clean" in captured.out.lower()
        )

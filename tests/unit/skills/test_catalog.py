"""
Tests for Phase 7f: Skill Management Commands

Tests for remove-skill and clean-skills commands.
"""

import json
from unittest.mock import Mock, patch
import pytest

from generator.skill_catalog import (
    remove_catalog_entry,
    clean_orphaned_entries,
)

pytestmark = [pytest.mark.unit, pytest.mark.skills]


class TestRemoveCatalogEntry:
    """Test removing entries from catalog."""

    def test_remove_existing_entry(self, tmp_path):
        """Remove entry from catalog when skill exists."""
        # Arrange
        catalog_path = tmp_path / "skills-catalog.json"
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {
                "copilot": {
                    "python-testing": {
                        "name": "python-testing",
                        "description": "Test skill",
                        "path": str(tmp_path / "python-testing"),
                    },
                    "python-review": {
                        "name": "python-review",
                        "description": "Review skill",
                        "path": str(tmp_path / "python-review"),
                    },
                }
            },
        }
        catalog_path.write_text(json.dumps(catalog_data, indent=2))

        # Act
        remove_catalog_entry("python-testing", "copilot", catalog_path)

        # Assert
        result = json.loads(catalog_path.read_text())
        assert "python-testing" not in result["skills"]["copilot"]
        assert "python-review" in result["skills"]["copilot"]

    def test_remove_nonexistent_entry(self, tmp_path):
        """Removing non-existent entry doesn't error."""
        # Arrange
        catalog_path = tmp_path / "skills-catalog.json"
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {"copilot": {}},
        }
        catalog_path.write_text(json.dumps(catalog_data, indent=2))

        # Act - should not raise
        remove_catalog_entry("nonexistent", "copilot", catalog_path)

        # Assert
        result = json.loads(catalog_path.read_text())
        assert result["skills"]["copilot"] == {}

    def test_remove_last_entry_keeps_format_key(self, tmp_path):
        """Removing last entry keeps format key in catalog."""
        # Arrange
        catalog_path = tmp_path / "skills-catalog.json"
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {
                "copilot": {
                    "python-testing": {
                        "name": "python-testing",
                        "description": "Test skill",
                        "path": str(tmp_path / "python-testing"),
                    }
                }
            },
        }
        catalog_path.write_text(json.dumps(catalog_data, indent=2))

        # Act
        remove_catalog_entry("python-testing", "copilot", catalog_path)

        # Assert
        result = json.loads(catalog_path.read_text())
        assert "copilot" in result["skills"]
        assert result["skills"]["copilot"] == {}

    def test_remove_updates_timestamp(self, tmp_path):
        """Removing entry updates last_updated timestamp."""
        # Arrange
        catalog_path = tmp_path / "skills-catalog.json"
        old_time = "2026-04-14T10:00:00Z"
        catalog_data = {
            "version": "1.0",
            "last_updated": old_time,
            "skills": {
                "copilot": {
                    "python-testing": {
                        "name": "python-testing",
                        "description": "Test skill",
                        "path": str(tmp_path / "python-testing"),
                    }
                }
            },
        }
        catalog_path.write_text(json.dumps(catalog_data, indent=2))

        # Act
        remove_catalog_entry("python-testing", "copilot", catalog_path)

        # Assert
        result = json.loads(catalog_path.read_text())
        assert result["last_updated"] != old_time


class TestCleanOrphanedEntries:
    """Test cleaning orphaned catalog entries."""

    def test_clean_removes_orphaned_entries(self, tmp_path):
        """Clean removes entries where skill directory doesn't exist."""
        # Arrange
        catalog_path = tmp_path / "skills-catalog.json"
        existing_skill_dir = tmp_path / "python-testing"
        existing_skill_dir.mkdir(parents=True)

        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {
                "copilot": {
                    "python-testing": {
                        "name": "python-testing",
                        "description": "Test skill",
                        "path": str(existing_skill_dir),
                    },
                    "orphaned-skill": {
                        "name": "orphaned-skill",
                        "description": "Missing directory",
                        "path": str(tmp_path / "orphaned-skill"),
                    },
                }
            },
        }
        catalog_path.write_text(json.dumps(catalog_data, indent=2))

        # Act
        removed = clean_orphaned_entries("copilot", catalog_path)

        # Assert
        assert len(removed) == 1
        assert removed[0] == "orphaned-skill"

        result = json.loads(catalog_path.read_text())
        assert "python-testing" in result["skills"]["copilot"]
        assert "orphaned-skill" not in result["skills"]["copilot"]

    def test_clean_with_no_orphans(self, tmp_path):
        """Clean with no orphaned entries returns empty list."""
        # Arrange
        catalog_path = tmp_path / "skills-catalog.json"
        skill_dir = tmp_path / "python-testing"
        skill_dir.mkdir(parents=True)

        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {
                "copilot": {
                    "python-testing": {
                        "name": "python-testing",
                        "description": "Test skill",
                        "path": str(skill_dir),
                    }
                }
            },
        }
        catalog_path.write_text(json.dumps(catalog_data, indent=2))

        # Act
        removed = clean_orphaned_entries("copilot", catalog_path)

        # Assert
        assert removed == []

        result = json.loads(catalog_path.read_text())
        assert "python-testing" in result["skills"]["copilot"]

    def test_clean_multiple_orphans(self, tmp_path):
        """Clean removes multiple orphaned entries."""
        # Arrange
        catalog_path = tmp_path / "skills-catalog.json"
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {
                "copilot": {
                    "orphan1": {
                        "name": "orphan1",
                        "path": str(tmp_path / "orphan1"),
                    },
                    "orphan2": {
                        "name": "orphan2",
                        "path": str(tmp_path / "orphan2"),
                    },
                }
            },
        }
        catalog_path.write_text(json.dumps(catalog_data, indent=2))

        # Act
        removed = clean_orphaned_entries("copilot", catalog_path)

        # Assert
        assert len(removed) == 2
        assert "orphan1" in removed
        assert "orphan2" in removed

        result = json.loads(catalog_path.read_text())
        assert result["skills"]["copilot"] == {}


class TestRemoveSkillCommand:
    """Test remove-skill command integration."""

    def test_remove_skill_deletes_directory(self, tmp_path):
        """remove-skill deletes skill directory."""
        # Arrange
        from generator.cli.commands import cmd_remove_skill

        skill_dir = tmp_path / "python-testing"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Test Skill")

        catalog_path = tmp_path / "skills-catalog.json"
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {
                "copilot": {
                    "python-testing": {
                        "name": "python-testing",
                        "path": str(skill_dir),
                    }
                }
            },
        }
        catalog_path.write_text(json.dumps(catalog_data, indent=2))

        args = Mock()
        args.skill_name = "python-testing"
        args.format = "copilot"
        args.force = True

        # Act
        with patch("generator.skill_catalog.get_catalog_path", return_value=catalog_path):
            with patch("generator.paths.get_skill_install_path", return_value=skill_dir):
                cmd_remove_skill(args)

        # Assert
        assert not skill_dir.exists()

        result = json.loads(catalog_path.read_text())
        assert "python-testing" not in result["skills"]["copilot"]

    def test_remove_skill_with_confirmation_yes(self, tmp_path):
        """remove-skill with user confirmation 'yes' removes skill."""
        # Arrange
        from generator.cli.commands import cmd_remove_skill

        skill_dir = tmp_path / "python-testing"
        skill_dir.mkdir(parents=True)

        catalog_path = tmp_path / "skills-catalog.json"
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {"copilot": {"python-testing": {"path": str(skill_dir)}}},
        }
        catalog_path.write_text(json.dumps(catalog_data, indent=2))

        args = Mock()
        args.skill_name = "python-testing"
        args.format = "copilot"
        args.force = False

        # Act
        with patch("generator.skill_catalog.get_catalog_path", return_value=catalog_path):
            with patch("generator.paths.get_skill_install_path", return_value=skill_dir):
                with patch("builtins.input", return_value="yes"):
                    cmd_remove_skill(args)

        # Assert
        assert not skill_dir.exists()

    def test_remove_skill_with_confirmation_no(self, tmp_path):
        """remove-skill with user confirmation 'no' keeps skill."""
        # Arrange
        from generator.cli.commands import cmd_remove_skill

        skill_dir = tmp_path / "python-testing"
        skill_dir.mkdir(parents=True)

        catalog_path = tmp_path / "skills-catalog.json"
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {"copilot": {"python-testing": {"path": str(skill_dir)}}},
        }
        catalog_path.write_text(json.dumps(catalog_data, indent=2))

        args = Mock()
        args.skill_name = "python-testing"
        args.format = "copilot"
        args.force = False

        # Act
        with patch("generator.skill_catalog.get_catalog_path", return_value=catalog_path):
            with patch("generator.paths.get_skill_install_path", return_value=skill_dir):
                with patch("builtins.input", return_value="no"):
                    result = cmd_remove_skill(args)

        # Assert
        assert result == 0  # Returns 0 for cancelled
        assert skill_dir.exists()

    def test_remove_nonexistent_skill(self, tmp_path):
        """remove-skill for non-existent skill shows error."""
        # Arrange
        from generator.cli.commands import cmd_remove_skill

        catalog_path = tmp_path / "skills-catalog.json"
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {"copilot": {}},
        }
        catalog_path.write_text(json.dumps(catalog_data, indent=2))

        args = Mock()
        args.skill_name = "nonexistent"
        args.format = "copilot"
        args.force = True

        # Act
        with patch("generator.skill_catalog.get_catalog_path", return_value=catalog_path):
            with patch(
                "generator.paths.get_skill_install_path",
                return_value=tmp_path / "nonexistent",
            ):
                result = cmd_remove_skill(args)

        # Assert
        assert result == 1


class TestCleanSkillsCommand:
    """Test clean-skills command integration."""

    def test_clean_skills_removes_orphans(self, tmp_path):
        """clean-skills removes orphaned entries from catalog."""
        # Arrange
        from generator.cli.commands import cmd_clean_skills

        catalog_path = tmp_path / "skills-catalog.json"
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {
                "copilot": {
                    "orphan1": {"path": str(tmp_path / "orphan1")},
                    "orphan2": {"path": str(tmp_path / "orphan2")},
                }
            },
        }
        catalog_path.write_text(json.dumps(catalog_data, indent=2))

        args = Mock()
        args.format = "copilot"
        args.force = True

        # Act
        with patch("generator.skill_catalog.get_catalog_path", return_value=catalog_path):
            with patch("generator.skill_catalog._get_skills_dir", return_value=tmp_path):
                cmd_clean_skills(args)

        # Assert
        result = json.loads(catalog_path.read_text())
        assert result["skills"]["copilot"] == {}

    def test_clean_skills_with_no_orphans(self, tmp_path):
        """clean-skills with no orphans shows message."""
        # Arrange
        from generator.cli.commands import cmd_clean_skills

        skill_dir = tmp_path / "python-testing"
        skill_dir.mkdir(parents=True)

        catalog_path = tmp_path / "skills-catalog.json"
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {
                "copilot": {
                    "python-testing": {"path": str(skill_dir)},
                }
            },
        }
        catalog_path.write_text(json.dumps(catalog_data, indent=2))

        args = Mock()
        args.format = "copilot"
        args.force = True

        # Act
        with patch("generator.skill_catalog.get_catalog_path", return_value=catalog_path):
            with patch("generator.skill_catalog._get_skills_dir", return_value=tmp_path):
                cmd_clean_skills(args)

        # Assert - catalog unchanged
        result = json.loads(catalog_path.read_text())
        assert "python-testing" in result["skills"]["copilot"]

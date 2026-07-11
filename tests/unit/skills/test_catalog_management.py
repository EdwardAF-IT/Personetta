"""
Phase 7f: Skill Management Commands Tests

Tests for remove-skill and clean-skills commands.
"""

import json


from generator.skill_catalog import (
    clean_orphaned_skills,
    remove_skill_from_catalog,
    scan_for_orphans,
)


class TestRemoveSkillFromCatalog:
    """Test removing skill entries from catalog."""

    def test_remove_existing_skill(self, tmp_path):
        """Remove existing skill entry from catalog."""
        # Arrange
        catalog_file = tmp_path / ".personetta" / "skills-catalog.json"
        catalog_file.parent.mkdir(parents=True, exist_ok=True)
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
                    "code-review": {
                        "name": "code-review",
                        "description": "Review skill",
                        "path": str(tmp_path / "code-review"),
                    },
                }
            },
        }
        catalog_file.write_text(json.dumps(catalog_data, indent=2))

        # Act
        result = remove_skill_from_catalog("python-testing", "copilot", tmp_path)

        # Assert
        assert result is True
        updated_catalog = json.loads(catalog_file.read_text())
        assert "python-testing" not in updated_catalog["skills"]["copilot"]
        assert "code-review" in updated_catalog["skills"]["copilot"]

    def test_remove_nonexistent_skill(self, tmp_path):
        """Removing nonexistent skill returns False."""
        # Arrange
        catalog_file = tmp_path / ".personetta" / "skills-catalog.json"
        catalog_file.parent.mkdir(parents=True, exist_ok=True)
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {"copilot": {}},
        }
        catalog_file.write_text(json.dumps(catalog_data, indent=2))

        # Act
        result = remove_skill_from_catalog("nonexistent", "copilot", tmp_path)

        # Assert
        assert result is False

    def test_remove_skill_missing_format(self, tmp_path):
        """Removing skill from missing format returns False."""
        # Arrange
        catalog_file = tmp_path / ".personetta" / "skills-catalog.json"
        catalog_file.parent.mkdir(parents=True, exist_ok=True)
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {"copilot": {"python-testing": {"name": "python-testing"}}},
        }
        catalog_file.write_text(json.dumps(catalog_data, indent=2))

        # Act
        result = remove_skill_from_catalog("python-testing", "claude", tmp_path)

        # Assert
        assert result is False

    def test_remove_skill_empty_catalog(self, tmp_path):
        """Removing from empty catalog returns False."""
        # Arrange
        catalog_file = tmp_path / ".personetta" / "skills-catalog.json"
        catalog_file.parent.mkdir(parents=True, exist_ok=True)
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {},
        }
        catalog_file.write_text(json.dumps(catalog_data, indent=2))

        # Act
        result = remove_skill_from_catalog("python-testing", "copilot", tmp_path)

        # Assert
        assert result is False

    def test_remove_skill_no_catalog_file(self, tmp_path):
        """Removing when catalog doesn't exist returns False."""
        # Act
        result = remove_skill_from_catalog("python-testing", "copilot", tmp_path)

        # Assert
        assert result is False


class TestScanForOrphans:
    """Test scanning for orphaned skills and catalog entries."""

    def test_scan_finds_orphaned_directory(self, tmp_path):
        """Scan detects skill directory without catalog entry."""
        # Arrange
        copilot_dir = tmp_path / ".copilot" / "skills"
        copilot_dir.mkdir(parents=True)

        # Create skill directory without catalog entry
        skill_dir = copilot_dir / "orphaned-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Test")

        catalog_file = tmp_path / "skills-catalog.json"
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {"copilot": {}},
        }
        catalog_file.write_text(json.dumps(catalog_data, indent=2))

        # Act
        orphans = scan_for_orphans("copilot", tmp_path, copilot_dir)

        # Assert
        assert len(orphans["orphaned_directories"]) == 1
        assert orphans["orphaned_directories"][0].name == "orphaned-skill"
        assert len(orphans["orphaned_entries"]) == 0

    def test_scan_finds_orphaned_catalog_entry(self, tmp_path):
        """Scan detects catalog entry without skill directory."""
        # Arrange
        copilot_dir = tmp_path / ".copilot" / "skills"
        copilot_dir.mkdir(parents=True)

        catalog_file = tmp_path / ".personetta" / "skills-catalog.json"
        catalog_file.parent.mkdir(parents=True, exist_ok=True)
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {
                "copilot": {
                    "missing-skill": {
                        "name": "missing-skill",
                        "path": str(copilot_dir / "missing-skill"),
                    }
                }
            },
        }
        catalog_file.write_text(json.dumps(catalog_data, indent=2))

        # Act
        orphans = scan_for_orphans("copilot", tmp_path, copilot_dir)

        # Assert
        assert len(orphans["orphaned_directories"]) == 0
        assert len(orphans["orphaned_entries"]) == 1
        assert orphans["orphaned_entries"][0] == "missing-skill"

    def test_scan_finds_both_types_of_orphans(self, tmp_path):
        """Scan detects both orphaned directories and entries."""
        # Arrange
        copilot_dir = tmp_path / ".copilot" / "skills"
        copilot_dir.mkdir(parents=True)

        # Orphaned directory
        orphaned_dir = copilot_dir / "orphaned-dir"
        orphaned_dir.mkdir()
        (orphaned_dir / "SKILL.md").write_text("# Test")

        catalog_file = tmp_path / ".personetta" / "skills-catalog.json"
        catalog_file.parent.mkdir(parents=True, exist_ok=True)
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {
                "copilot": {
                    "orphaned-entry": {
                        "name": "orphaned-entry",
                        "path": str(copilot_dir / "orphaned-entry"),
                    }
                }
            },
        }
        catalog_file.write_text(json.dumps(catalog_data, indent=2))

        # Act
        orphans = scan_for_orphans("copilot", tmp_path, copilot_dir)

        # Assert
        assert len(orphans["orphaned_directories"]) == 1
        assert len(orphans["orphaned_entries"]) == 1

    def test_scan_finds_no_orphans(self, tmp_path):
        """Scan returns empty when everything is synced."""
        # Arrange
        copilot_dir = tmp_path / ".copilot" / "skills"
        copilot_dir.mkdir(parents=True)

        # Valid skill with matching catalog entry
        skill_dir = copilot_dir / "valid-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Test")

        catalog_file = tmp_path / ".personetta" / "skills-catalog.json"
        catalog_file.parent.mkdir(parents=True, exist_ok=True)
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {
                "copilot": {
                    "valid-skill": {
                        "name": "valid-skill",
                        "path": str(skill_dir),
                    }
                }
            },
        }
        catalog_file.write_text(json.dumps(catalog_data, indent=2))

        # Act
        orphans = scan_for_orphans("copilot", tmp_path, copilot_dir)

        # Assert
        assert len(orphans["orphaned_directories"]) == 0
        assert len(orphans["orphaned_entries"]) == 0

    def test_scan_skips_non_skill_directories(self, tmp_path):
        """Scan ignores directories without SKILL.md."""
        # Arrange
        copilot_dir = tmp_path / ".copilot" / "skills"
        copilot_dir.mkdir(parents=True)

        # Not a skill (no SKILL.md)
        not_skill = copilot_dir / "not-a-skill"
        not_skill.mkdir()
        (not_skill / "README.md").write_text("# Not a skill")

        catalog_file = tmp_path / ".personetta" / "skills-catalog.json"
        catalog_file.parent.mkdir(parents=True, exist_ok=True)
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {"copilot": {}},
        }
        catalog_file.write_text(json.dumps(catalog_data, indent=2))

        # Act
        orphans = scan_for_orphans("copilot", tmp_path, copilot_dir)

        # Assert
        assert len(orphans["orphaned_directories"]) == 0


class TestCleanOrphanedSkills:
    """Test cleaning orphaned skills."""

    def test_clean_removes_orphaned_directory(self, tmp_path):
        """Clean removes orphaned skill directory."""
        # Arrange
        copilot_dir = tmp_path / ".copilot" / "skills"
        copilot_dir.mkdir(parents=True)

        orphaned_dir = copilot_dir / "orphaned-skill"
        orphaned_dir.mkdir()
        (orphaned_dir / "SKILL.md").write_text("# Test")

        catalog_file = tmp_path / ".personetta" / "skills-catalog.json"
        catalog_file.parent.mkdir(parents=True, exist_ok=True)
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {"copilot": {}},
        }
        catalog_file.write_text(json.dumps(catalog_data, indent=2))

        # Act
        result = clean_orphaned_skills("copilot", tmp_path, copilot_dir)

        # Assert
        assert result["directories_removed"] == 1
        assert result["entries_removed"] == 0
        assert not orphaned_dir.exists()

    def test_clean_removes_orphaned_entry(self, tmp_path):
        """Clean removes orphaned catalog entry."""
        # Arrange
        copilot_dir = tmp_path / ".copilot" / "skills"
        copilot_dir.mkdir(parents=True)

        catalog_file = tmp_path / ".personetta" / "skills-catalog.json"
        catalog_file.parent.mkdir(parents=True, exist_ok=True)
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {
                "copilot": {
                    "orphaned-entry": {
                        "name": "orphaned-entry",
                        "path": str(copilot_dir / "orphaned-entry"),
                    }
                }
            },
        }
        catalog_file.write_text(json.dumps(catalog_data, indent=2))

        # Act
        result = clean_orphaned_skills("copilot", tmp_path, copilot_dir)

        # Assert
        assert result["directories_removed"] == 0
        assert result["entries_removed"] == 1
        updated_catalog = json.loads(catalog_file.read_text())
        assert "orphaned-entry" not in updated_catalog["skills"]["copilot"]

    def test_clean_removes_both_types(self, tmp_path):
        """Clean removes both orphaned directories and entries."""
        # Arrange
        copilot_dir = tmp_path / ".copilot" / "skills"
        copilot_dir.mkdir(parents=True)

        orphaned_dir = copilot_dir / "orphaned-dir"
        orphaned_dir.mkdir()
        (orphaned_dir / "SKILL.md").write_text("# Test")

        catalog_file = tmp_path / ".personetta" / "skills-catalog.json"
        catalog_file.parent.mkdir(parents=True, exist_ok=True)
        catalog_data = {
            "version": "1.0",
            "last_updated": "2026-04-14T10:00:00Z",
            "skills": {
                "copilot": {
                    "orphaned-entry": {
                        "name": "orphaned-entry",
                        "path": str(copilot_dir / "orphaned-entry"),
                    }
                }
            },
        }
        catalog_file.write_text(json.dumps(catalog_data, indent=2))

        # Act
        result = clean_orphaned_skills("copilot", tmp_path, copilot_dir)

        # Assert
        assert result["directories_removed"] == 1
        assert result["entries_removed"] == 1

    def test_clean_with_no_orphans(self, tmp_path):
        """Clean reports zero when nothing to clean."""
        # Arrange
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

        # Act
        result = clean_orphaned_skills("copilot", tmp_path, copilot_dir)

        # Assert
        assert result["directories_removed"] == 0
        assert result["entries_removed"] == 0

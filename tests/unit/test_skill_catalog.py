"""Tests for skill catalog management.

Tests catalog operations including updates, deletions, and queries.

Following TDD approach: write tests first, then implement.
Tests for:
- Catalog creation and structure
- Catalog entry updates
- Skill directory scanning
- List-skills command
- Catalog refresh
- Error handling for missing/invalid entries
"""

from __future__ import annotations

import json
import pytest
from datetime import datetime
from generator.skill_catalog import (
    create_catalog,
    update_catalog_entry,
    scan_all_skills,
    get_catalog_path,
    load_catalog,
    save_catalog,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def empty_catalog_dir(tmp_path):
    """Empty directory for catalog testing."""
    catalog_dir = tmp_path / ".personetta"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    return catalog_dir


@pytest.fixture
def sample_skill_dir(tmp_path):
    """Sample skill directory with metadata."""
    skill_dir = tmp_path / ".copilot" / "skills" / "python-testing"
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Create metadata file
    metadata = {
        "skill_name": "python-testing",
        "generated_at": "2026-04-14T15:30:00Z",
        "personetta_version": "1.0.0",
        "format": "copilot",
        "source_recipes": [
            {
                "name": "test-python-backend",
                "file_path": "recipes/test-python-backend.yaml",
                "content_hash": "sha256:abc123",
                "file_mtime": "2026-04-10T12:00:00Z",
            }
        ],
    }

    metadata_file = skill_dir / ".skill-metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    # Create some skill files
    (skill_dir / "SKILL.md").write_text("# Python Testing\n\nTest skill")
    (skill_dir / "README.md").write_text("# README\n\nUsage guide")

    # Create scripts directory with files
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "run-pytest.sh").write_text("#!/bin/bash\npytest")
    (scripts_dir / "run-pytest.ps1").write_text("pytest")
    (scripts_dir / "run-ruff.sh").write_text("#!/bin/bash\nruff")

    return skill_dir


# ============================================================================
# Catalog Creation Tests
# ============================================================================


class TestCatalogCreation:
    """Test catalog structure and creation."""

    def test_create_catalog_returns_valid_structure(self):
        """create_catalog returns catalog with all required fields."""
        catalog = create_catalog()

        assert "version" in catalog
        assert catalog["version"] == "1.0"
        assert "last_updated" in catalog
        assert "skills" in catalog
        assert isinstance(catalog["skills"], dict)

    def test_create_catalog_has_timestamp(self):
        """Catalog includes ISO 8601 timestamp."""
        catalog = create_catalog()

        timestamp = catalog["last_updated"]
        # Should be ISO 8601 format with timezone
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    def test_create_catalog_initializes_empty_skills(self):
        """New catalog has empty skills dict."""
        catalog = create_catalog()

        assert catalog["skills"] == {}


# ============================================================================
# Catalog Path Resolution Tests
# ============================================================================


class TestCatalogPathResolution:
    """Test catalog file path resolution."""

    def test_get_catalog_path_default_location(self):
        """get_catalog_path returns ~/.personetta/skills-catalog.json."""
        path = get_catalog_path()

        assert path.name == "skills-catalog.json"
        assert ".personetta" in str(path)

    def test_get_catalog_path_custom_location(self, tmp_path):
        """get_catalog_path accepts custom directory."""
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()

        path = get_catalog_path(base_dir=custom_dir)

        assert path.parent == custom_dir / ".personetta"
        assert path.name == "skills-catalog.json"


# ============================================================================
# Catalog Load/Save Tests
# ============================================================================


class TestCatalogLoadSave:
    """Test catalog persistence."""

    def test_save_catalog_creates_file(self, empty_catalog_dir):
        """save_catalog creates JSON file."""
        catalog = create_catalog()
        catalog_path = empty_catalog_dir / "skills-catalog.json"

        save_catalog(catalog, catalog_path)

        assert catalog_path.exists()
        assert catalog_path.is_file()

    def test_save_catalog_writes_valid_json(self, empty_catalog_dir):
        """Saved catalog is valid JSON."""
        catalog = create_catalog()
        catalog_path = empty_catalog_dir / "skills-catalog.json"

        save_catalog(catalog, catalog_path)

        # Should be parseable
        with open(catalog_path, encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded == catalog

    def test_load_catalog_reads_existing_file(self, empty_catalog_dir):
        """load_catalog reads existing catalog."""
        catalog = create_catalog()
        catalog["skills"]["copilot"] = {"test": {}}
        catalog_path = empty_catalog_dir / "skills-catalog.json"

        save_catalog(catalog, catalog_path)
        loaded = load_catalog(catalog_path)

        assert loaded == catalog
        assert "copilot" in loaded["skills"]

    def test_load_catalog_creates_new_if_missing(self, empty_catalog_dir):
        """load_catalog creates new catalog if file doesn't exist."""
        catalog_path = empty_catalog_dir / "skills-catalog.json"

        loaded = load_catalog(catalog_path)

        assert "version" in loaded
        assert loaded["skills"] == {}

    def test_load_catalog_handles_corrupt_file(self, empty_catalog_dir):
        """load_catalog creates new catalog if file is corrupt."""
        catalog_path = empty_catalog_dir / "skills-catalog.json"
        catalog_path.write_text("{ invalid json }")

        loaded = load_catalog(catalog_path)

        # Should return new catalog, not crash
        assert "version" in loaded
        assert loaded["skills"] == {}


# ============================================================================
# Catalog Entry Update Tests
# ============================================================================


class TestCatalogEntryUpdate:
    """Test updating individual catalog entries."""

    def test_update_catalog_entry_adds_new_skill(
        self, sample_skill_dir, empty_catalog_dir
    ):
        """update_catalog_entry adds new skill to catalog."""
        catalog_path = empty_catalog_dir / "skills-catalog.json"
        catalog = create_catalog()
        save_catalog(catalog, catalog_path)

        update_catalog_entry("python-testing", "copilot", sample_skill_dir, catalog_path)

        updated = load_catalog(catalog_path)
        assert "copilot" in updated["skills"]
        assert "python-testing" in updated["skills"]["copilot"]

    def test_update_catalog_entry_includes_metadata(
        self, sample_skill_dir, empty_catalog_dir
    ):
        """Catalog entry includes all metadata fields."""
        catalog_path = empty_catalog_dir / "skills-catalog.json"
        catalog = create_catalog()
        save_catalog(catalog, catalog_path)

        update_catalog_entry("python-testing", "copilot", sample_skill_dir, catalog_path)

        updated = load_catalog(catalog_path)
        entry = updated["skills"]["copilot"]["python-testing"]

        assert entry["name"] == "python-testing"
        assert "description" in entry
        assert entry["path"] == str(sample_skill_dir)
        assert entry["source_recipes"] == ["test-python-backend"]
        assert entry["generated_at"] == "2026-04-14T15:30:00Z"

    def test_update_catalog_entry_counts_scripts(
        self, sample_skill_dir, empty_catalog_dir
    ):
        """Catalog entry counts script files."""
        catalog_path = empty_catalog_dir / "skills-catalog.json"
        catalog = create_catalog()
        save_catalog(catalog, catalog_path)

        update_catalog_entry("python-testing", "copilot", sample_skill_dir, catalog_path)

        updated = load_catalog(catalog_path)
        entry = updated["skills"]["copilot"]["python-testing"]

        assert entry["has_scripts"] is True
        assert entry["script_count"] == 3  # .sh and .ps1 files

    def test_update_catalog_entry_detects_no_scripts(self, tmp_path, empty_catalog_dir):
        """Catalog entry detects when no scripts present."""
        skill_dir = tmp_path / ".copilot" / "skills" / "no-scripts"
        skill_dir.mkdir(parents=True, exist_ok=True)

        metadata = {
            "skill_name": "no-scripts",
            "generated_at": "2026-04-14T15:30:00Z",
            "personetta_version": "1.0.0",
            "format": "copilot",
            "source_recipes": [
                {
                    "name": "test",
                    "file_path": "test.yaml",
                    "content_hash": "sha256:abc",
                    "file_mtime": "2026-04-10T12:00:00Z",
                }
            ],
        }
        (skill_dir / ".skill-metadata.json").write_text(json.dumps(metadata))

        catalog_path = empty_catalog_dir / "skills-catalog.json"
        catalog = create_catalog()
        save_catalog(catalog, catalog_path)

        update_catalog_entry("no-scripts", "copilot", skill_dir, catalog_path)

        updated = load_catalog(catalog_path)
        entry = updated["skills"]["copilot"]["no-scripts"]

        assert entry["has_scripts"] is False
        assert entry["script_count"] == 0

    def test_update_catalog_entry_overwrites_existing(
        self, sample_skill_dir, empty_catalog_dir
    ):
        """update_catalog_entry overwrites existing entry."""
        catalog_path = empty_catalog_dir / "skills-catalog.json"
        catalog = create_catalog()
        catalog["skills"]["copilot"] = {"python-testing": {"old": "data"}}
        save_catalog(catalog, catalog_path)

        update_catalog_entry("python-testing", "copilot", sample_skill_dir, catalog_path)

        updated = load_catalog(catalog_path)
        entry = updated["skills"]["copilot"]["python-testing"]

        assert "old" not in entry
        assert entry["name"] == "python-testing"


# ============================================================================
# Skill Scanning Tests
# ============================================================================


class TestSkillScanning:
    """Test scanning skill directories."""

    def test_scan_all_skills_finds_skills(self, tmp_path):
        """scan_all_skills finds all skills in directory."""
        # Create multiple skills
        copilot_dir = tmp_path / ".copilot" / "skills"
        copilot_dir.mkdir(parents=True)

        for name in ["python-testing", "code-review", "design-patterns"]:
            skill_dir = copilot_dir / name
            skill_dir.mkdir()
            metadata = {
                "skill_name": name,
                "generated_at": "2026-04-14T15:30:00Z",
                "personetta_version": "1.0.0",
                "format": "copilot",
                "source_recipes": [
                    {
                        "name": "test",
                        "file_path": "test.yaml",
                        "content_hash": "sha256:abc",
                        "file_mtime": "2026-04-10T12:00:00Z",
                    }
                ],
            }
            (skill_dir / ".skill-metadata.json").write_text(json.dumps(metadata))

        skills = scan_all_skills("copilot", base_dir=tmp_path)

        assert len(skills) == 3
        assert "python-testing" in skills
        assert "code-review" in skills
        assert "design-patterns" in skills

    def test_scan_all_skills_skips_invalid_skills(self, tmp_path):
        """scan_all_skills skips directories without metadata."""
        copilot_dir = tmp_path / ".copilot" / "skills"
        copilot_dir.mkdir(parents=True)

        # Valid skill
        valid_dir = copilot_dir / "valid"
        valid_dir.mkdir()
        metadata = {
            "skill_name": "valid",
            "generated_at": "2026-04-14T15:30:00Z",
            "personetta_version": "1.0.0",
            "format": "copilot",
            "source_recipes": [
                {
                    "name": "test",
                    "file_path": "test.yaml",
                    "content_hash": "sha256:abc",
                    "file_mtime": "2026-04-10T12:00:00Z",
                }
            ],
        }
        (valid_dir / ".skill-metadata.json").write_text(json.dumps(metadata))

        # Invalid skill (no metadata)
        invalid_dir = copilot_dir / "invalid"
        invalid_dir.mkdir()
        (invalid_dir / "SKILL.md").write_text("# Invalid")

        skills = scan_all_skills("copilot", base_dir=tmp_path)

        assert len(skills) == 1
        assert "valid" in skills
        assert "invalid" not in skills

    def test_scan_all_skills_handles_empty_directory(self, tmp_path):
        """scan_all_skills returns empty dict when no skills found."""
        copilot_dir = tmp_path / ".copilot" / "skills"
        copilot_dir.mkdir(parents=True)

        skills = scan_all_skills("copilot", base_dir=tmp_path)

        assert skills == {}

    def test_scan_all_skills_handles_missing_directory(self, tmp_path):
        """scan_all_skills returns empty dict when skills directory doesn't exist."""
        skills = scan_all_skills("copilot", base_dir=tmp_path)

        assert skills == {}


# ============================================================================
# Integration Tests
# ============================================================================


class TestCatalogIntegration:
    """Integration tests for complete catalog workflow."""

    def test_catalog_workflow_create_update_load(
        self, sample_skill_dir, empty_catalog_dir
    ):
        """Complete workflow: create catalog, add entry, reload."""
        catalog_path = empty_catalog_dir / "skills-catalog.json"

        # Create fresh catalog
        catalog = create_catalog()
        save_catalog(catalog, catalog_path)

        # Add skill entry
        update_catalog_entry("python-testing", "copilot", sample_skill_dir, catalog_path)

        # Reload and verify
        reloaded = load_catalog(catalog_path)

        assert "copilot" in reloaded["skills"]
        assert "python-testing" in reloaded["skills"]["copilot"]
        entry = reloaded["skills"]["copilot"]["python-testing"]
        assert entry["name"] == "python-testing"
        assert entry["script_count"] == 3

    def test_catalog_supports_multiple_formats(self, tmp_path, empty_catalog_dir):
        """Catalog tracks skills across multiple formats."""
        catalog_path = empty_catalog_dir / "skills-catalog.json"
        catalog = create_catalog()
        save_catalog(catalog, catalog_path)

        # Create skills for different formats
        for format_name in ["copilot", "claude", "cursor"]:
            skill_dir = tmp_path / f".{format_name}" / "skills" / "test-skill"
            skill_dir.mkdir(parents=True)
            metadata = {
                "skill_name": "test-skill",
                "generated_at": "2026-04-14T15:30:00Z",
                "personetta_version": "1.0.0",
                "format": format_name,
                "source_recipes": [
                    {
                        "name": "test",
                        "file_path": "test.yaml",
                        "content_hash": "sha256:abc",
                        "file_mtime": "2026-04-10T12:00:00Z",
                    }
                ],
            }
            (skill_dir / ".skill-metadata.json").write_text(json.dumps(metadata))

            update_catalog_entry("test-skill", format_name, skill_dir, catalog_path)

        # Verify all formats present
        final = load_catalog(catalog_path)

        assert "copilot" in final["skills"]
        assert "claude" in final["skills"]
        assert "cursor" in final["skills"]
        assert "test-skill" in final["skills"]["copilot"]
        assert "test-skill" in final["skills"]["claude"]
        assert "test-skill" in final["skills"]["cursor"]

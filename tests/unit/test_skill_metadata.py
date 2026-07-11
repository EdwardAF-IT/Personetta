"""Tests for skill metadata generation.

Tests .skill-metadata.json creation, updates, and hash computation.

Following TDD approach: write tests first, then implement.
Tests for:
- Recipe hash computation (SHA-256)
- Metadata creation with all required fields
- Metadata file writing during skill generation
"""

from __future__ import annotations

import json
import pytest
from datetime import datetime
from pathlib import Path
from generator.skills import SkillGenerator
from generator.skills.metadata import compute_recipe_hash, create_metadata

# ============================================================================
# Fixtures
# ============================================================================


from generator.project_layout import ProjectLayout


@pytest.fixture
def skill_generator_with_templates():
    """SkillGenerator with actual templates from data/templates/skill/."""
    # Use real templates from repo - updated for new structure
    template_dir = ProjectLayout.from_file(__file__).templates / "skill"
    return SkillGenerator(template_dir)


# ============================================================================
# Phase 7a: Recipe Hash Computation
# ============================================================================


class TestRecipeHashComputation:
    """Test recipe content hashing for staleness detection."""

    def test_compute_hash_returns_sha256_string(self):
        """compute_recipe_hash returns SHA-256 hash as hex string."""
        recipe = {"name": "test", "description": "Test recipe"}

        result = compute_recipe_hash(recipe)

        assert isinstance(result, str)
        assert result.startswith("sha256:")
        # SHA-256 produces 64-character hex string
        hash_part = result.split(":", 1)[1]
        assert len(hash_part) == 64
        assert all(c in "0123456789abcdef" for c in hash_part)

    def test_identical_recipes_produce_identical_hashes(self):
        """Same recipe content produces same hash (deterministic)."""
        recipe1 = {"name": "test", "description": "Test recipe"}
        recipe2 = {"name": "test", "description": "Test recipe"}

        hash1 = compute_recipe_hash(recipe1)
        hash2 = compute_recipe_hash(recipe2)

        assert hash1 == hash2

    def test_different_recipes_produce_different_hashes(self):
        """Different recipe content produces different hashes."""
        recipe1 = {"name": "test", "description": "Test recipe"}
        recipe2 = {"name": "test", "description": "Different recipe"}

        hash1 = compute_recipe_hash(recipe1)
        hash2 = compute_recipe_hash(recipe2)

        assert hash1 != hash2

    def test_key_order_does_not_affect_hash(self):
        """Hash is deterministic regardless of dictionary key order."""
        recipe1 = {"name": "test", "description": "Test", "version": "1.0"}
        recipe2 = {"version": "1.0", "description": "Test", "name": "test"}

        hash1 = compute_recipe_hash(recipe1)
        hash2 = compute_recipe_hash(recipe2)

        assert hash1 == hash2


# ============================================================================
# Phase 7a: Metadata Creation
# ============================================================================


class TestMetadataCreation:
    """Test metadata dictionary generation."""

    def test_create_metadata_includes_all_required_fields(self):
        """Metadata includes: skill_name, generated_at, version, format, source_recipes."""
        recipe = {
            "name": "test-python-backend",
            "description": "Test recipe",
        }

        metadata = create_metadata(
            skill_name="python-testing",
            recipes=[recipe],
            format="copilot",
            base_dir=Path("/fake/recipes"),
        )

        assert "skill_name" in metadata
        assert "generated_at" in metadata
        assert "personetta_version" in metadata
        assert "format" in metadata
        assert "source_recipes" in metadata

    def test_metadata_skill_name_matches_parameter(self):
        """Metadata skill_name field matches input parameter."""
        recipe = {"name": "test", "description": "Test"}

        metadata = create_metadata(
            skill_name="my-skill", recipes=[recipe], format="copilot"
        )

        assert metadata["skill_name"] == "my-skill"

    def test_metadata_format_matches_parameter(self):
        """Metadata format field matches input parameter."""
        recipe = {"name": "test", "description": "Test"}

        metadata = create_metadata(skill_name="test", recipes=[recipe], format="claude")

        assert metadata["format"] == "claude"

    def test_metadata_timestamp_is_iso8601(self):
        """Timestamp is in ISO 8601 format with timezone."""
        recipe = {"name": "test", "description": "Test"}

        metadata = create_metadata(skill_name="test", recipes=[recipe], format="copilot")

        timestamp = metadata["generated_at"]
        # Should be parseable as ISO 8601
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        assert parsed is not None

    def test_metadata_includes_version_from_pyproject(self):
        """Metadata includes personetta version from pyproject.toml."""
        recipe = {"name": "test", "description": "Test"}

        metadata = create_metadata(skill_name="test", recipes=[recipe], format="copilot")

        version = metadata["personetta_version"]
        assert version is not None
        assert isinstance(version, str)
        # Should match semantic versioning pattern
        assert "." in version

    def test_source_recipes_contains_recipe_details(self):
        """Each source recipe entry has name, file_path, content_hash, file_mtime."""
        recipe = {"name": "test-python", "description": "Test"}

        metadata = create_metadata(
            skill_name="test",
            recipes=[recipe],
            format="copilot",
            base_dir=Path("/fake/recipes"),
        )

        source_recipes = metadata["source_recipes"]
        assert len(source_recipes) == 1

        recipe_ref = source_recipes[0]
        assert "name" in recipe_ref
        assert "file_path" in recipe_ref
        assert "content_hash" in recipe_ref
        assert "file_mtime" in recipe_ref

        assert recipe_ref["name"] == "test-python"
        assert recipe_ref["content_hash"].startswith("sha256:")

    def test_multi_recipe_metadata_lists_all_sources(self):
        """Metadata for multi-recipe skill lists all source recipes."""
        recipe1 = {"name": "test-python", "description": "Test"}
        recipe2 = {"name": "review-python", "description": "Review"}

        metadata = create_metadata(
            skill_name="python-quality", recipes=[recipe1, recipe2], format="copilot"
        )

        source_recipes = metadata["source_recipes"]
        assert len(source_recipes) == 2
        assert source_recipes[0]["name"] == "test-python"
        assert source_recipes[1]["name"] == "review-python"


# ============================================================================
# Phase 7a: Metadata File Writing
# ============================================================================


class TestMetadataFileWriting:
    """Test .skill-metadata.json file generation during skill creation."""

    def test_generate_creates_metadata_file(
        self, tmp_path, skill_generator_with_templates
    ):
        """SkillGenerator.generate() creates .skill-metadata.json file."""
        generator = skill_generator_with_templates
        output_dir = tmp_path / "python-testing"

        recipe = {
            "name": "test-python-backend",
            "description": "Test recipe",
            "responsibilities": ["Test code"],
        }

        generator.generate(
            recipe=recipe,
            format="copilot",
            skill_name="python-testing",
            output_dir=output_dir,
        )

        metadata_file = output_dir / ".skill-metadata.json"
        assert metadata_file.exists()

    def test_metadata_file_is_valid_json(self, tmp_path, skill_generator_with_templates):
        """Metadata file contains valid JSON."""
        generator = skill_generator_with_templates
        output_dir = tmp_path / "python-testing"

        recipe = {
            "name": "test-python-backend",
            "description": "Test recipe",
            "responsibilities": ["Test code"],
        }

        generator.generate(
            recipe=recipe,
            format="copilot",
            skill_name="python-testing",
            output_dir=output_dir,
        )

        metadata_file = output_dir / ".skill-metadata.json"
        content = metadata_file.read_text(encoding="utf-8")

        # Should parse without error
        metadata = json.loads(content)
        assert isinstance(metadata, dict)

    def test_metadata_file_contains_expected_structure(
        self, tmp_path, skill_generator_with_templates
    ):
        """Metadata file has expected structure matching create_metadata output."""
        generator = skill_generator_with_templates
        output_dir = tmp_path / "python-testing"

        recipe = {
            "name": "test-python-backend",
            "description": "Test recipe",
            "responsibilities": ["Test code"],
        }

        generator.generate(
            recipe=recipe,
            format="copilot",
            skill_name="python-testing",
            output_dir=output_dir,
        )

        metadata_file = output_dir / ".skill-metadata.json"
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))

        assert metadata["skill_name"] == "python-testing"
        assert metadata["format"] == "copilot"
        assert "generated_at" in metadata
        assert "personetta_version" in metadata
        assert len(metadata["source_recipes"]) == 1
        assert metadata["source_recipes"][0]["name"] == "test-python-backend"

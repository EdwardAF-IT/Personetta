"""
Phase 7e tests: Skill update detection and regeneration.

Tests staleness detection, check-skills command, and update-skill command.
"""

import json
from generator.skills.metadata import compute_recipe_hash
from generator.skill_updater import (
    is_skill_stale,
    check_stale_skills,
    update_skill,
    update_all_stale_skills,
)


class TestStalenessDetection:
    """Test is_skill_stale() function."""

    def test_skill_is_fresh_when_hash_matches(self, tmp_path):
        """Skill is fresh when recipe hash matches metadata."""
        # Arrange
        recipe = {
            "name": "test-python",
            "description": "Test recipe",
            "responsibilities": ["Write tests"],
        }
        recipe_hash = compute_recipe_hash(recipe)

        metadata = {
            "skill_name": "python-testing",
            "generated_at": "2026-04-14T10:00:00Z",
            "personetta_version": "1.0.0",
            "format": "copilot",
            "source_recipes": [
                {
                    "name": "test-python",
                    "file_path": "recipes/test-python.yaml",
                    "content_hash": recipe_hash,
                }
            ],
        }

        # Act
        is_stale, reason = is_skill_stale(metadata, {"test-python": recipe})

        # Assert
        assert is_stale is False
        assert reason is None

    def test_skill_is_stale_when_recipe_changed(self, tmp_path):
        """Skill is stale when recipe content changed."""
        # Arrange
        original_recipe = {
            "name": "test-python",
            "description": "Test recipe",
            "responsibilities": ["Write tests"],
        }
        original_hash = compute_recipe_hash(original_recipe)

        updated_recipe = {
            "name": "test-python",
            "description": "Updated test recipe",  # Changed
            "responsibilities": ["Write tests", "Run coverage"],  # Changed
        }

        metadata = {
            "skill_name": "python-testing",
            "generated_at": "2026-04-14T10:00:00Z",
            "personetta_version": "1.0.0",
            "format": "copilot",
            "source_recipes": [
                {
                    "name": "test-python",
                    "file_path": "recipes/test-python.yaml",
                    "content_hash": original_hash,
                }
            ],
        }

        # Act
        is_stale, reason = is_skill_stale(metadata, {"test-python": updated_recipe})

        # Assert
        assert is_stale is True
        assert "test-python" in reason
        assert "updated" in reason.lower()

    def test_multi_recipe_skill_stale_when_one_recipe_changed(self, tmp_path):
        """Multi-recipe skill is stale if any recipe changed."""
        # Arrange
        recipe1 = {"name": "test-python", "description": "Test"}
        recipe2_original = {"name": "review-python", "description": "Review"}
        recipe2_updated = {"name": "review-python", "description": "Updated review"}

        hash1 = compute_recipe_hash(recipe1)
        hash2_original = compute_recipe_hash(recipe2_original)

        metadata = {
            "skill_name": "python-quality",
            "generated_at": "2026-04-14T10:00:00Z",
            "personetta_version": "1.0.0",
            "format": "copilot",
            "source_recipes": [
                {"name": "test-python", "content_hash": hash1},
                {"name": "review-python", "content_hash": hash2_original},
            ],
        }

        current_recipes = {
            "test-python": recipe1,
            "review-python": recipe2_updated,  # This one changed
        }

        # Act
        is_stale, reason = is_skill_stale(metadata, current_recipes)

        # Assert
        assert is_stale is True
        assert "review-python" in reason

    def test_skill_stale_when_recipe_missing(self, tmp_path):
        """Skill is stale when source recipe no longer exists."""
        # Arrange
        metadata = {
            "skill_name": "python-testing",
            "generated_at": "2026-04-14T10:00:00Z",
            "personetta_version": "1.0.0",
            "format": "copilot",
            "source_recipes": [{"name": "test-python", "content_hash": "abc123"}],
        }

        current_recipes = {}  # Recipe no longer exists

        # Act
        is_stale, reason = is_skill_stale(metadata, current_recipes)

        # Assert
        assert is_stale is True
        assert "test-python" in reason
        assert "not found" in reason.lower() or "missing" in reason.lower()


class TestCheckStaleSkills:
    """Test check_stale_skills() function."""

    def test_check_finds_stale_skills(self, tmp_path):
        """check_stale_skills finds all stale skills."""
        # Arrange: Create 3 skills - 1 fresh, 2 stale
        base_dir = tmp_path / "skills"

        # Fresh skill
        fresh_dir = base_dir / "fresh-skill"
        fresh_dir.mkdir(parents=True)
        fresh_recipe = {"name": "fresh", "description": "Fresh"}
        fresh_hash = compute_recipe_hash(fresh_recipe)
        fresh_metadata = {
            "skill_name": "fresh-skill",
            "format": "copilot",
            "source_recipes": [{"name": "fresh", "content_hash": fresh_hash}],
        }
        (fresh_dir / ".skill-metadata.json").write_text(json.dumps(fresh_metadata))

        # Stale skill 1
        stale1_dir = base_dir / "stale-skill-1"
        stale1_dir.mkdir(parents=True)
        stale1_recipe_old = {"name": "stale1", "description": "Old"}
        stale1_hash_old = compute_recipe_hash(stale1_recipe_old)
        stale1_metadata = {
            "skill_name": "stale-skill-1",
            "format": "copilot",
            "source_recipes": [{"name": "stale1", "content_hash": stale1_hash_old}],
        }
        (stale1_dir / ".skill-metadata.json").write_text(json.dumps(stale1_metadata))

        # Stale skill 2
        stale2_dir = base_dir / "stale-skill-2"
        stale2_dir.mkdir(parents=True)
        stale2_recipe_old = {"name": "stale2", "description": "Old"}
        stale2_hash_old = compute_recipe_hash(stale2_recipe_old)
        stale2_metadata = {
            "skill_name": "stale-skill-2",
            "format": "copilot",
            "source_recipes": [{"name": "stale2", "content_hash": stale2_hash_old}],
        }
        (stale2_dir / ".skill-metadata.json").write_text(json.dumps(stale2_metadata))

        # Current recipes (fresh unchanged, stale1 and stale2 updated)
        current_recipes = {
            "fresh": fresh_recipe,
            "stale1": {"name": "stale1", "description": "Updated"},
            "stale2": {"name": "stale2", "description": "Updated"},
        }

        # Act
        stale_skills = check_stale_skills(base_dir, current_recipes)

        # Assert
        assert len(stale_skills) == 2
        stale_names = [s["skill_name"] for s in stale_skills]
        assert "stale-skill-1" in stale_names
        assert "stale-skill-2" in stale_names
        assert "fresh-skill" not in stale_names

    def test_check_handles_missing_metadata(self, tmp_path):
        """check_stale_skills skips skills with missing metadata."""
        # Arrange: Create skill without metadata
        base_dir = tmp_path / "skills"
        skill_dir = base_dir / "no-metadata-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Skill")
        # No .skill-metadata.json file

        current_recipes = {}

        # Act
        stale_skills = check_stale_skills(base_dir, current_recipes)

        # Assert - Should not crash, should skip skill
        assert len(stale_skills) == 0

    def test_check_returns_empty_when_all_fresh(self, tmp_path):
        """check_stale_skills returns empty list when all skills fresh."""
        # Arrange
        base_dir = tmp_path / "skills"
        skill_dir = base_dir / "fresh-skill"
        skill_dir.mkdir(parents=True)

        recipe = {"name": "fresh", "description": "Fresh"}
        recipe_hash = compute_recipe_hash(recipe)
        metadata = {
            "skill_name": "fresh-skill",
            "format": "copilot",
            "source_recipes": [{"name": "fresh", "content_hash": recipe_hash}],
        }
        (skill_dir / ".skill-metadata.json").write_text(json.dumps(metadata))

        current_recipes = {"fresh": recipe}

        # Act
        stale_skills = check_stale_skills(base_dir, current_recipes)

        # Assert
        assert len(stale_skills) == 0


class TestUpdateSkill:
    """Test update_skill() function."""

    def test_update_regenerates_skill_from_latest_recipe(self, tmp_path):
        """update_skill regenerates skill with updated recipe."""
        # Arrange
        skill_dir = tmp_path / "python-testing"
        skill_dir.mkdir(parents=True)

        # Create initial skill with old metadata
        old_recipe = {"name": "test-python", "description": "Old description"}
        old_hash = compute_recipe_hash(old_recipe)
        old_metadata = {
            "skill_name": "python-testing",
            "format": "copilot",
            "source_recipes": [{"name": "test-python", "content_hash": old_hash}],
        }
        (skill_dir / ".skill-metadata.json").write_text(json.dumps(old_metadata))
        (skill_dir / "SKILL.md").write_text(
            "---\nname: python-testing\n---\n\nOld description"
        )

        # New recipe
        new_recipe = {
            "name": "test-python",
            "description": "New updated description",
            "responsibilities": ["Write tests", "Run coverage"],
        }

        # Act
        success = update_skill(skill_dir, [new_recipe], "copilot")

        # Assert
        assert success is True

        # Check metadata updated
        new_metadata = json.loads((skill_dir / ".skill-metadata.json").read_text())
        new_hash = compute_recipe_hash(new_recipe)
        assert new_metadata["source_recipes"][0]["content_hash"] == new_hash

        # Check SKILL.md updated
        skill_md = (skill_dir / "SKILL.md").read_text()
        assert "New updated description" in skill_md

    def test_update_preserves_skill_name(self, tmp_path):
        """update_skill preserves original skill name."""
        # Arrange
        skill_dir = tmp_path / "custom-name"
        skill_dir.mkdir(parents=True)

        old_metadata = {
            "skill_name": "custom-name",
            "format": "copilot",
            "source_recipes": [{"name": "test-python", "content_hash": "old"}],
        }
        (skill_dir / ".skill-metadata.json").write_text(json.dumps(old_metadata))

        new_recipe = {"name": "test-python", "description": "Updated"}

        # Act
        update_skill(skill_dir, [new_recipe], "copilot")

        # Assert
        new_metadata = json.loads((skill_dir / ".skill-metadata.json").read_text())
        assert new_metadata["skill_name"] == "custom-name"

    def test_update_fails_gracefully_when_recipe_invalid(self, tmp_path):
        """update_skill returns False when recipe invalid."""
        # Arrange
        skill_dir = tmp_path / "python-testing"
        skill_dir.mkdir(parents=True)

        metadata = {
            "skill_name": "python-testing",
            "format": "copilot",
            "source_recipes": [{"name": "test-python", "content_hash": "abc"}],
        }
        (skill_dir / ".skill-metadata.json").write_text(json.dumps(metadata))

        invalid_recipe = {}  # Missing required fields

        # Act
        success = update_skill(skill_dir, [invalid_recipe], "copilot")

        # Assert
        assert success is False


class TestUpdateAllStaleSkills:
    """Test update_all_stale_skills() function."""

    def test_update_all_regenerates_all_stale_skills(self, tmp_path):
        """update_all_stale_skills regenerates all stale skills."""
        # Arrange
        base_dir = tmp_path / "skills"

        # Create 2 stale skills
        for i in [1, 2]:
            skill_dir = base_dir / f"stale-skill-{i}"
            skill_dir.mkdir(parents=True)

            old_recipe = {"name": f"recipe{i}", "description": f"Old {i}"}
            old_hash = compute_recipe_hash(old_recipe)
            metadata = {
                "skill_name": f"stale-skill-{i}",
                "format": "copilot",
                "source_recipes": [{"name": f"recipe{i}", "content_hash": old_hash}],
            }
            (skill_dir / ".skill-metadata.json").write_text(json.dumps(metadata))
            (skill_dir / "SKILL.md").write_text(f"Old content {i}")

        # New recipes
        new_recipes = {
            "recipe1": {"name": "recipe1", "description": "New 1"},
            "recipe2": {"name": "recipe2", "description": "New 2"},
        }

        # Act
        updated_count = update_all_stale_skills(base_dir, new_recipes)

        # Assert
        assert updated_count == 2

        # Verify both updated
        for i in [1, 2]:
            skill_dir = base_dir / f"stale-skill-{i}"
            skill_md = (skill_dir / "SKILL.md").read_text()
            assert f"New {i}" in skill_md

    def test_update_all_skips_fresh_skills(self, tmp_path):
        """update_all_stale_skills skips skills that are fresh."""
        # Arrange
        base_dir = tmp_path / "skills"

        # Fresh skill
        fresh_dir = base_dir / "fresh-skill"
        fresh_dir.mkdir(parents=True)
        recipe = {"name": "fresh", "description": "Unchanged"}
        recipe_hash = compute_recipe_hash(recipe)
        metadata = {
            "skill_name": "fresh-skill",
            "format": "copilot",
            "source_recipes": [{"name": "fresh", "content_hash": recipe_hash}],
        }
        (fresh_dir / ".skill-metadata.json").write_text(json.dumps(metadata))
        (fresh_dir / "SKILL.md").write_text("# Fresh\nUnchanged")

        current_recipes = {"fresh": recipe}

        # Act
        updated_count = update_all_stale_skills(base_dir, current_recipes)

        # Assert
        assert updated_count == 0
        # Verify SKILL.md unchanged
        assert (fresh_dir / "SKILL.md").read_text() == "# Fresh\nUnchanged"

"""Unit tests for generator/cli/commands/update_skill.py.

Tests skill update command functionality including
validation, metadata loading, and update workflows.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from generator.cli.commands.update_skill import (
    _check_and_confirm_stale_updates,
    _load_all_current_recipes,
    _load_recipes_from_names,
    _load_skill_metadata,
    _update_all_formats,
    _update_single_skill_impl,
    _validate_update_args,
)


@pytest.fixture
def mock_args():
    """Create mock arguments namespace."""
    args = argparse.Namespace()
    args.all = False
    args.name = None
    args.format = None
    args.whatif = False
    args.force = False
    args.workspace = False
    args.target = None
    return args


@pytest.fixture
def sample_recipes():
    """Create sample recipes dictionary."""
    return {
        "recipe-a": {
            "name": "recipe-a",
            "description": "Recipe A",
            "version": "1.0.0",
        },
        "recipe-b": {
            "name": "recipe-b",
            "description": "Recipe B",
            "version": "1.0.0",
        },
    }


class TestValidateUpdateArgs:
    """Test argument validation."""

    def test_missing_name_and_all(self, mock_args, capsys):
        """Should fail when neither name nor --all provided."""
        mock_args.all = False
        mock_args.name = None

        result = _validate_update_args(mock_args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Must provide skill name or use --all" in captured.err

    def test_name_without_format(self, mock_args, capsys):
        """Should fail when name provided without format."""
        mock_args.all = False
        mock_args.name = "test-skill"
        mock_args.format = None

        result = _validate_update_args(mock_args)

        assert result == 1
        captured = capsys.readouterr()
        assert "--format required" in captured.err

    def test_valid_with_name_and_format(self, mock_args):
        """Should pass when name and format provided."""
        mock_args.name = "test-skill"
        mock_args.format = "copilot"

        result = _validate_update_args(mock_args)

        assert result is None

    def test_valid_with_all_flag(self, mock_args):
        """Should pass when --all flag provided."""
        mock_args.all = True

        result = _validate_update_args(mock_args)

        assert result is None


class TestLoadAllCurrentRecipes:
    """Test recipe loading."""

    @patch("generator.cli.commands.update_skill.load_recipe")
    @patch("generator.cli.commands.update_skill.list_recipes")
    @patch("generator.cli.commands.update_skill.REPO_ROOT", Path("/repo"))
    def test_loads_all_recipes(self, mock_list, mock_load):
        """Should load all recipes from repository."""
        mock_list.return_value = [
            {"name": "recipe-a"},
            {"name": "recipe-b"},
        ]
        mock_load.side_effect = [
            {"name": "recipe-a", "version": "1.0.0"},
            {"name": "recipe-b", "version": "2.0.0"},
        ]

        result = _load_all_current_recipes()

        assert len(result) == 2
        assert "recipe-a" in result
        assert "recipe-b" in result
        assert result["recipe-a"]["version"] == "1.0.0"
        assert result["recipe-b"]["version"] == "2.0.0"

    @patch("generator.cli.commands.update_skill.load_recipe")
    @patch("generator.cli.commands.update_skill.list_recipes")
    @patch("generator.cli.commands.update_skill.REPO_ROOT", Path("/repo"))
    def test_uses_repo_root_as_base(self, mock_list, mock_load):
        """Should use REPO_ROOT as base directory."""
        mock_list.return_value = [{"name": "test"}]
        mock_load.return_value = {"name": "test"}

        _load_all_current_recipes()

        mock_list.assert_called_once_with(base_dir=Path("/repo"))


class TestLoadSkillMetadata:
    """Test skill metadata loading."""

    def test_loads_valid_metadata(self, tmp_path: Path):
        """Should load metadata from .skill-metadata.json."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        metadata = {
            "source_recipes": [
                {"name": "recipe-a"},
                {"name": "recipe-b"},
            ]
        }
        (skill_dir / ".skill-metadata.json").write_text(
            json.dumps(metadata), encoding="utf-8"
        )

        recipe_names, exit_code = _load_skill_metadata(skill_dir)

        assert exit_code == 0
        assert recipe_names == ["recipe-a", "recipe-b"]

    def test_missing_metadata_file(self, tmp_path: Path, capsys):
        """Should return error when metadata file missing."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        recipe_names, exit_code = _load_skill_metadata(skill_dir)

        assert exit_code == 1
        assert recipe_names is None
        captured = capsys.readouterr()
        assert "Skill metadata not found" in captured.err

    def test_empty_source_recipes(self, tmp_path: Path, capsys):
        """Should return error when source_recipes is empty."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        metadata: dict[str, list[str]] = {"source_recipes": []}
        (skill_dir / ".skill-metadata.json").write_text(
            json.dumps(metadata), encoding="utf-8"
        )

        recipe_names, exit_code = _load_skill_metadata(skill_dir)

        assert exit_code == 1
        assert recipe_names is None
        captured = capsys.readouterr()
        assert "No source recipes" in captured.err


class TestLoadRecipesFromNames:
    """Test recipe loading from names."""

    def test_loads_valid_recipes(self, sample_recipes):
        """Should load recipes that exist."""
        recipe_names = ["recipe-a", "recipe-b"]

        recipes, exit_code = _load_recipes_from_names(recipe_names, sample_recipes)

        assert exit_code == 0
        assert len(recipes) == 2
        assert recipes[0]["name"] == "recipe-a"
        assert recipes[1]["name"] == "recipe-b"

    def test_skips_missing_recipes(self, sample_recipes, capsys):
        """Should skip recipes that don't exist."""
        recipe_names = ["recipe-a", "missing-recipe", "recipe-b"]

        recipes, exit_code = _load_recipes_from_names(recipe_names, sample_recipes)

        assert exit_code == 0
        assert len(recipes) == 2
        captured = capsys.readouterr()
        assert "Recipe 'missing-recipe' not found" in captured.err

    def test_all_recipes_missing(self, sample_recipes, capsys):
        """Should return error when all recipes missing."""
        recipe_names = ["missing-1", "missing-2"]

        recipes, exit_code = _load_recipes_from_names(recipe_names, sample_recipes)

        assert exit_code == 1
        assert recipes is None
        captured = capsys.readouterr()
        assert "No valid recipes found" in captured.err


class TestCheckAndConfirmStaleUpdates:
    """Test stale update confirmation."""

    def test_whatif_mode_lists_updates(self, capsys):
        """Should list updates in whatif mode without prompting."""
        stale_skills = [
            {"skill_name": "skill-a", "reason": "out of date"},
            {"skill_name": "skill-b", "reason": "missing file"},
        ]

        result = _check_and_confirm_stale_updates(
            stale_skills, "copilot", force=False, whatif=True
        )

        assert result is False
        captured = capsys.readouterr()
        assert "Would update 2 skill(s)" in captured.out
        assert "skill-a: out of date" in captured.out
        assert "skill-b: missing file" in captured.out

    def test_force_mode_no_prompt(self):
        """Should skip confirmation in force mode."""
        stale_skills = [{"skill_name": "test", "reason": "test"}]

        result = _check_and_confirm_stale_updates(
            stale_skills, "copilot", force=True, whatif=False
        )

        assert result is True

    @patch("builtins.input", return_value="y")
    def test_user_confirms_update(self, mock_input, capsys):
        """Should proceed when user confirms."""
        stale_skills = [{"skill_name": "test", "reason": "test"}]

        result = _check_and_confirm_stale_updates(
            stale_skills, "copilot", force=False, whatif=False
        )

        assert result is True

    @patch("builtins.input", return_value="n")
    def test_user_cancels_update(self, mock_input, capsys):
        """Should cancel when user declines."""
        stale_skills = [{"skill_name": "test", "reason": "test"}]

        result = _check_and_confirm_stale_updates(
            stale_skills, "copilot", force=False, whatif=False
        )

        assert result is False
        captured = capsys.readouterr()
        assert "Cancelled" in captured.out


class TestUpdateAllFormats:
    """Test updating across multiple formats."""

    @patch("generator.cli.commands.update_skill.update_catalog_entry")
    @patch("generator.cli.commands.update_skill.update_all_stale_skills")
    @patch("generator.cli.commands.update_skill.check_stale_skills")
    @patch("generator.cli.commands.update_skill.get_skill_install_path")
    def test_updates_stale_skills(
        self,
        mock_get_path,
        mock_check,
        mock_update,
        mock_catalog,
        tmp_path,
        sample_recipes,
        capsys,
    ):
        """Should update stale skills in each format."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        mock_get_path.return_value = skills_dir / "dummy"
        mock_check.return_value = [
            {"skill_name": "skill-a", "reason": "stale", "skill_dir": skills_dir / "a"}
        ]
        mock_update.return_value = 1

        total = _update_all_formats(
            ["copilot"],
            tmp_path,
            sample_recipes,
            whatif=False,
            force=True,
        )

        assert total == 1
        mock_update.assert_called_once()

    @patch("generator.cli.commands.update_skill.get_skill_install_path")
    def test_skips_nonexistent_skill_directories(
        self, mock_get_path, tmp_path, sample_recipes
    ):
        """Should skip formats with nonexistent skill directories."""
        nonexistent_dir = tmp_path / "nonexistent" / "skills"
        mock_get_path.return_value = nonexistent_dir / "dummy"

        total = _update_all_formats(
            ["copilot"], tmp_path, sample_recipes, whatif=False, force=True
        )

        assert total == 0

    @patch("generator.cli.commands.update_skill.check_stale_skills")
    @patch("generator.cli.commands.update_skill.get_skill_install_path")
    def test_skips_formats_with_no_stale_skills(
        self, mock_get_path, mock_check, tmp_path, sample_recipes
    ):
        """Should skip formats with no stale skills."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        mock_get_path.return_value = skills_dir / "dummy"
        mock_check.return_value = []  # No stale skills

        total = _update_all_formats(
            ["copilot"], tmp_path, sample_recipes, whatif=False, force=True
        )

        assert total == 0


class TestUpdateSingleSkillImpl:
    """Test single skill update implementation."""

    @patch("generator.cli.commands.update_skill.update_catalog_entry")
    @patch("generator.cli.commands.update_skill.update_skill")
    def test_successful_update(
        self, mock_update, mock_catalog, tmp_path, sample_recipes, capsys
    ):
        """Should successfully update skill."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        metadata = {
            "source_recipes": [
                {"name": "recipe-a"},
                {"name": "recipe-b"},
            ]
        }
        (skill_dir / ".skill-metadata.json").write_text(
            json.dumps(metadata), encoding="utf-8"
        )

        mock_update.return_value = True

        result = _update_single_skill_impl(
            "test-skill", skill_dir, "copilot", sample_recipes, whatif=False
        )

        assert result == 0
        mock_update.assert_called_once()
        mock_catalog.assert_called_once_with("test-skill", "copilot", skill_dir)
        captured = capsys.readouterr()
        assert "✓ Updated skill: test-skill" in captured.out

    @patch("generator.cli.commands.update_skill.update_skill")
    def test_update_failure(self, mock_update, tmp_path, sample_recipes, capsys):
        """Should return error code when update fails."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        metadata = {"source_recipes": [{"name": "recipe-a"}]}
        (skill_dir / ".skill-metadata.json").write_text(
            json.dumps(metadata), encoding="utf-8"
        )

        mock_update.return_value = False

        result = _update_single_skill_impl(
            "test-skill", skill_dir, "copilot", sample_recipes, whatif=False
        )

        assert result == 1
        captured = capsys.readouterr()
        assert "Failed to update skill" in captured.err

    def test_whatif_mode(self, tmp_path, sample_recipes, capsys):
        """Should only print what would be updated in whatif mode."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        metadata = {"source_recipes": [{"name": "recipe-a"}]}
        (skill_dir / ".skill-metadata.json").write_text(
            json.dumps(metadata), encoding="utf-8"
        )

        result = _update_single_skill_impl(
            "test-skill", skill_dir, "copilot", sample_recipes, whatif=True
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "[WHATIF]" in captured.out
        assert "Would update skill 'test-skill'" in captured.out

    def test_missing_metadata(self, tmp_path, sample_recipes):
        """Should return error when metadata missing."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        result = _update_single_skill_impl(
            "test-skill", skill_dir, "copilot", sample_recipes, whatif=False
        )

        assert result == 1

    def test_missing_recipes(self, tmp_path, capsys):
        """Should return error when recipes not found."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        metadata = {"source_recipes": [{"name": "missing-recipe"}]}
        (skill_dir / ".skill-metadata.json").write_text(
            json.dumps(metadata), encoding="utf-8"
        )

        result = _update_single_skill_impl(
            "test-skill", skill_dir, "copilot", {}, whatif=False
        )

        assert result == 1

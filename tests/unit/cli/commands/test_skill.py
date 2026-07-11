"""Tests for skill command.

This module tests skill command functionality including argument parsing,
validation, pattern matching, overwrite handling, and whatif mode.
"""

from __future__ import annotations

import argparse
import sys
from unittest.mock import patch

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


class TestSkillCommandParser:
    """Tests for skill subparser."""

    def test_skill_subparser_exists(self, monkeypatch):
        """Verify 'skill' subparser is present."""
        monkeypatch.setattr(sys, "argv", ["personetta", "-h"])
        from generator.cli.parser import build_parser

        parser = build_parser()
        subparsers_action = None
        for action in parser._actions:
            if hasattr(action, "choices") and action.choices:
                subparsers_action = action
                break

        assert subparsers_action is not None, "Should have subparsers"
        assert "skill" in subparsers_action.choices, "skill command should exist"

    def test_skill_required_arguments(self, monkeypatch):
        """Test skill command requires patterns, --format, and --name."""
        from generator.cli.parser import build_parser

        parser = build_parser()

        # Missing pattern
        with pytest.raises(SystemExit):
            parser.parse_args(["skill", "-f", "copilot", "-n", "test"])

        # Missing --format
        with pytest.raises(SystemExit):
            parser.parse_args(["skill", "test-python-backend", "-n", "test"])

        # Missing --name
        with pytest.raises(SystemExit):
            parser.parse_args(["skill", "test-python-backend", "-f", "copilot"])

        # All required present - should parse successfully
        args = parser.parse_args(
            ["skill", "test-python-backend", "-f", "copilot", "-n", "python-testing"]
        )
        assert args.command == "skill"
        assert args.patterns == ["test-python-backend"]
        assert args.format == "copilot"
        assert args.name == "python-testing"

    def test_skill_optional_flags(self, monkeypatch):
        """Test skill command optional flags (-w, -t, --force, --whatif)."""
        from generator.cli.parser import build_parser

        parser = build_parser()

        # With workspace flag
        args = parser.parse_args(
            ["skill", "test-python", "-f", "copilot", "-n", "test", "-w"]
        )
        assert args.workspace is True

        # With target flag
        args = parser.parse_args(
            [
                "skill",
                "test-python",
                "-f",
                "copilot",
                "-n",
                "test",
                "-t",
                "project",
                "/tmp",
            ]
        )
        assert args.target == ["project", "/tmp"]

        # With force flag
        args = parser.parse_args(
            ["skill", "test-python", "-f", "copilot", "-n", "test", "--force"]
        )
        assert args.force is True

        # With whatif flag
        args = parser.parse_args(
            ["skill", "test-python", "-f", "copilot", "-n", "test", "--whatif"]
        )
        assert args.whatif is True

    def test_skill_multiple_patterns(self, monkeypatch):
        """Test skill command accepts multiple patterns."""
        from generator.cli.parser import build_parser

        parser = build_parser()
        args = parser.parse_args(
            ["skill", "test-*", "review-*", "-f", "copilot", "-n", "code-review"]
        )
        assert args.patterns == ["test-*", "review-*"]

    def test_skill_short_form_flags(self, monkeypatch):
        """Test skill command accepts short-form flags."""
        from generator.cli.parser import build_parser

        parser = build_parser()
        args = parser.parse_args(
            ["skill", "test-python", "-f", "copilot", "-n", "test", "-w", "-t", "project"]
        )
        assert args.format == "copilot"
        assert args.name == "test"
        assert args.workspace is True
        assert args.target == ["project"]


class TestSkillNameValidation:
    """Tests for skill name validation and normalization."""

    def test_normalize_skill_name_lowercase(self):
        """Test name is converted to lowercase."""
        from generator.cli.commands import normalize_skill_name

        assert normalize_skill_name("Python-Testing") == "python-testing"
        assert normalize_skill_name("CODE-REVIEW") == "code-review"

    def test_normalize_skill_name_spaces_to_hyphens(self):
        """Test spaces are converted to hyphens."""
        from generator.cli.commands import normalize_skill_name

        assert normalize_skill_name("python testing") == "python-testing"
        assert normalize_skill_name("code review python") == "code-review-python"

    def test_normalize_skill_name_underscores_to_hyphens(self):
        """Test underscores are converted to hyphens."""
        from generator.cli.commands import normalize_skill_name

        assert normalize_skill_name("python_testing") == "python-testing"
        assert normalize_skill_name("code_review_python") == "code-review-python"

    def test_normalize_skill_name_multiple_hyphens(self):
        """Test multiple consecutive hyphens are collapsed."""
        from generator.cli.commands import normalize_skill_name

        assert normalize_skill_name("python--testing") == "python-testing"
        assert normalize_skill_name("code---review") == "code-review"

    def test_normalize_skill_name_strip_hyphens(self):
        """Test leading/trailing hyphens are stripped."""
        from generator.cli.commands import normalize_skill_name

        assert normalize_skill_name("-python-") == "python"
        assert normalize_skill_name("--code-review--") == "code-review"

    def test_validate_skill_name_valid(self):
        """Test valid skill names pass validation."""
        from generator.cli.commands import validate_skill_name

        assert validate_skill_name("python-testing") is True
        assert validate_skill_name("code-review") is True
        assert validate_skill_name("test123") is True
        assert validate_skill_name("a") is True  # Single char
        assert validate_skill_name("a" * 64) is True  # Max length

    def test_validate_skill_name_invalid_special_chars(self):
        """Test names with special characters fail validation."""
        from generator.cli.commands import validate_skill_name

        assert validate_skill_name("python@testing") is False
        assert (
            validate_skill_name("code_review") is False
        )  # Underscores should be normalized first
        assert validate_skill_name("test.skill") is False
        assert (
            validate_skill_name("my skill") is False
        )  # Spaces should be normalized first

    def test_validate_skill_name_invalid_length(self):
        """Test names exceeding max length fail validation."""
        from generator.cli.commands import validate_skill_name

        assert validate_skill_name("a" * 65) is False  # Too long
        assert validate_skill_name("") is False  # Empty

    def test_validate_skill_name_invalid_start_end(self):
        """Test names starting/ending with hyphens fail (should be normalized first)."""
        from generator.cli.commands import validate_skill_name

        assert validate_skill_name("-python") is False
        assert validate_skill_name("python-") is False


class TestSkillCommandPatternMatching:
    """Tests for recipe pattern matching in skill command."""

    def test_single_pattern_matches_one_recipe(self, real_project, monkeypatch, capsys):
        """Test single pattern matching one recipe."""
        monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "personetta",
                "skill",
                "test-python-backend",
                "-f",
                "copilot",
                "-n",
                "python-testing",
                "--whatif",
            ],
        )

        from generator.cli.main import main

        exit_code = main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "python-testing" in captured.out.lower()

    def test_wildcard_pattern_matches_multiple(self, real_project, monkeypatch, capsys):
        """Test wildcard pattern matches multiple recipes."""
        monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "personetta",
                "skill",
                "test-*",
                "-f",
                "copilot",
                "-n",
                "testing-toolkit",
                "--whatif",
            ],
        )

        from generator.cli.main import main

        exit_code = main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "testing-toolkit" in captured.out.lower()

    def test_no_pattern_matches_shows_error(self, real_project, monkeypatch, capsys):
        """Test no matches shows helpful error."""
        monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "personetta",
                "skill",
                "nonexistent-recipe-xyz",
                "-f",
                "copilot",
                "-n",
                "test",
            ],
        )

        from generator.cli.main import main

        exit_code = main()

        assert exit_code == 1
        captured = capsys.readouterr()
        output = captured.err
        assert "no recipes matched" in output.lower()


class TestSkillCommandOverwriteBehavior:
    """Tests for overwrite handling in skill command."""

    def test_skill_creates_new_directory(
        self, real_project, tmp_path, monkeypatch, capsys
    ):
        """Test skill creation when directory doesn't exist."""
        monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "personetta",
                "skill",
                "test-python-backend",
                "-f",
                "copilot",
                "-n",
                "python-testing",
                "-t",
                "project",
                str(tmp_path),
            ],
        )

        from generator.cli.main import main

        exit_code = main()

        assert exit_code == 0

        # Check skill directory was created
        skill_dir = tmp_path / ".github" / "skills" / "python-testing"
        assert skill_dir.exists()
        assert (skill_dir / "SKILL.md").exists()
        assert (skill_dir / "README.md").exists()

    def test_force_flag_overwrites_existing(
        self, real_project, tmp_path, monkeypatch, capsys
    ):
        """Test --force flag overwrites existing skill without prompting."""
        monkeypatch.setenv("PERSONETTA_BASE", str(real_project))

        # Create skill first time
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "personetta",
                "skill",
                "test-python-backend",
                "-f",
                "copilot",
                "-n",
                "python-testing",
                "-t",
                "project",
                str(tmp_path),
            ],
        )
        from generator.cli.main import main

        main()

        # Create marker file to verify overwrite
        skill_dir = tmp_path / ".github" / "skills" / "python-testing"
        marker_file = skill_dir / "marker.txt"
        marker_file.write_text("old content")

        # Overwrite with --force
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "personetta",
                "skill",
                "test-python-backend",
                "-f",
                "copilot",
                "-n",
                "python-testing",
                "-t",
                "project",
                str(tmp_path),
                "--force",
            ],
        )
        exit_code = main()

        assert exit_code == 0
        # Marker should be gone (directory was replaced)
        assert not marker_file.exists()
        assert (skill_dir / "SKILL.md").exists()

    def test_prompt_on_existing_without_force(
        self, real_project, tmp_path, monkeypatch, capsys
    ):
        """Test prompt appears for existing skill without --force."""
        monkeypatch.setenv("PERSONETTA_BASE", str(real_project))

        # Create skill first time
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "personetta",
                "skill",
                "test-python-backend",
                "-f",
                "copilot",
                "-n",
                "python-testing",
                "-t",
                "project",
                str(tmp_path),
            ],
        )
        from generator.cli.main import main

        main()

        # Try to create again without --force, simulating 'n' response
        with patch("builtins.input", return_value="n"):
            monkeypatch.setattr(
                sys,
                "argv",
                [
                    "personetta",
                    "skill",
                    "test-python-backend",
                    "-f",
                    "copilot",
                    "-n",
                    "python-testing",
                    "-t",
                    "project",
                    str(tmp_path),
                ],
            )
            exit_code = main()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert (
            "already exists" in captured.out.lower()
            or "overwrite" in captured.out.lower()
        )


class TestSkillCommandWhatIfMode:
    """Tests for --whatif flag in skill command."""

    def test_whatif_shows_plan_no_creation(
        self, real_project, tmp_path, monkeypatch, capsys
    ):
        """Test --whatif shows plan without creating files."""
        monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "personetta",
                "skill",
                "test-python-backend",
                "-f",
                "copilot",
                "-n",
                "python-testing",
                "-t",
                "project",
                str(tmp_path),
                "--whatif",
            ],
        )

        from generator.cli.main import main

        exit_code = main()

        assert exit_code == 0
        captured = capsys.readouterr()
        output = captured.out.lower()
        assert "would generate" in output or "whatif" in output

        # Verify no files created
        skill_dir = tmp_path / ".github" / "skills" / "python-testing"
        assert not skill_dir.exists()


class TestSkillCommandIntegration:
    """Integration tests for skill command end-to-end."""

    def test_skill_generation_creates_all_files(
        self, real_project, tmp_path, monkeypatch
    ):
        """Test skill generation creates all expected files."""
        monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "personetta",
                "skill",
                "test-python-backend",
                "-f",
                "copilot",
                "-n",
                "python-testing",
                "-t",
                "project",
                str(tmp_path),
            ],
        )

        from generator.cli.main import main

        exit_code = main()

        assert exit_code == 0

        # Verify directory structure
        skill_dir = tmp_path / ".github" / "skills" / "python-testing"
        assert skill_dir.exists()
        assert skill_dir.is_dir()

        # Verify files
        assert (skill_dir / "SKILL.md").exists()
        assert (skill_dir / "README.md").exists()
        assert (skill_dir / "references").is_dir()
        assert (skill_dir / "templates").is_dir()

        # Verify SKILL.md has content
        skill_content = (skill_dir / "SKILL.md").read_text()
        assert "name: python-testing" in skill_content
        assert "## When to Use" in skill_content
        assert "## Procedure" in skill_content

    def test_skill_name_auto_conversion(
        self, real_project, tmp_path, monkeypatch, capsys
    ):
        """Test automatic skill name conversion."""
        monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "personetta",
                "skill",
                "test-python-backend",
                "-f",
                "copilot",
                "-n",
                "Python Testing",  # Invalid -> will be converted
                "-t",
                "project",
                str(tmp_path),
            ],
        )

        from generator.cli.main import main

        exit_code = main()

        assert exit_code == 0

        # Should have been converted to python-testing
        skill_dir = tmp_path / ".github" / "skills" / "python-testing"
        assert skill_dir.exists()

        captured = capsys.readouterr()
        assert "converted" in captured.out.lower() or "normalized" in captured.out.lower()

    def test_skill_name_invalid_fails(self, real_project, tmp_path, monkeypatch, capsys):
        """Test invalid skill name that can't be auto-converted fails."""
        monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "personetta",
                "skill",
                "test-python-backend",
                "-f",
                "copilot",
                "-n",
                "python@testing!",  # Invalid chars
                "-t",
                "project",
                str(tmp_path),
            ],
        )

        from generator.cli.main import main

        exit_code = main()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "invalid" in captured.err.lower()


class TestSkillCommand:
    """Tests for skill command."""

    def test_skill_normalizes_name(self, monkeypatch):
        """Test skill normalizes skill names."""
        from generator.cli.commands.skill import _validate_and_normalize_skill_name

        normalized, exit_code = _validate_and_normalize_skill_name("Python Testing")
        assert normalized == "python-testing"
        assert exit_code == 0

    def test_skill_validates_normalized_name(self, capsys, monkeypatch):
        """Test skill validates normalized names."""
        from generator.cli.commands.skill import _validate_and_normalize_skill_name

        # Test truly invalid name (starts with hyphen after normalization)
        normalized, exit_code = _validate_and_normalize_skill_name("-@-invalid-@-")
        assert normalized is None
        assert exit_code == 1

        captured = capsys.readouterr()
        assert "Invalid skill name" in captured.err

    def test_skill_matches_recipes_case_insensitive(self, monkeypatch):
        """Test skill matches recipes case insensitively."""
        from generator.cli.commands.skill import _match_recipes_for_skill

        recipes = [{"name": "Test-Python"}, {"name": "test-csharp"}]

        matched = _match_recipes_for_skill(["TEST-*"], recipes)
        assert len(matched) == 2

    def test_skill_deduplicates_recipe_matches(self, monkeypatch):
        """Test skill deduplicates matched recipes."""
        from generator.cli.commands.skill import _match_recipes_for_skill

        recipes = [{"name": "test-python"}]
        matched = _match_recipes_for_skill(["test-*", "test-python"], recipes)

        assert len(matched) == 1

    def test_skill_whatif_shows_plan(self, tmp_path, capsys, monkeypatch):
        """Test skill --whatif displays plan."""
        from generator.cli.commands.skill import _print_whatif_skill

        matched = [{"name": "test-python"}, {"name": "test-csharp"}]
        skill_dir = tmp_path / "test-skill"

        _print_whatif_skill("test-skill", matched, skill_dir, "copilot")

        captured = capsys.readouterr()
        assert "[WHATIF]" in captured.out
        assert "test-skill" in captured.out

    def test_skill_handles_empty_skill_name(self, capsys, monkeypatch):
        """Test skill handles empty skill name."""
        from generator.cli.commands.skill import _validate_and_normalize_skill_name

        normalized, exit_code = _validate_and_normalize_skill_name("")
        assert normalized is None
        assert exit_code == 1

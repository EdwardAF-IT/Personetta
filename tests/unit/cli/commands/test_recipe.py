"""Tests for recipe command."""

from __future__ import annotations

import argparse
import sys

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


class TestRecipeCommandExists:
    """Tests verifying recipe command is properly registered.

    Note: The recipe command was re-added in Phase 3 refactoring after being temporarily removed.
    It provides useful functionality for generating skills and exporting prompts from recipes.
    """

    def test_recipe_command_in_parser(self, monkeypatch):
        """Verify 'recipe' subparser exists and is properly registered."""
        monkeypatch.setattr(sys, "argv", ["personetta", "-h"])
        from generator.cli.parser import build_parser

        parser = build_parser()
        subparsers_action = None
        for action in parser._actions:
            if hasattr(action, "choices") and action.choices:
                subparsers_action = action
                break

        assert subparsers_action is not None, "Should have subparsers"
        assert (
            "recipe" in subparsers_action.choices
        ), "recipe command should exist in parser"

    def test_recipe_command_has_required_args(self, monkeypatch):
        """Test that 'personetta recipe' subcommand has expected arguments."""
        monkeypatch.setattr(sys, "argv", ["personetta", "recipe", "-h"])
        from generator.cli.parser import build_parser

        parser = build_parser()

        # Should not raise an error - verifies the recipe subcommand exists
        # Help messages cause SystemExit, which is expected behavior
        try:
            parser.parse_args(["recipe", "-h"])
        except SystemExit as e:
            # Exit code 0 means help was displayed successfully
            assert e.code == 0, "Help message should exit with code 0"


class TestRecipeCommand:
    """Tests for recipe command."""

    def test_recipe_prints_warnings(self, capsys, monkeypatch):
        """Test recipe prints warnings from composition."""
        from generator.cli.commands.recipe import _print_warnings

        # Mock ComposeWarning as a dict-like object
        warnings = [
            type(
                "ComposeWarning", (), {"severity": "error", "message": "Critical issue"}
            )(),
            type(
                "ComposeWarning", (), {"severity": "warning", "message": "Minor issue"}
            )(),
        ]

        error_count = _print_warnings(warnings)
        assert error_count == 1

        captured = capsys.readouterr()
        assert "ERROR" in captured.err
        assert "WARNING" in captured.err

    def test_recipe_fails_on_errors(self, tmp_path, capsys, monkeypatch):
        """Test recipe fails when errors detected."""
        from generator.cli.commands.recipe import cmd_recipe

        args = create_mock_args(name="test-python", format="copilot")

        def mock_compose(*a):
            warning = type(
                "ComposeWarning", (), {"severity": "error", "message": "Test error"}
            )()
            return {}, [warning]

        monkeypatch.setattr(
            "generator.cli.commands.recipe.get_base_dir", lambda: tmp_path
        )
        monkeypatch.setattr(
            "generator.cli.commands.recipe._load_and_compose_recipe", mock_compose
        )

        exit_code = cmd_recipe(args)
        assert exit_code == 1

    def test_recipe_install_to_cache(self, tmp_path, monkeypatch):
        """Test recipe --install writes to cache."""
        from generator.cli.commands.recipe import cmd_recipe

        args = create_mock_args(
            name="test-python", format="copilot", install=True, target=None
        )

        install_called = {"value": False}

        def mock_compose(*a):
            return {"name": "test-python"}, []

        def mock_install(*a):
            install_called["value"] = True
            return str(tmp_path / "test-python.md")

        monkeypatch.setattr(
            "generator.cli.commands.recipe.get_base_dir", lambda: tmp_path
        )
        monkeypatch.setattr(
            "generator.cli.commands.recipe._load_and_compose_recipe", mock_compose
        )
        monkeypatch.setattr(
            "generator.cli.commands.recipe._install_to_cache", mock_install
        )

        exit_code = cmd_recipe(args)
        assert exit_code == 0
        assert install_called["value"]

    def test_recipe_writes_to_file(self, tmp_path, monkeypatch):
        """Test recipe --output writes to file."""
        from generator.cli.commands.recipe import cmd_recipe

        output_file = tmp_path / "output.md"
        args = create_mock_args(
            name="test-python", format="copilot", output=str(output_file)
        )

        def mock_compose(*a):
            return {"name": "test-python"}, []

        def mock_format(*a):
            return "# Test Output"

        monkeypatch.setattr(
            "generator.cli.commands.recipe.get_base_dir", lambda: tmp_path
        )
        monkeypatch.setattr(
            "generator.cli.commands.recipe._load_and_compose_recipe", mock_compose
        )
        monkeypatch.setattr("generator.cli.commands.recipe.format_role", mock_format)

        exit_code = cmd_recipe(args)
        assert exit_code == 0
        assert output_file.exists()

    def test_recipe_prints_to_stdout(self, tmp_path, capsys, monkeypatch):
        """Test recipe without --install or --output prints to stdout."""
        from generator.cli.commands.recipe import cmd_recipe

        args = create_mock_args(name="test-python", format="copilot")

        def mock_compose(*a):
            return {"name": "test-python"}, []

        def mock_format(*a):
            return "# Test Output"

        monkeypatch.setattr(
            "generator.cli.commands.recipe.get_base_dir", lambda: tmp_path
        )
        monkeypatch.setattr(
            "generator.cli.commands.recipe._load_and_compose_recipe", mock_compose
        )
        monkeypatch.setattr("generator.cli.commands.recipe.format_role", mock_format)

        exit_code = cmd_recipe(args)
        assert exit_code == 0

        captured = capsys.readouterr()
        assert "# Test Output" in captured.out

    def test_recipe_handles_install_error(self, tmp_path, capsys, monkeypatch):
        """Test recipe handles installation errors."""
        from generator.cli.commands.recipe import cmd_recipe

        args = create_mock_args(name="test-python", format="copilot", install=True)

        def mock_compose(*a):
            return {"name": "test-python"}, []

        def mock_install(*a):
            raise ValueError("Install failed")

        monkeypatch.setattr(
            "generator.cli.commands.recipe.get_base_dir", lambda: tmp_path
        )
        monkeypatch.setattr(
            "generator.cli.commands.recipe._load_and_compose_recipe", mock_compose
        )
        monkeypatch.setattr(
            "generator.cli.commands.recipe._install_to_cache", mock_install
        )

        exit_code = cmd_recipe(args)
        assert exit_code == 1

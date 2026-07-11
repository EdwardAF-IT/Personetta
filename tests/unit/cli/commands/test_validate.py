"""Tests for validate command."""

from __future__ import annotations

import argparse

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


class TestValidateCommand:
    """Tests for validate command."""

    def test_validate_all_files_valid(self, tmp_path, capsys, monkeypatch):
        """Test validate when all files are valid."""
        from generator.cli.commands.validate import cmd_validate

        args = create_mock_args()
        monkeypatch.setattr(
            "generator.cli.commands.validate.get_base_dir", lambda: tmp_path
        )
        monkeypatch.setattr("generator.cli.commands.validate.validate_all", lambda bd: {})

        exit_code = cmd_validate(args)
        assert exit_code == 0

        captured = capsys.readouterr()
        assert "All files valid" in captured.out

    def test_validate_with_errors(self, tmp_path, capsys, monkeypatch):
        """Test validate with validation errors."""
        from generator.cli.commands.validate import cmd_validate

        errors = {"test.yaml": ["Missing required field: name", "Invalid version"]}

        args = create_mock_args()
        monkeypatch.setattr(
            "generator.cli.commands.validate.get_base_dir", lambda: tmp_path
        )
        monkeypatch.setattr(
            "generator.cli.commands.validate.validate_all", lambda bd: errors
        )

        exit_code = cmd_validate(args)
        assert exit_code == 1

        captured = capsys.readouterr()
        assert "2 error(s)" in captured.out
        assert "Missing required field" in captured.out

    def test_validate_shows_file_paths(self, tmp_path, capsys, monkeypatch):
        """Test validate shows file paths with errors."""
        from generator.cli.commands.validate import cmd_validate

        errors = {"recipe1.yaml": ["Error 1"], "recipe2.yaml": ["Error 2"]}

        args = create_mock_args()
        monkeypatch.setattr(
            "generator.cli.commands.validate.get_base_dir", lambda: tmp_path
        )
        monkeypatch.setattr(
            "generator.cli.commands.validate.validate_all", lambda bd: errors
        )

        exit_code = cmd_validate(args)
        assert exit_code == 1

        captured = capsys.readouterr()
        assert "recipe1.yaml" in captured.out
        assert "recipe2.yaml" in captured.out

    def test_validate_counts_total_errors(self, tmp_path, capsys, monkeypatch):
        """Test validate counts total errors correctly."""
        from generator.cli.commands.validate import cmd_validate

        errors = {"file1.yaml": ["Error 1", "Error 2"], "file2.yaml": ["Error 3"]}

        args = create_mock_args()
        monkeypatch.setattr(
            "generator.cli.commands.validate.get_base_dir", lambda: tmp_path
        )
        monkeypatch.setattr(
            "generator.cli.commands.validate.validate_all", lambda bd: errors
        )

        exit_code = cmd_validate(args)
        assert exit_code == 1

        captured = capsys.readouterr()
        assert "3 error(s)" in captured.out
        assert "2 file(s)" in captured.out

    def test_validate_returns_zero_on_success(self, tmp_path, monkeypatch):
        """Test validate returns exit code 0 on success."""
        from generator.cli.commands.validate import cmd_validate

        args = create_mock_args()
        monkeypatch.setattr(
            "generator.cli.commands.validate.get_base_dir", lambda: tmp_path
        )
        monkeypatch.setattr("generator.cli.commands.validate.validate_all", lambda bd: {})

        exit_code = cmd_validate(args)
        assert exit_code == 0

    def test_validate_returns_one_on_failure(self, tmp_path, monkeypatch):
        """Test validate returns exit code 1 on failure."""
        from generator.cli.commands.validate import cmd_validate

        errors = {"test.yaml": ["Error"]}

        args = create_mock_args()
        monkeypatch.setattr(
            "generator.cli.commands.validate.get_base_dir", lambda: tmp_path
        )
        monkeypatch.setattr(
            "generator.cli.commands.validate.validate_all", lambda bd: errors
        )

        exit_code = cmd_validate(args)
        assert exit_code == 1

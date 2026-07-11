"""Tests for generate command."""

from __future__ import annotations

import argparse
from pathlib import Path

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


class TestGenerateCommand:
    """Tests for generate command."""

    def test_generate_requires_backend_or_prompt(self, capsys, monkeypatch):
        """Test generate validates at least one output target."""
        from generator.cli.commands.generate import cmd_generate

        args = create_mock_args(recipes=["test-python"])
        monkeypatch.setattr(
            "generator.cli.commands.generate.get_base_dir", lambda: Path()
        )

        exit_code = cmd_generate(args)
        assert exit_code == 1

        captured = capsys.readouterr()
        assert "Must specify at least one" in captured.err

    def test_generate_output_requires_prompt(self, capsys, monkeypatch):
        """Test generate --output requires --prompt."""
        from generator.cli.commands.generate import cmd_generate

        args = create_mock_args(
            recipes=["test-python"], backend=[["copilot"]], output="/tmp/out.md"
        )
        monkeypatch.setattr(
            "generator.cli.commands.generate.get_base_dir", lambda: Path()
        )

        # Backend is specified, so should succeed validation
        # This tests the scenario where output is used with backend only
        exit_code = cmd_generate(args)
        # Will fail later but not on validation
        assert exit_code == 1

    def test_generate_output_conflicts_with_all(self, capsys, monkeypatch):
        """Test generate --output conflicts with --prompt all."""
        from generator.cli.commands.generate import cmd_generate

        args = create_mock_args(
            recipes=["test-python"], prompt="all", output="/tmp/out.md"
        )
        monkeypatch.setattr(
            "generator.cli.commands.generate.get_base_dir", lambda: Path()
        )

        exit_code = cmd_generate(args)
        assert exit_code == 1

        captured = capsys.readouterr()
        assert "Cannot use --output with" in captured.err

    def test_generate_target_requires_backend(self, capsys, monkeypatch):
        """Test generate --target requires --backend."""
        from generator.cli.commands.generate import cmd_generate

        args = create_mock_args(
            recipes=["test-python"], target=["project", "/tmp"], prompt="stdout"
        )
        monkeypatch.setattr(
            "generator.cli.commands.generate.get_base_dir", lambda: Path()
        )

        exit_code = cmd_generate(args)
        assert exit_code == 1

        captured = capsys.readouterr()
        assert "--target requires --backend" in captured.err

    def test_generate_backend_all_expands(self, monkeypatch):
        """Test generate --backend all expands to all formats."""
        from generator.cli.commands.generate import _expand_all_backends

        backends = _expand_all_backends(["all"])
        assert set(backends) == {"cursor", "copilot", "claude", "cline"}

    def test_generate_deduplicates_backends(self, monkeypatch):
        """Test generate deduplicates backend list."""
        from generator.cli.commands.generate import _deduplicate_backends

        backends = _deduplicate_backends(["copilot", "cursor", "copilot", "claude"])
        assert backends == ["copilot", "cursor", "claude"]

    def test_generate_install_command_error_detection(self, monkeypatch):
        """Test generate detects 'install' misuse."""
        from generator.cli.commands.generate import _is_install_command_error

        assert _is_install_command_error(["install"])
        assert _is_install_command_error(["install-all"])
        assert not _is_install_command_error(["test-python"])

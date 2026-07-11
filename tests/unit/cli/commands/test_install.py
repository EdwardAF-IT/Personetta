"""Tests for install command."""

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


class TestInstallCommand:
    """Tests for install command."""

    def test_install_requires_format(self, capsys, monkeypatch):
        """Test install validates format is required."""
        from generator.cli.commands.install import cmd_install

        args = create_mock_args(patterns=["*"], format=None)
        monkeypatch.setattr("generator.cli.commands.install.get_base_dir", lambda: Path())

        # This should fail because format is None
        with pytest.raises(RuntimeError, match="Unhandled install format"):
            cmd_install(args)

    def test_install_matches_recipes_case_insensitive(self, tmp_path, monkeypatch):
        """Test install pattern matching is case insensitive."""
        from generator.cli.commands.install import _match_recipes_for_install

        recipes = [
            {"name": "Test-Python", "path": "test.yaml"},
            {"name": "test-csharp", "path": "test2.yaml"},
        ]

        matched = _match_recipes_for_install(["TEST-*"], recipes)
        assert len(matched) == 2

    def test_install_no_matches_returns_empty(self, monkeypatch):
        """Test install with no pattern matches."""
        from generator.cli.commands.install import _match_recipes_for_install

        recipes = [{"name": "test-python", "path": "test.yaml"}]
        matched = _match_recipes_for_install(["nonexistent-*"], recipes)

        assert len(matched) == 0

    def test_install_whatif_shows_plan(self, tmp_path, capsys, monkeypatch):
        """Test install --whatif displays plan."""
        from generator.cli.commands.install import _print_whatif_install

        recipe_names = ["test-python", "test-csharp"]
        _print_whatif_install(recipe_names, "copilot", tmp_path)

        captured = capsys.readouterr()
        assert "[WHATIF]" in captured.out
        assert "test-python" in captured.out
        assert "test-csharp" in captured.out

    def test_install_deduplicates_patterns(self, monkeypatch):
        """Test install deduplicates matching recipes."""
        from generator.cli.commands.install import _match_recipes_for_install

        recipes = [{"name": "test-python", "path": "test.yaml"}]
        # Match same recipe with multiple patterns
        matched = _match_recipes_for_install(["test-*", "test-python"], recipes)

        assert len(matched) == 1

    def test_install_prints_installed_recipes(self, tmp_path, capsys, monkeypatch):
        """Test install prints installed recipe list."""
        from generator.cli.commands.install import _print_installed_recipes

        ok = ["test-python", "test-csharp"]
        cache_root = tmp_path / "cache"
        cache_root.mkdir()

        _print_installed_recipes(ok, cache_root)

        captured = capsys.readouterr()
        assert "test-python" in captured.out
        assert "test-csharp" in captured.out

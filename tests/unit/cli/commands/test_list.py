"""Tests for list command."""

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


class TestListCommand:
    """Tests for list command."""

    def test_list_normalizes_empty_patterns(self, monkeypatch):
        """Test list normalizes empty patterns to wildcard."""
        from generator.cli.commands.list import _normalize_patterns

        patterns = _normalize_patterns(None)
        assert patterns == ["*"]

        patterns = _normalize_patterns([])
        assert patterns == ["*"]

    def test_list_normalizes_all_to_wildcard(self, monkeypatch):
        """Test list converts 'all' to wildcard."""
        from generator.cli.commands.list import _normalize_patterns

        patterns = _normalize_patterns(["all"])
        assert patterns == ["*"]

    def test_list_filters_case_insensitive(self, monkeypatch):
        """Test list filters are case insensitive."""
        from generator.cli.commands.list import _filter_by_patterns

        items = [{"name": "Test-Python"}, {"name": "test-csharp"}]

        filtered = _filter_by_patterns(items, ["TEST-*"])
        assert len(filtered) == 2

    def test_list_wildcard_returns_all(self, monkeypatch):
        """Test list with wildcard returns all items."""
        from generator.cli.commands.list import _filter_by_patterns

        items = [{"name": "test-1"}, {"name": "test-2"}]
        filtered = _filter_by_patterns(items, ["*"])

        assert len(filtered) == 2

    def test_list_deduplicates_matches(self, monkeypatch):
        """Test list deduplicates items matched by multiple patterns."""
        from generator.cli.commands.list import _filter_by_patterns

        items = [{"name": "test-python"}]
        filtered = _filter_by_patterns(items, ["test-*", "test-python"])

        assert len(filtered) == 1

    def test_list_defaults_to_both_roles_and_recipes(
        self, real_project_module, monkeypatch
    ):
        """Test list shows both roles and recipes by default."""
        from generator.cli.commands.list import cmd_list

        args = create_mock_args()
        monkeypatch.setattr(
            "generator.cli.commands.list.get_base_dir", lambda: real_project_module
        )

        exit_code = cmd_list(args)
        assert exit_code == 0

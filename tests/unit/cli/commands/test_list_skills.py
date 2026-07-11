"""Tests for list_skills command."""

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


class TestListSkillsCommand:
    """Tests for list_skills command."""

    def test_list_skills_specific_format(self, monkeypatch):
        """Test list_skills with specific format."""
        from generator.cli.commands.list_skills import _get_formats_to_show

        args = create_mock_args(format="copilot")
        formats = _get_formats_to_show(args)

        assert formats == ["copilot"]

    def test_list_skills_all_formats(self, monkeypatch):
        """Test list_skills defaults to all formats."""
        from generator.cli.commands.list_skills import _get_formats_to_show

        args = argparse.Namespace(format=None)
        formats = _get_formats_to_show(args)

        assert formats == ["copilot", "claude", "cursor", "cline"]

    def test_list_skills_truncates_long_descriptions(self, monkeypatch):
        """Test list_skills truncates long descriptions."""
        from generator.cli.commands.list_skills import _format_description

        long_desc = "x" * 100
        truncated = _format_description(long_desc, max_length=80)

        assert len(truncated) == 80
        assert truncated.endswith("...")

    def test_list_skills_preserves_short_descriptions(self, monkeypatch):
        """Test list_skills preserves short descriptions."""
        from generator.cli.commands.list_skills import _format_description

        short_desc = "Short description"
        result = _format_description(short_desc, max_length=80)

        assert result == short_desc

    def test_list_skills_counts_total_skills(self, monkeypatch):
        """Test list_skills counts skills correctly."""
        from generator.cli.commands.list_skills import _count_total_skills

        catalog = {
            "skills": {"copilot": {"skill1": {}, "skill2": {}}, "claude": {"skill3": {}}}
        }

        total = _count_total_skills(catalog, ["copilot", "claude"])
        assert total == 3

    def test_list_skills_refresh_flag_triggers_refresh(self, tmp_path, monkeypatch):
        """Test list_skills --refresh triggers catalog refresh."""
        from generator.cli.commands.list_skills import cmd_list_skills

        refresh_called = {"value": False}

        def mock_refresh(*args):
            refresh_called["value"] = True

        def mock_load_catalog(p):
            return {"skills": {}, "last_updated": "2024-01-01"}

        def mock_get_catalog_path():
            return tmp_path / "catalog.json"

        args = argparse.Namespace(refresh=True, format=None)
        monkeypatch.setattr("generator.skill_catalog.refresh_all_catalogs", mock_refresh)
        monkeypatch.setattr("generator.skill_catalog.load_catalog", mock_load_catalog)
        monkeypatch.setattr(
            "generator.skill_catalog.get_catalog_path", mock_get_catalog_path
        )

        cmd_list_skills(args)
        assert refresh_called["value"]

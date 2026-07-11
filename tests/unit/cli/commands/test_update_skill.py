"""Tests for update_skill command."""

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


class TestUpdateSkillCommand:
    """Tests for update_skill command."""

    def test_update_skill_validates_args(self, capsys, monkeypatch):
        """Test update_skill validates arguments."""
        from generator.cli.commands.update_skill import _validate_update_args

        # Missing both --all and name
        args = create_mock_args(all=False, name=None)
        exit_code = _validate_update_args(args)

        assert exit_code == 1

    def test_update_skill_requires_format_with_name(self, capsys, monkeypatch):
        """Test update_skill requires --format when updating specific skill."""
        from generator.cli.commands.update_skill import _validate_update_args

        args = create_mock_args(all=False, name="test-skill", format=None)
        exit_code = _validate_update_args(args)

        assert exit_code == 1

    def test_update_skill_whatif_shows_plan(self, tmp_path, monkeypatch):
        """Test update_skill --whatif displays plan."""
        from generator.cli.commands.update_skill import _check_and_confirm_stale_updates

        stale = [{"skill_name": "test-skill", "reason": "Recipe updated"}]

        result = _check_and_confirm_stale_updates(stale, "copilot", False, True)
        assert result is False  # Should not proceed in whatif mode

    def test_update_skill_force_skips_confirmation(self, tmp_path, monkeypatch):
        """Test update_skill --force skips confirmation."""
        from generator.cli.commands.update_skill import _check_and_confirm_stale_updates

        stale = [{"skill_name": "test-skill", "reason": "Recipe updated"}]

        result = _check_and_confirm_stale_updates(stale, "copilot", True, False)
        assert result is True

    def test_update_skill_loads_current_recipes(self, monkeypatch):
        """Test update_skill loads all current recipes."""
        from generator.cli.commands.update_skill import _load_all_current_recipes

        monkeypatch.setattr(
            "generator.cli.commands.update_skill.list_recipes",
            lambda base_dir: [{"name": "test-recipe"}],
        )
        monkeypatch.setattr(
            "generator.cli.commands.update_skill.load_recipe",
            lambda name, base_dir: {"name": name, "version": "1.0"},
        )

        recipes = _load_all_current_recipes()
        assert "test-recipe" in recipes

    def test_update_skill_user_cancels_update(self, tmp_path, monkeypatch):
        """Test update_skill handles user cancellation."""
        from generator.cli.commands.update_skill import _check_and_confirm_stale_updates

        stale = [{"skill_name": "test-skill", "reason": "Recipe updated"}]

        monkeypatch.setattr("builtins.input", lambda _: "no")
        result = _check_and_confirm_stale_updates(stale, "copilot", False, False)

        assert result is False

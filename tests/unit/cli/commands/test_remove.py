"""Tests for remove command with glob pattern matching."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

import pytest


@pytest.fixture
def mock_input_yes(monkeypatch):
    """Mock input to always confirm with 'yes'."""
    monkeypatch.setattr("builtins.input", lambda _: "yes")


@pytest.fixture
def mock_input_no(monkeypatch):
    """Mock input to always cancel with 'no'."""
    monkeypatch.setattr("builtins.input", lambda _: "no")


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


# =============================================================================
# Unit Tests
# =============================================================================

pytestmark_unit = [pytest.mark.unit, pytest.mark.cli, pytest.mark.readonly]


@pytest.mark.unit
@pytest.mark.cli
@pytest.mark.readonly
class TestRemoveCommand:
    """Unit tests for remove command."""

    def test_remove_matches_case_insensitive(self, monkeypatch):
        """Test remove pattern matching is case insensitive."""
        from generator.cli.commands.remove import _match_recipes_by_patterns

        cached = ["Test-Python", "test-csharp", "TEST-JAVA"]
        matched = _match_recipes_by_patterns(cached, ["test-*"])

        assert len(matched) == 3

    def test_remove_deduplicates_matches(self, monkeypatch):
        """Test remove deduplicates recipes matched by multiple patterns."""
        from generator.cli.commands.remove import _match_recipes_by_patterns

        cached = ["test-python"]
        matched = _match_recipes_by_patterns(cached, ["test-*", "test-python"])

        assert len(matched) == 1

    def test_remove_whatif_skips_removal(self, tmp_path, capsys, monkeypatch):
        """Test remove --whatif displays plan without removing."""
        from generator.cli.commands.remove import cmd_remove

        args = create_mock_args(patterns=["test-*"], format="copilot", whatif=True)

        monkeypatch.setattr(
            "generator.cli.commands.remove._get_cached_recipes_and_state",
            lambda f, t: (["test-python"], tmp_path, None),
        )

        exit_code = cmd_remove(args)
        assert exit_code == 0

        captured = capsys.readouterr()
        assert "[WHATIF]" in captured.out

    def test_remove_yes_flag_skips_confirmation(self, tmp_path, monkeypatch):
        """Test remove --yes skips user confirmation."""
        from generator.cli.commands.remove import _confirm_removal

        args = create_mock_args(yes=True)
        result = _confirm_removal(args, tmp_path, 1)

        assert result is True

    def test_remove_handles_keyboard_interrupt(self, tmp_path, monkeypatch):
        """Test remove handles keyboard interrupt gracefully."""
        from generator.cli.commands.remove import _prompt_user_confirmation

        def mock_input(_):
            raise KeyboardInterrupt()

        monkeypatch.setattr("builtins.input", mock_input)
        result = _prompt_user_confirmation()

        assert result is False

    def test_remove_handles_eof_error(self, tmp_path, monkeypatch):
        """Test remove handles EOF gracefully."""
        from generator.cli.commands.remove import _prompt_user_confirmation

        def mock_input(_):
            raise EOFError()

        monkeypatch.setattr("builtins.input", mock_input)
        result = _prompt_user_confirmation()

        assert result is False


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.integration
class TestRemovePatternMatching:
    """Integration tests for pattern matching and filtering logic."""

    def test_remove_single_exact_match(self, real_project, tmp_path, mock_input_yes):
        """Remove a single recipe by exact name."""
        target = tmp_path / "remove_exact"
        # Install all recipes first
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        # Remove one specific recipe
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "remove",
                "test-python-backend",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
                "--yes",
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "test-python-backend" in result.stdout
        assert "Removed: test-python-backend" in result.stdout

        # Verify file is gone
        cache_dir = target / ".personetta" / "cursor-recipes"
        assert not (cache_dir / "test-python-backend.md").exists()

    def test_remove_wildcard_pattern(self, real_project, tmp_path, mock_input_yes):
        """Remove multiple recipes matching a wildcard pattern."""
        target = tmp_path / "remove_pattern"
        # Install all recipes
        subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )

        # Remove all test recipes
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "remove",
                "test-*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
                "--yes",
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        # Verify test recipes are gone but others remain
        cache_dir = target / ".personetta" / "cursor-recipes"
        remaining = list(cache_dir.glob("*.md"))
        remaining_names = {p.stem for p in remaining}

        assert not any(n.startswith("test-") for n in remaining_names)
        assert len(remaining_names) > 0  # Some recipes should remain

    def test_remove_multiple_patterns(self, real_project, tmp_path, mock_input_yes):
        """Remove recipes matching multiple patterns."""
        target = tmp_path / "remove_multi"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )

        # Remove test recipes AND python recipes
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "remove",
                "test-*",
                "*python*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
                "--yes",
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        # Verify both patterns were matched
        cache_dir = target / ".personetta" / "cursor-recipes"
        remaining = list(cache_dir.glob("*.md"))
        remaining_names = {p.stem for p in remaining}

        assert not any(n.startswith("test-") for n in remaining_names)
        assert not any("python" in n for n in remaining_names)

    def test_remove_case_insensitive_pattern(
        self, real_project, tmp_path, mock_input_yes
    ):
        """Pattern matching should be case-insensitive."""
        target = tmp_path / "remove_case"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )

        # Use uppercase pattern
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "remove",
                "TEST-*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
                "--yes",
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        # Lowercase recipe names should still be removed
        cache_dir = target / ".personetta" / "cursor-recipes"
        remaining_names = {p.stem for p in cache_dir.glob("*.md")}
        assert not any(n.startswith("test-") for n in remaining_names)

    def test_remove_no_matches_error(self, real_project, tmp_path):
        """Error when no recipes match the pattern."""
        target = tmp_path / "remove_nomatch"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )

        # Try to remove non-existent pattern
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "remove",
                "does-not-exist-*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
                "--yes",
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "No installed cursor recipes matched patterns" in result.stderr
        assert "Installed cursor recipes:" in result.stderr  # Shows available recipes

    def test_remove_empty_cache_error(self, real_project, tmp_path):
        """Error when trying to remove from empty cache."""
        target = tmp_path / "remove_empty"
        target.mkdir(parents=True)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "remove",
                "*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
                "--yes",
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "No cursor recipes installed" in result.stderr


@pytest.mark.integration
class TestActiveRecipeHandling:
    """Integration tests for active recipe handling when removed or kept."""

    def test_remove_active_recipe_sets_new_active(
        self, real_project, tmp_path, mock_input_yes
    ):
        """When active recipe is removed, set active to first remaining (alphabetically)."""
        target = tmp_path / "remove_active"
        # Install all recipes
        subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )

        # Default active is first alphabetically - likely "design-*"
        state_file = target / ".personetta" / "cursor-active.json"
        state = json.loads(state_file.read_text())
        original_active = state["active_recipe"]

        # Remove the active recipe
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "remove",
                original_active,
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
                "--yes",
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Active persona changed:" in result.stdout
        assert original_active in result.stdout

        # Verify new active is set
        new_state = json.loads(state_file.read_text())
        assert new_state["active_recipe"] != original_active
        assert new_state["active_recipe"]  # Not empty

    def test_remove_non_active_recipe_keeps_active(
        self, real_project, tmp_path, mock_input_yes
    ):
        """When removing non-active recipe, active should stay unchanged."""
        target = tmp_path / "remove_keep_active"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )

        state_file = target / ".personetta" / "cursor-active.json"
        state = json.loads(state_file.read_text())
        original_active = state["active_recipe"]

        # Find a recipe that's NOT active
        cache_dir = target / ".personetta" / "cursor-recipes"
        all_recipes = [p.stem for p in cache_dir.glob("*.md")]
        non_active = [r for r in all_recipes if r != original_active][0]

        # Remove non-active recipe
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "remove",
                non_active,
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
                "--yes",
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Active persona changed" not in result.stdout

        # Verify active unchanged
        new_state = json.loads(state_file.read_text())
        assert new_state["active_recipe"] == original_active

    def test_remove_all_recipes_clears_active(
        self, real_project, tmp_path, mock_input_yes
    ):
        """When all recipes removed, active should be cleared."""
        target = tmp_path / "remove_all"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )

        # Remove all recipes
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "remove",
                "*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
                "--yes",
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Active persona cleared (no recipes remain)" in result.stdout

        # Verify active is empty
        state_file = target / ".personetta" / "cursor-active.json"
        state = json.loads(state_file.read_text())
        assert state["active_recipe"] == ""


@pytest.mark.integration
class TestConfirmationPrompt:
    """Integration tests for confirmation prompt behavior."""

    def test_confirmation_yes_proceeds(self, real_project, tmp_path, mock_input_yes):
        """Confirming with 'yes' proceeds with removal."""
        target = tmp_path / "confirm_yes"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "test-python-backend",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )

        # Don't use --yes flag, rely on mocked input
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "remove",
                "test-python-backend",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
            input="yes\n",
        )
        assert result.returncode == 0
        assert "Removed: test-python-backend" in result.stdout

    def test_confirmation_no_cancels(self, real_project, tmp_path):
        """Cancelling with 'no' aborts removal."""
        target = tmp_path / "confirm_no"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "test-python-backend",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "remove",
                "test-python-backend",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
            input="no\n",
        )
        assert result.returncode == 0
        assert "Cancelled" in result.stdout

        # Verify file still exists
        cache_dir = target / ".personetta" / "cursor-recipes"
        assert (cache_dir / "test-python-backend.md").exists()

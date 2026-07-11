"""Integration tests for CLI commands - flags, formats, and end-to-end behavior.

These tests verify CLI command integration, short flags, --whatif functionality,
and format variations. Restored during Phase 10 reorganization (were accidentally
excluded from unit test split).

Original test coverage:
- Short flags, whatif, end-to-end commands
- Format variations, UI feedback, yes flag
- Skill generation with options
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.cli,
    pytest.mark.requires_real_project,
    pytest.mark.xdist_group(name="cli_integration"),
]


@pytest.fixture
def mock_input_yes(monkeypatch):
    """Mock input to always confirm with 'yes'."""
    monkeypatch.setattr("builtins.input", lambda _: "yes")


class TestShortFormFlags:
    """Tests for short-form flag aliases (-f, -t, -n, -w)."""

    def test_install_short_format_flag(self, real_project, tmp_path, monkeypatch):
        """Test install -f works same as --format."""
        monkeypatch.setenv("PERSONETTA_BASE", str(real_project))

        # Test with short form
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "personetta",
                "install",
                "test-python-backend",
                "-f",
                "copilot",
                "-t",
                "project",
                str(tmp_path),
            ],
        )
        from generator.cli.main import main

        exit_code = main()
        assert exit_code == 0

    def test_set_active_short_format_flag(self, real_project, tmp_path, monkeypatch):
        """Test set-active -f works same as --format."""
        # First install a recipe
        monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "personetta",
                "install",
                "test-python-backend",
                "-f",
                "copilot",
                "-t",
                "project",
                str(tmp_path),
            ],
        )
        from generator.cli.main import main

        main()

        # Then test set-active with short form
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "personetta",
                "set-active",
                "test-python-backend",
                "-f",
                "copilot",
                "-t",
                "project",
                str(tmp_path),
            ],
        )

        exit_code = main()
        assert exit_code == 0

    def test_remove_short_format_flag(self, real_project, tmp_path, monkeypatch):
        """Test remove -f works same as --format."""
        # First install something
        monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "personetta",
                "install",
                "test-python-backend",
                "-f",
                "copilot",
                "-t",
                "project",
                str(tmp_path),
            ],
        )
        from generator.cli.main import main

        main()

        # Then test remove with short form and -y to skip prompt
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "personetta",
                "remove",
                "test-python-backend",
                "-f",
                "copilot",
                "-t",
                "project",
                str(tmp_path),
                "-y",
            ],
        )

        exit_code = main()
        assert exit_code == 0

    def test_install_short_target_flag(self, real_project, tmp_path, monkeypatch):
        """Test install -t works same as --target."""
        monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "personetta",
                "install",
                "test-python-backend",
                "-f",
                "copilot",
                "-t",
                "project",
                str(tmp_path),  # Short form
            ],
        )
        from generator.cli.main import main

        exit_code = main()
        assert exit_code == 0


class TestWhatIfFlag:
    """Tests for --whatif flag (dry-run mode)."""

    def test_install_whatif_shows_plan_without_installing(
        self, real_project, tmp_path, capsys, monkeypatch
    ):
        """Test install --whatif shows what would be installed without actually installing."""
        monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "personetta",
                "install",
                "test-python-backend",
                "-f",
                "copilot",
                "-t",
                "project",
                str(tmp_path),
                "--whatif",
            ],
        )
        from generator.cli.main import main

        exit_code = main()

        # Should succeed
        assert exit_code == 0

        # Should show what would be done
        captured = capsys.readouterr()
        output = captured.out + captured.err
        assert (
            "would install" in output.lower()
            or "whatif" in output.lower()
            or "dry" in output.lower()
        )

        # Verify nothing was actually installed
        copilot_cache = tmp_path / ".personetta" / "copilot-recipes"
        if copilot_cache.exists():
            # Cache dir may exist but should be empty or not contain our recipe
            installed = list(copilot_cache.glob("*"))
            assert len(installed) == 0 or not any(
                "test-python" in str(p) for p in installed
            )

    def test_remove_whatif_shows_plan_without_removing(
        self, real_project, tmp_path, capsys, monkeypatch
    ):
        """Test remove --whatif shows what would be removed without actually removing."""
        # First install something
        monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "personetta",
                "install",
                "test-python-backend",
                "-f",
                "copilot",
                "-t",
                "project",
                str(tmp_path),
            ],
        )
        from generator.cli.main import main

        main()

        # Verify it was installed
        copilot_cache = tmp_path / ".personetta" / "copilot-recipes"
        assert copilot_cache.exists()
        installed_before = list(copilot_cache.glob("*"))
        assert len(installed_before) > 0

        # Now test remove with --whatif
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "personetta",
                "remove",
                "test-python-backend",
                "-f",
                "copilot",
                "-t",
                "project",
                str(tmp_path),
                "--whatif",
            ],
        )

        exit_code = main()
        assert exit_code == 0

        # Should show what would be removed
        captured = capsys.readouterr()
        output = captured.out + captured.err
        assert (
            "would remove" in output.lower()
            or "whatif" in output.lower()
            or "dry" in output.lower()
        )

        # Verify nothing was actually removed
        installed_after = list(copilot_cache.glob("*"))
        assert len(installed_after) == len(installed_before)

    def test_set_active_whatif_shows_plan_without_changing(
        self, real_project, tmp_path, capsys, monkeypatch
    ):
        """Test set-active --whatif shows what would change without actually changing."""
        # First install a recipe
        monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "personetta",
                "install",
                "test-python-backend",
                "-f",
                "copilot",
                "-t",
                "project",
                str(tmp_path),
            ],
        )
        from generator.cli.main import main

        main()

        # Get initial state
        active_file = (
            tmp_path / ".copilot" / "instructions" / "personetta-active.instructions.md"
        )
        initial_content = active_file.read_text() if active_file.exists() else None

        # Test set-active with --whatif
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "personetta",
                "set-active",
                "test-python-backend",
                "-f",
                "copilot",
                "-t",
                "project",
                str(tmp_path),
                "--whatif",
            ],
        )

        exit_code = main()
        assert exit_code == 0

        # Should show what would be done
        captured = capsys.readouterr()
        output = captured.out + captured.err
        assert (
            "would" in output.lower()
            or "whatif" in output.lower()
            or "dry" in output.lower()
        )

        # Verify state didn't change
        final_content = active_file.read_text() if active_file.exists() else None
        assert final_content == initial_content


class TestEndToEndCommands:
    """Verify complete CLI command workflows work end-to-end."""

    def test_list_command_still_works(self, real_project, monkeypatch):
        """Sanity check that list command wasn't broken."""
        monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
        monkeypatch.setattr(sys, "argv", ["personetta", "list"])
        from generator.cli.main import main

        exit_code = main()
        assert exit_code == 0

    def test_validate_command_still_works(self, real_project, monkeypatch):
        """Sanity check that validate command wasn't broken."""
        monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
        monkeypatch.setattr(sys, "argv", ["personetta", "validate"])
        from generator.cli.main import main

        exit_code = main()
        assert exit_code == 0

    def test_generate_command_still_works(self, real_project, monkeypatch):
        """Sanity check that generate command wasn't broken."""
        monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
        # Use simple prompt generation to avoid path complexity
        monkeypatch.setattr(
            sys,
            "argv",
            ["personetta", "generate", "test-python-backend", "--prompt", "stdout"],
        )
        from generator.cli.main import main

        exit_code = main()
        assert exit_code == 0


class TestYesFlagAndConfirmation:
    """Tests for --yes flag to skip confirmation prompts."""

    def test_yes_flag_skips_confirmation(self, real_project, tmp_path):
        """--yes flag skips confirmation prompt."""
        target = tmp_path / "yes_flag"
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

        # Should not prompt
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
        assert "Proceed with removal?" not in result.stdout
        assert "Removed: test-python-backend" in result.stdout


class TestMultiFormat:
    """Test remove works correctly for all formats."""

    def test_remove_copilot_format(self, real_project, tmp_path, mock_input_yes):
        """Remove recipes for Copilot format."""
        target = tmp_path / "remove_copilot"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*",
                "--format",
                "copilot",
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
                "test-*",
                "--format",
                "copilot",
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

        cache_dir = target / ".personetta" / "copilot-recipes"
        remaining_names = {p.stem for p in cache_dir.glob("*.md")}
        assert not any(n.startswith("test-") for n in remaining_names)

    def test_remove_claude_format(self, real_project, tmp_path, mock_input_yes):
        """Remove recipes for Claude format."""
        target = tmp_path / "remove_claude"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*",
                "--format",
                "claude",
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
                "test-*",
                "--format",
                "claude",
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

        cache_dir = target / ".personetta" / "claude-recipes"
        remaining_names = {p.stem for p in cache_dir.glob("*.md")}
        assert not any(n.startswith("test-") for n in remaining_names)

    def test_remove_cline_format(self, real_project, tmp_path, mock_input_yes):
        """Remove recipes for Cline format."""
        target = tmp_path / "remove_cline"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*",
                "--format",
                "cline",
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
                "test-*",
                "--format",
                "cline",
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

        cache_dir = target / ".personetta" / "cline-recipes"
        remaining_names = {p.stem for p in cache_dir.glob("*.md")}
        assert not any(n.startswith("test-") for n in remaining_names)


class TestRouterRegeneration:
    """Test that router is regenerated after removal."""

    def test_router_regenerated_after_removal(
        self, real_project, tmp_path, mock_input_yes
    ):
        """Router file should be updated with remaining recipes."""
        target = tmp_path / "remove_router"
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

        # Get initial router content
        router_file = target / ".cursor" / "rules" / "personetta-router.md"
        initial_router = router_file.read_text(encoding="utf-8")
        assert "test-python-backend" in initial_router

        # Remove test recipes
        subprocess.run(
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

        # Check router was updated
        updated_router = router_file.read_text(encoding="utf-8")
        assert "test-python-backend" not in updated_router
        # Router should still exist and be valid
        assert "personetta set-active" in updated_router


class TestUIFeedback:
    """Test CLI output messages are clear and helpful."""

    def test_shows_recipes_to_be_removed(self, real_project, tmp_path, mock_input_yes):
        """Should list recipes before removal."""
        target = tmp_path / "remove_list"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*python*",
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

        # Should show what's being removed
        assert "recipe(s) will be removed:" in result.stdout
        assert "python" in result.stdout.lower()

    def test_shows_active_marker_in_list(self, real_project, tmp_path, mock_input_yes):
        """Should mark active recipe in removal list."""
        target = tmp_path / "remove_marker"
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
        active = state["active_recipe"]

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "remove",
                active,
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
        assert "(active)" in result.stdout

    def test_shows_summary_count(self, real_project, tmp_path, mock_input_yes):
        """Shows count of removed recipes."""
        target = tmp_path / "remove_count"
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
        assert "Removed" in result.stdout
        assert "recipe(s)" in result.stdout


class TestSkillGeneration:
    """Tests for skill generation with different options."""

    def test_skill_generation_different_formats(
        self, real_project, tmp_path, monkeypatch
    ):
        """Test skill generation for different formats."""
        monkeypatch.setenv("PERSONETTA_BASE", str(real_project))

        for format_name, expected_subdir in [
            ("copilot", ".github/skills"),
            ("claude", ".claude/skills"),
            ("cursor", ".cursor/skills"),
        ]:
            monkeypatch.setattr(
                sys,
                "argv",
                [
                    "personetta",
                    "skill",
                    "test-python-backend",
                    "-f",
                    format_name,
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

            # Verify format-specific directory
            skill_dir = tmp_path / expected_subdir / "python-testing"
            assert skill_dir.exists(), f"Expected {skill_dir} for format {format_name}"
            assert (skill_dir / "SKILL.md").exists()

    def test_skill_generation_workspace_flag(self, real_project, tmp_path, monkeypatch):
        """Test skill generation with -w workspace flag."""
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
                "-w",
                "-t",
                "project",
                str(tmp_path),
            ],
        )

        from generator.cli.main import main

        exit_code = main()

        assert exit_code == 0

        # With -w, should use workspace directory
        skill_dir = tmp_path / ".github" / "skills" / "python-testing"
        assert skill_dir.exists()
        assert (skill_dir / "SKILL.md").exists()

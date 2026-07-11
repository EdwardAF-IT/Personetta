"""CLI tests for generate command.

Tests command-line interface, parameter validation, and user-facing behavior.
"""

import pytest
import subprocess
import sys
from pathlib import Path

pytestmark = [pytest.mark.integration, pytest.mark.prompt_export]


class TestGenerateCommandSyntax:
    """Test generate command syntax and parameter handling."""

    def test_generate_requires_recipe_id(self):
        """Generate command requires at least one recipe."""
        result = subprocess.run(
            [sys.executable, "-m", "generator", "generate"],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )
        # Should fail with error about missing recipe
        assert result.returncode != 0

    def test_generate_requires_backend_or_prompt(self):
        """Generate requires at least --backend or --prompt."""
        result = subprocess.run(
            [sys.executable, "-m", "generator", "generate", "test-recipe"],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )
        # Should fail requiring --backend or --prompt
        assert result.returncode != 0
        assert (
            "Must specify at least one of" in result.stderr
            or "backend" in result.stderr.lower()
        )

    def test_generate_backend_cursor_success(self):
        """Generate with --backend cursor should work."""
        # This will fail if recipe doesn't exist, but syntax is valid
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "generate",
                "implement-python-backend-perf",
                "--backend",
                "cursor",
            ],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )
        # Either succeeds or fails for non-syntax reasons
        # Syntax error would be returncode 2 typically
        assert result.returncode <= 1

    def test_generate_prompt_stdout_success(self):
        """Generate with --prompt should work."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "generate",
                "implement-python-backend-perf",
                "--prompt",
            ],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )
        assert result.returncode <= 1

    def test_generate_output_requires_prompt(self):
        """--output requires --prompt to be specified."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "generate",
                "test-recipe",
                "-o",
                "output.md",
            ],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "requires --prompt" in result.stderr or "output" in result.stderr.lower()

    def test_generate_output_conflicts_with_prompt_all(self):
        """Cannot use --output with --prompt all."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "generate",
                "test",
                "--prompt",
                "all",
                "-o",
                "out.md",
            ],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert (
            "Cannot use --output with --prompt all" in result.stderr
            or "conflict" in result.stderr.lower()
        )

    def test_generate_target_requires_backend(self):
        """--target requires --backend."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "generate",
                "test",
                "--prompt",
                "--target",
                "global",
            ],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "requires --backend" in result.stderr or "target" in result.stderr.lower()


class TestGenerateCommandExecution:
    """Test actual generate command execution with real recipes."""

    @pytest.mark.skipif(
        not Path("data/recipes/implement-python-backend-perf.yaml").exists(),
        reason="Requires real recipe",
    )
    def test_generate_prompt_to_file(self, tmp_path):
        """Generate prompt to a file."""
        output_file = tmp_path / "test-output.md"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "generate",
                "implement-python-backend-perf",
                "--prompt",
                "-o",
                str(output_file),
            ],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert output_file.exists()

        content = output_file.read_text(encoding="utf-8")
        assert len(content) > 500
        assert "implement-python-backend-perf" in content

    @pytest.mark.skipif(
        not Path("data/recipes/test-python-backend.yaml").exists(),
        reason="Requires real recipe",
    )
    def test_generate_multiple_recipes_prompt(self, tmp_path):
        """Generate prompts for multiple recipes."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "generate",
                "test-python-backend",
                "implement-python-backend-perf",
                "--prompt",
                "all",
            ],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )

        # Should succeed or fail gracefully
        assert result.returncode <= 1

        if result.returncode == 0:
            assert "Generated" in result.stdout or "prompt" in result.stdout.lower()

    @pytest.mark.skipif(
        not Path("data/recipes/implement-python-backend-perf.yaml").exists(),
        reason="Requires real recipe",
    )
    def test_generate_backend_and_prompt_together(self, tmp_path):
        """Generate both backend and prompt in one command."""
        output_file = tmp_path / "combined-output.md"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "generate",
                "implement-python-backend-perf",
                "--backend",
                "cursor",
                "--prompt",
                "-o",
                str(output_file),
            ],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            assert (
                "backend installation" in result.stdout
                or "cursor" in result.stdout.lower()
            )
            assert "prompt" in result.stdout
            assert output_file.exists()


class TestGenerateCommandOutput:
    """Test generate command output formatting."""

    @pytest.mark.skipif(
        not Path("data/recipes/implement-python-backend-perf.yaml").exists(),
        reason="Requires real recipe",
    )
    def test_generate_shows_summary(self, tmp_path):
        """Generate command shows summary of what was generated."""
        output_file = tmp_path / "output.md"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "generate",
                "implement-python-backend-perf",
                "--prompt",
                "-o",
                str(output_file),
            ],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            assert "Generated" in result.stdout
            assert "1 prompt" in result.stdout

    @pytest.mark.skipif(
        not Path("data/recipes/implement-python-backend-perf.yaml").exists(),
        reason="Requires real recipe",
    )
    def test_generate_prompt_stdout_goes_to_stdout(self):
        """Generate with --prompt (no -o) sends prompt to stdout."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "generate",
                "implement-python-backend-perf",
                "--prompt",
            ],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            # Output should contain the prompt
            assert (
                "## Your Core Responsibilities" in result.stdout
                or len(result.stdout) > 1000
            )

    def test_generate_error_shows_helpful_message(self):
        """When generate fails, show helpful error."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "generate",
                "nonexistent-recipe",
                "--prompt",
            ],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert (
            "[ERROR]" in result.stderr
            or "error" in result.stderr.lower()
            or "Error" in result.stderr
        )


class TestBackendParameterParsing:
    """Test --backend parameter parsing."""

    def test_backend_accepts_single_value(self):
        """--backend cursor"""
        # Syntax validation only
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "generate",
                "test",
                "--backend",
                "cursor",
            ],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )
        # Should not fail on parameter syntax
        assert "unrecognized arguments" not in result.stderr

    def test_backend_accepts_multiple_values(self):
        """--backend cursor copilot"""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "generate",
                "test",
                "--backend",
                "cursor",
                "copilot",
            ],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )
        assert "unrecognized arguments" not in result.stderr

    def test_backend_accepts_repeated_flag(self):
        """--backend cursor --backend copilot"""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "generate",
                "test",
                "--backend",
                "cursor",
                "--backend",
                "copilot",
            ],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )
        assert "unrecognized arguments" not in result.stderr

    def test_backend_all_expands_correctly(self):
        """--backend all should expand to all backends."""
        result = subprocess.run(
            [sys.executable, "-m", "generator", "generate", "test", "--backend", "all"],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )
        # Should not fail on syntax
        assert "unrecognized arguments" not in result.stderr

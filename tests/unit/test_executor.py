"""Unit tests for generator/executor.py.

Tests pipeline execution functionality including
backend installation and prompt generation.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from generator.executor import (
    ExecutionResults,
    _execute_backend_item,
    _execute_prompt_item,
    execute_pipeline,
)
from generator.pipeline import BackendWorkItem, PromptStyle, PromptWorkItem


@pytest.fixture
def sample_merged_role():
    """Create sample merged role data."""
    return {
        "name": "test-role",
        "description": "Test role",
        "responsibilities": ["Do stuff"],
        "guidelines": ["Be awesome"],
    }


class TestExecutePipeline:
    """Test full pipeline execution."""

    @patch("generator.executor._execute_prompt_item")
    @patch("generator.executor._execute_backend_item")
    def test_executes_backend_items(
        self, mock_backend, mock_prompt, tmp_path, sample_merged_role
    ):
        """Should execute all backend work items."""
        pipeline = [
            BackendWorkItem(
                recipe_id="test-recipe",
                format="copilot",
                merged_role=sample_merged_role,
                target=None,
            ),
            BackendWorkItem(
                recipe_id="another-recipe",
                format="claude",
                merged_role=sample_merged_role,
                target=None,
            ),
        ]

        result = execute_pipeline(pipeline, tmp_path)

        assert result.backend_count == 2
        assert result.prompt_count == 0
        assert mock_backend.call_count == 2
        assert mock_prompt.call_count == 0

    @patch("generator.executor._execute_prompt_item")
    @patch("generator.executor._execute_backend_item")
    def test_executes_prompt_items(
        self, mock_backend, mock_prompt, tmp_path, sample_merged_role
    ):
        """Should execute all prompt work items."""
        mock_prompt.side_effect = [
            Path("/output/prompt1.md"),
            None,  # stdout
        ]

        pipeline = [
            PromptWorkItem(
                recipe_id="test",
                merged_role=sample_merged_role,
                is_stdout=False,
                output_path=Path("/output/prompt1.md"),
                style=PromptStyle.MARKDOWN,
            ),
            PromptWorkItem(
                recipe_id="test2",
                merged_role=sample_merged_role,
                is_stdout=True,
                output_path=None,
                style=PromptStyle.COMPACT,
            ),
        ]

        result = execute_pipeline(pipeline, tmp_path)

        assert result.backend_count == 0
        assert result.prompt_count == 2
        assert len(result.prompt_files) == 1
        assert result.prompt_files[0] == Path("/output/prompt1.md")

    @patch("generator.executor._execute_prompt_item")
    @patch("generator.executor._execute_backend_item")
    def test_executes_mixed_items(
        self, mock_backend, mock_prompt, tmp_path, sample_merged_role
    ):
        """Should execute mixed backend and prompt items."""
        mock_prompt.return_value = Path("/output/prompt.md")

        pipeline = [
            BackendWorkItem(
                recipe_id="backend-recipe",
                format="copilot",
                merged_role=sample_merged_role,
                target=None,
            ),
            PromptWorkItem(
                recipe_id="prompt-recipe",
                merged_role=sample_merged_role,
                is_stdout=False,
                output_path=Path("/output/prompt.md"),
                style=PromptStyle.MARKDOWN,
            ),
        ]

        result = execute_pipeline(pipeline, tmp_path)

        assert result.backend_count == 1
        assert result.prompt_count == 1
        assert len(result.prompt_files) == 1


class TestExecuteBackendItem:
    """Test backend item execution."""

    @patch("generator.formatter.format_copilot")
    @patch("generator.copilot_layout.install_single_copilot_recipe_to_cache")
    def test_executes_copilot_backend(
        self, mock_install, mock_format, tmp_path, sample_merged_role, capsys
    ):
        """Should install copilot backend."""
        item = BackendWorkItem(
            recipe_id="test-recipe",
            format="copilot",
            merged_role=sample_merged_role,
            target=None,
        )

        mock_format.return_value = {"formatted": "data"}
        mock_install.return_value = (
            tmp_path / "copilot-recipes" / "test-recipe.instructions.md"
        )

        _execute_backend_item(item, tmp_path)

        mock_format.assert_called_once_with(sample_merged_role)
        mock_install.assert_called_once_with(tmp_path, None, "test-recipe")
        captured = capsys.readouterr()
        assert "[OK] Installed test-recipe for copilot" in captured.out

    @patch("generator.formatter.format_claude")
    @patch("generator.claude_layout.install_single_claude_recipe_to_cache")
    def test_executes_claude_backend(
        self, mock_install, mock_format, tmp_path, sample_merged_role, capsys
    ):
        """Should install claude backend."""
        item = BackendWorkItem(
            recipe_id="claude-recipe",
            format="claude",
            merged_role=sample_merged_role,
            target=None,
        )

        mock_format.return_value = {"formatted": "data"}
        mock_install.return_value = tmp_path / "claude-recipes" / "claude-recipe.md"

        _execute_backend_item(item, tmp_path)

        mock_format.assert_called_once_with(sample_merged_role)
        mock_install.assert_called_once()
        captured = capsys.readouterr()
        assert "[OK] Installed claude-recipe for claude" in captured.out

    @patch("generator.formatter.format_cursor")
    @patch("generator.cursor_layout.install_single_cursor_recipe_to_cache")
    def test_executes_cursor_backend(
        self, mock_install, mock_format, tmp_path, sample_merged_role, capsys
    ):
        """Should install cursor backend."""
        item = BackendWorkItem(
            recipe_id="cursor-recipe",
            format="cursor",
            merged_role=sample_merged_role,
            target=None,
        )

        mock_format.return_value = {"formatted": "data"}
        mock_install.return_value = tmp_path / "cursor" / "cursor-recipe.mdrules"

        _execute_backend_item(item, tmp_path)

        mock_format.assert_called_once()
        mock_install.assert_called_once()
        captured = capsys.readouterr()
        assert "[OK] Installed cursor-recipe for cursor" in captured.out

    @patch("generator.formatter.format_cline")
    @patch("generator.cline_layout.install_single_cline_recipe_to_cache")
    def test_executes_cline_backend(
        self, mock_install, mock_format, tmp_path, sample_merged_role
    ):
        """Should install cline backend."""
        item = BackendWorkItem(
            recipe_id="cline-recipe",
            format="cline",
            merged_role=sample_merged_role,
            target=None,
        )

        mock_format.return_value = {"formatted": "data"}
        mock_install.return_value = tmp_path / "cline" / "cline-recipe.md"

        _execute_backend_item(item, tmp_path)

        mock_format.assert_called_once()
        mock_install.assert_called_once()

    def test_unknown_format_raises(self, tmp_path, sample_merged_role):
        """Should raise ValueError for unknown format."""
        item = BackendWorkItem(
            recipe_id="test",
            format="unknown-format",
            merged_role=sample_merged_role,
            target=None,
        )

        with pytest.raises((ValueError, AttributeError)):
            _execute_backend_item(item, tmp_path)

    @patch("generator.formatter.format_copilot")
    @patch("generator.copilot_layout.install_single_copilot_recipe_to_cache")
    def test_passes_target_to_install(
        self, mock_install, mock_format, tmp_path, sample_merged_role
    ):
        """Should pass target parameter to install function."""
        custom_target = tmp_path / "custom-target"
        item = BackendWorkItem(
            recipe_id="test",
            format="copilot",
            merged_role=sample_merged_role,
            target=custom_target,
        )

        mock_format.return_value = {}
        mock_install.return_value = custom_target / "recipe.md"

        _execute_backend_item(item, tmp_path)

        mock_install.assert_called_once_with(tmp_path, custom_target, "test")


class TestExecutePromptItem:
    """Test prompt item execution."""

    @patch("generator.formatters.standalone_prompt.StandalonePromptGenerator")
    def test_writes_to_file(
        self, mock_generator_class, tmp_path, sample_merged_role, capsys
    ):
        """Should write prompt to file."""
        output_path = tmp_path / "output.md"

        mock_generator = Mock()
        mock_generator.generate.return_value = "Generated prompt content"
        mock_generator_class.return_value = mock_generator

        item = PromptWorkItem(
            recipe_id="test-prompt",
            merged_role=sample_merged_role,
            is_stdout=False,
            output_path=output_path,
            style=PromptStyle.MARKDOWN,
        )

        result = _execute_prompt_item(item)

        assert result == output_path
        assert output_path.read_text(encoding="utf-8") == "Generated prompt content"

        captured = capsys.readouterr()
        assert "[OK] test-prompt prompt ->" in captured.out

    @patch("generator.formatters.standalone_prompt.StandalonePromptGenerator")
    def test_writes_to_stdout(self, mock_generator_class, sample_merged_role, capsys):
        """Should write prompt to stdout."""
        mock_generator = Mock()
        mock_generator.generate.return_value = "Stdout prompt content"
        mock_generator_class.return_value = mock_generator

        item = PromptWorkItem(
            recipe_id="stdout-prompt",
            merged_role=sample_merged_role,
            is_stdout=True,
            output_path=None,
            style=PromptStyle.COMPACT,
        )

        result = _execute_prompt_item(item)

        assert result is None
        captured = capsys.readouterr()
        assert "Stdout prompt content" in captured.out

    @patch("generator.formatters.standalone_prompt.StandalonePromptGenerator")
    def test_uses_full_metadata_for_full_style(
        self, mock_generator_class, sample_merged_role
    ):
        """Should include metadata for MARKDOWN style."""
        item = PromptWorkItem(
            recipe_id="test",
            merged_role=sample_merged_role,
            is_stdout=True,
            output_path=None,
            style=PromptStyle.MARKDOWN,
        )

        _execute_prompt_item(item)

        # Should be called with include_metadata=True for MARKDOWN style
        mock_generator_class.assert_called_once_with(
            sample_merged_role,
            include_metadata=True,
            style=PromptStyle.MARKDOWN,
        )

    @patch("generator.formatters.standalone_prompt.StandalonePromptGenerator")
    def test_excludes_metadata_for_ultra_compact(
        self, mock_generator_class, sample_merged_role
    ):
        """Should exclude metadata for ULTRA_COMPACT style."""
        item = PromptWorkItem(
            recipe_id="test",
            merged_role=sample_merged_role,
            is_stdout=True,
            output_path=None,
            style=PromptStyle.ULTRA_COMPACT,
        )

        _execute_prompt_item(item)

        # Should be called with include_metadata=False for ULTRA_COMPACT
        mock_generator_class.assert_called_once_with(
            sample_merged_role,
            include_metadata=False,
            style=PromptStyle.ULTRA_COMPACT,
        )

    def test_raises_when_output_path_missing(self, sample_merged_role):
        """Should raise ValueError when file output has no path."""
        item = PromptWorkItem(
            recipe_id="test",
            merged_role=sample_merged_role,
            is_stdout=False,
            output_path=None,  # Missing path for file output
            style=PromptStyle.MARKDOWN,
        )

        with pytest.raises(
            ValueError, match="Non-stdout prompt item must have output_path"
        ):
            _execute_prompt_item(item)


class TestExecutionResults:
    """Test ExecutionResults dataclass."""

    def test_creates_results(self):
        """Should create execution results."""
        files = [Path("/a.md"), Path("/b.md")]

        results = ExecutionResults(
            backend_count=3,
            prompt_count=2,
            prompt_files=files,
        )

        assert results.backend_count == 3
        assert results.prompt_count == 2
        assert results.prompt_files == files

    def test_empty_results(self):
        """Should create empty results."""
        results = ExecutionResults(
            backend_count=0,
            prompt_count=0,
            prompt_files=[],
        )

        assert results.backend_count == 0
        assert results.prompt_count == 0
        assert len(results.prompt_files) == 0

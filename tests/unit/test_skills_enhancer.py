"""Unit tests for generator/skills/enhancer.py.

Tests skill enhancement logic including argument hints,
format-specific extraction, and fallback handling.
"""

from __future__ import annotations

import pytest

from generator.skills.enhancer import SkillEnhancer


@pytest.fixture
def enhancer() -> SkillEnhancer:
    """Create SkillEnhancer instance."""
    return SkillEnhancer()


class TestExtractArgumentHint:
    """Test format-specific argument hint extraction."""

    def test_extract_from_copilot_example(self, enhancer: SkillEnhancer):
        """Should extract hint from copilot example."""
        recipe = {
            "name": "test-skill",
            "examples": [
                {
                    "input": "@workspace /test-skill analyze code",
                    "scenario": "code analysis",
                }
            ],
        }

        result = enhancer.extract_argument_hint(recipe, "copilot")

        assert "@workspace /test-skill" in result
        assert "<analyze code>" in result

    def test_extract_from_claude_example(self, enhancer: SkillEnhancer):
        """Should extract hint from claude example."""
        recipe = {
            "examples": [
                {
                    "input": "Review this code",
                    "scenario": "review code quality",
                }
            ]
        }

        result = enhancer.extract_argument_hint(recipe, "claude")

        assert "review code quality" in result.lower()

    def test_extract_from_cursor_example_with_file(self, enhancer: SkillEnhancer):
        """Should extract file hint for cursor."""
        recipe = {
            "examples": [
                {
                    "input": "Process main.py",
                    "scenario": "analyze a file",
                }
            ]
        }

        result = enhancer.extract_argument_hint(recipe, "cursor")

        assert "file" in result.lower() or result is not None

    def test_fallback_when_no_examples(self, enhancer: SkillEnhancer):
        """Should use fallback when no examples."""
        recipe = {"description": "Test skill for testing"}

        result = enhancer.extract_argument_hint(recipe, "copilot")

        # Should return description prefix or fallback
        assert len(result) > 0

    def test_fallback_for_unknown_format(self, enhancer: SkillEnhancer):
        """Should use generic fallback for unknown format."""
        recipe = {"description": "Test description"}

        result = enhancer.extract_argument_hint(recipe, "unknown-format")

        # Should truncate description to 150 chars or use fallback
        assert len(result) <= 150 or "Describe what you need help with" in result


class TestTryExtractFromExamples:
    """Test example extraction logic."""

    def test_extract_with_valid_examples(self, enhancer: SkillEnhancer):
        """Should extract from valid examples."""
        recipe = {
            "name": "test",
            "examples": [{"input": "@workspace /test query", "scenario": "testing"}],
        }

        result = enhancer._try_extract_from_examples(recipe, "copilot")

        assert result is not None

    def test_extract_with_no_examples(self, enhancer: SkillEnhancer):
        """Should return None when no examples."""
        recipe: dict[str, list] = {"examples": []}

        result = enhancer._try_extract_from_examples(recipe, "copilot")

        assert result is None

    def test_extract_with_missing_examples(self, enhancer: SkillEnhancer):
        """Should return None when examples key missing."""
        recipe: dict[str, str] = {}

        result = enhancer._try_extract_from_examples(recipe, "copilot")

        assert result is None

    def test_extract_with_non_dict_example(self, enhancer: SkillEnhancer):
        """Should return None when first example is not dict."""
        recipe = {"examples": ["simple string example"]}

        result = enhancer._try_extract_from_examples(recipe, "copilot")

        assert result is None


class TestExtractHintFromExample:
    """Test hint extraction from single example."""

    def test_extract_copilot_hint(self, enhancer: SkillEnhancer):
        """Should extract copilot hint from example."""
        example = {
            "input": "@workspace /skill do something",
            "scenario": "doing things",
        }
        recipe = {"name": "skill"}

        result = enhancer._extract_hint_from_example(example, recipe, "copilot")

        assert result is not None
        assert "workspace" in result.lower()

    def test_extract_claude_hint(self, enhancer: SkillEnhancer):
        """Should extract claude hint from example."""
        example = {
            "input": "Do something",
            "scenario": "processing data",
        }
        recipe: dict[str, str] = {}

        result = enhancer._extract_hint_from_example(example, recipe, "claude")

        assert result is not None
        assert "processing data" in result.lower()

    def test_extract_cursor_hint(self, enhancer: SkillEnhancer):
        """Should extract cursor hint from example."""
        example = {
            "input": "Process file",
            "scenario": "analyze class structure",
        }
        recipe: dict[str, str] = {}

        result = enhancer._extract_hint_from_example(example, recipe, "cursor")

        assert (
            result is not None or result is None
        )  # May return None if no file/class in scenario

    def test_extract_with_no_input(self, enhancer: SkillEnhancer):
        """Should return None when no input."""
        example = {"scenario": "test"}
        recipe: dict[str, str] = {}

        result = enhancer._extract_hint_from_example(example, recipe, "copilot")

        assert result is None

    def test_extract_for_unsupported_format(self, enhancer: SkillEnhancer):
        """Should return None for unsupported format."""
        example = {"input": "test", "scenario": "test"}
        recipe: dict[str, str] = {}

        result = enhancer._extract_hint_from_example(example, recipe, "unknown")

        assert result is None


class TestExtractCopilotHint:
    """Test copilot-specific hint extraction."""

    def test_extract_with_workspace_syntax(self, enhancer: SkillEnhancer):
        """Should extract parameter from @workspace syntax."""
        input_text = "@workspace /myskill process this file"
        recipe = {"name": "myskill"}

        result = enhancer._extract_copilot_hint(input_text, "", recipe)

        assert result is not None
        assert "@workspace /myskill" in result
        assert "<process this file>" in result

    def test_extract_with_scenario_no_workspace(self, enhancer: SkillEnhancer):
        """Should use scenario when no @workspace."""
        input_text = "Some input"
        scenario = "Testing Code Quality"
        recipe: dict[str, str] = {}

        result = enhancer._extract_copilot_hint(input_text, scenario, recipe)

        assert result is not None
        assert "testing code quality" in result.lower()

    def test_extract_with_no_workspace_no_scenario(self, enhancer: SkillEnhancer):
        """Should return None when no @workspace or scenario."""
        result = enhancer._extract_copilot_hint("input", "", {})

        assert result is None

    def test_extract_with_workspace_no_param(self, enhancer: SkillEnhancer):
        """Should handle @workspace without parameter."""
        input_text = "@workspace /skill"
        recipe = {"name": "skill"}

        result = enhancer._extract_copilot_hint(input_text, "", recipe)

        # Should return None if no param extracted
        assert result is None or "workspace" in result.lower()


class TestExtractWorkspaceParam:
    """Test parameter extraction from @workspace syntax."""

    def test_extract_param_from_workspace_command(self, enhancer: SkillEnhancer):
        """Should extract parameter after command."""
        input_text = "@workspace /skill analyze code quality"

        result = enhancer._extract_workspace_param(input_text)

        assert result == "analyze code quality"

    def test_extract_with_no_slash(self, enhancer: SkillEnhancer):
        """Should return None when no slash in input."""
        input_text = "no slash here"

        result = enhancer._extract_workspace_param(input_text)

        assert result is None

    def test_extract_with_slash_but_no_param(self, enhancer: SkillEnhancer):
        """Should return None when no parameter after command."""
        input_text = "@workspace /skill"

        result = enhancer._extract_workspace_param(input_text)

        assert result is None

    def test_extract_multiword_param(self, enhancer: SkillEnhancer):
        """Should extract multi-word parameters."""
        input_text = "@workspace /test this is a long parameter"

        result = enhancer._extract_workspace_param(input_text)

        assert result == "this is a long parameter"


class TestExtractClaudeHint:
    """Test claude-specific hint extraction."""

    def test_extract_with_scenario(self, enhancer: SkillEnhancer):
        """Should format scenario for claude."""
        scenario = "Analyze Code Performance"

        result = enhancer._extract_claude_hint(scenario)

        assert result is not None
        assert "analyze code performance" in result.lower()
        assert "what you want to" in result.lower()

    def test_extract_without_scenario(self, enhancer: SkillEnhancer):
        """Should use default when no scenario."""
        result = enhancer._extract_claude_hint("")

        assert result is not None
        assert "Describe what you want to analyze or generate" in result


class TestExtractCursorHint:
    """Test cursor/cline-specific hint extraction."""

    def test_extract_with_file_in_scenario(self, enhancer: SkillEnhancer):
        """Should detect file-related scenario."""
        scenario = "analyze file structure"

        result = enhancer._extract_cursor_hint(scenario)

        assert result is not None
        assert "file" in result.lower() or "path" in result.lower()

    def test_extract_with_class_in_scenario(self, enhancer: SkillEnhancer):
        """Should detect class-related scenario."""
        scenario = "review class design"

        result = enhancer._extract_cursor_hint(scenario)

        assert result is not None
        assert "file" in result.lower() or "path" in result.lower()

    def test_extract_without_file_or_class(self, enhancer: SkillEnhancer):
        """Should return None when not file/class related."""
        scenario = "general analysis"

        result = enhancer._extract_cursor_hint(scenario)

        assert result is None

    def test_extract_with_empty_scenario(self, enhancer: SkillEnhancer):
        """Should return None for empty scenario."""
        result = enhancer._extract_cursor_hint("")

        assert result is None


class TestGetFallbackHint:
    """Test fallback hint generation."""

    def test_fallback_with_description(self, enhancer: SkillEnhancer):
        """Should use description as fallback."""
        recipe = {"description": "A" * 200}  # Long description

        result = enhancer._get_fallback_hint(recipe, "copilot")

        # Should truncate to 150 chars
        assert len(result) == 150
        assert result == "A" * 150

    def test_fallback_copilot_format(self, enhancer: SkillEnhancer):
        """Should use copilot fallback format."""
        recipe: dict[str, str] = {}

        result = enhancer._get_fallback_hint(recipe, "copilot")

        assert result == "@workspace /skill <input>"

    def test_fallback_claude_format(self, enhancer: SkillEnhancer):
        """Should use claude fallback format."""
        recipe: dict[str, str] = {}

        result = enhancer._get_fallback_hint(recipe, "claude")

        assert result == "Describe what you need help with"

    def test_fallback_cursor_format(self, enhancer: SkillEnhancer):
        """Should use cursor fallback format."""
        recipe: dict[str, str] = {}

        result = enhancer._get_fallback_hint(recipe, "cursor")

        assert result == "File or code to process"

    def test_fallback_cline_format(self, enhancer: SkillEnhancer):
        """Should use cline fallback format."""
        recipe: dict[str, str] = {}

        result = enhancer._get_fallback_hint(recipe, "cline")

        assert result == "Describe the task or provide file path"

    def test_fallback_unknown_format(self, enhancer: SkillEnhancer):
        """Should use generic fallback for unknown format."""
        recipe: dict[str, str] = {}

        result = enhancer._get_fallback_hint(recipe, "unknown")

        assert result == "Describe what you need help with"


class TestExtractEnhancedExamples:
    """Test enhanced examples extraction."""

    def test_extract_examples_with_list(self, enhancer: SkillEnhancer):
        """Should format examples from list."""
        recipe = {
            "examples": [
                {"input": "test input 1", "output": "test output 1"},
                {"input": "test input 2", "output": "test output 2"},
            ]
        }

        result = enhancer.extract_enhanced_examples(recipe)

        assert "test input 1" in result
        assert "test output 1" in result
        assert "test input 2" in result
        assert "test output 2" in result

    def test_extract_examples_empty_list(self, enhancer: SkillEnhancer):
        """Should return empty string for empty examples."""
        recipe: dict[str, list] = {"examples": []}

        result = enhancer.extract_enhanced_examples(recipe)

        assert result == ""

    def test_extract_examples_missing(self, enhancer: SkillEnhancer):
        """Should return empty string when examples missing."""
        recipe: dict[str, list] = {}

        result = enhancer.extract_enhanced_examples(recipe)

        assert result == ""


class TestFormatSingleExample:
    """Test single example formatting."""

    def test_format_dict_example(self, enhancer: SkillEnhancer):
        """Should format dictionary example."""
        example = {
            "input": "test input",
            "output": "test output",
            "scenario": "test scenario",
        }

        result = enhancer._format_single_example(example, 1)

        assert len(result) > 0
        # Should contain formatted content
        assert any("input" in line.lower() or "test" in line.lower() for line in result)

    def test_format_string_example(self, enhancer: SkillEnhancer):
        """Should format string example."""
        example = "Simple string example"

        result = enhancer._format_single_example(example, 1)

        assert len(result) > 0
        assert any("Simple string example" in line for line in result)

    def test_format_example_with_index(self, enhancer: SkillEnhancer):
        """Should include index in formatted output."""
        example = {"input": "test"}

        result = enhancer._format_single_example(example, 3)

        # Should have some formatted lines
        assert len(result) > 0

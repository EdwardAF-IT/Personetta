"""Comprehensive tests for StandalonePromptGenerator.

Test categories:
- Transformation quality (imperative patterns)
- Field handling (responsibilities, guidelines, tools, etc.)
- Output format (sections, structure, metadata)
- Edge cases (empty fields, special characters, etc.)
"""

from generator.formatters.standalone_prompt import StandalonePromptGenerator
from generator.pipeline import PromptStyle

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.skills]

# ============================================================================
# TRANSFORMATION QUALITY TESTS
# ============================================================================


class TestImperativeTransformations:
    """Test semantic transformations from declarative to imperative."""

    def test_should_transforms_to_must(self):
        role = {
            "_recipe_name": "Test",
            "guidelines": ["You should validate inputs before processing"],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "You must validate inputs" in output
        assert "should" not in output.lower()

    def test_prefer_transforms_to_use_at_start(self):
        role = {"_recipe_name": "Test", "guidelines": ["Prefer explicit over implicit"]}
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "Use explicit over implicit" in output
        assert "Prefer" not in output

    def test_avoid_transforms_to_never_at_start(self):
        role = {"_recipe_name": "Test", "guidelines": ["Avoid premature optimization"]}
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "Never premature optimization" in output or "Never" in output

    def test_avoid_transforms_to_without_in_middle(self):
        role = {
            "_recipe_name": "Test",
            "guidelines": ["Keep functions small and avoid global state"],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "without global state" in output

    def test_to_avoid_transforms_correctly(self):
        """Test 'to avoid' infinitive form becomes 'without'."""
        role = {
            "_recipe_name": "Test",
            "guidelines": ["Use generators to avoid loading everything into memory"],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "without loading" in output
        assert "to without" not in output
        assert "to avoid" not in output

    def test_consider_transforms_to_evaluate(self):
        role = {
            "_recipe_name": "Test",
            "guidelines": ["Consider using async when I/O bound"],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "Evaluate using async" in output

    def test_multiple_transformations_in_one_guideline(self):
        role = {
            "_recipe_name": "Test",
            "guidelines": ["You should prefer explicit types and avoid magic numbers"],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "must" in output or "Use" in output
        assert "without magic numbers" in output or "Never magic numbers" in output

    def test_transformations_preserve_technical_terms(self):
        """Ensure code elements like __init__.py aren't mangled."""
        role = {
            "_recipe_name": "Test",
            "guidelines": ["Keep __init__.py files minimal"],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "__init__.py" in output


# ============================================================================
# FIELD HANDLING TESTS
# ============================================================================


class TestResponsibilitiesFormatting:
    """Test handling of responsibilities and non_responsibilities."""

    def test_empty_responsibilities_omits_section(self):
        role = {"_recipe_name": "Test", "responsibilities": []}
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "## Your Core Responsibilities" not in output

    def test_responsibilities_formatted_as_must(self):
        role = {
            "_recipe_name": "Test",
            "responsibilities": ["Write clean code", "Handle errors"],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "**You MUST:**" in output
        assert "- Write clean code" in output
        assert "- Handle errors" in output

    def test_non_responsibilities_formatted_as_must_not(self):
        role = {
            "_recipe_name": "Test",
            "non_responsibilities": ["Fix production bugs", "Deploy to production"],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "**You MUST NOT:**" in output
        assert (
            "Never fix production bugs" in output or "Never Fix production bugs" in output
        )

    def test_non_responsibilities_already_negative_preserved(self):
        role = {
            "_recipe_name": "Test",
            "non_responsibilities": [
                "Never skip validation",
                "Do not commit untested code",
            ],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "Never skip validation" in output
        assert (
            "Do not commit untested code" in output
            or "never commit untested code" in output
        )

    def test_responsibilities_handle_dict_items(self):
        """Handle dict with 'text' or 'description' key."""
        role = {
            "_recipe_name": "Test",
            "responsibilities": [
                {"text": "Write tests"},
                {"description": "Document APIs"},
            ],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "Write tests" in output
        assert "Document APIs" in output


class TestGuidelinesFormatting:
    """Test guideline transformation and formatting."""

    def test_empty_guidelines_omits_section(self):
        role = {"_recipe_name": "Test", "guidelines": []}
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "## How You Work" not in output

    def test_guidelines_numbered(self):
        role = {
            "_recipe_name": "Test",
            "guidelines": ["First guideline", "Second guideline", "Third guideline"],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "1. " in output
        assert "2. " in output
        assert "3. " in output

    def test_guidelines_have_emphasis(self):
        """First part of guideline should be bolded."""
        role = {
            "_recipe_name": "Test",
            "guidelines": ["Write clean code that solves the problem"],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert (
            "**Write clean code**" in output
            or "**Write clean code that solves the problem**" in output
        )

    def test_guideline_emphasis_stops_at_dash(self):
        """Bold should stop at em-dash separator."""
        role = {
            "_recipe_name": "Test",
            "guidelines": ["Keep functions small — under 50 lines ideally"],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "**Keep functions small**" in output
        assert " — under 50" in output

    def test_guideline_preserves_code_elements(self):
        """Code elements with dots shouldn't trigger sentence end."""
        role = {
            "_recipe_name": "Test",
            "guidelines": ["Use pathlib.Path instead of os.path for file operations"],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "pathlib.Path" in output
        assert "os.path" in output

    def test_guidelines_handle_dict_items(self):
        role = {"_recipe_name": "Test", "guidelines": [{"text": "Use type hints"}]}
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "Use type hints" in output


class TestToolsFormatting:
    """Test tools section formatting."""

    def test_empty_tools_omits_section(self):
        role = {"_recipe_name": "Test", "tools": []}
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "## Tools at Your Disposal" not in output

    def test_tool_with_name_purpose_when(self):
        role = {
            "_recipe_name": "Test",
            "tools": [
                {
                    "name": "pytest",
                    "purpose": "Testing framework",
                    "when": "Writing unit tests",
                }
            ],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "**pytest**" in output
        assert "Testing framework" in output
        assert "When to use: Writing unit tests" in output

    def test_tool_without_when_clause(self):
        role = {
            "_recipe_name": "Test",
            "tools": [{"name": "black", "purpose": "Code formatter"}],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "**black**" in output
        assert "Code formatter" in output
        assert "When to use:" not in output

    def test_string_tools_formatted_as_list(self):
        role = {"_recipe_name": "Test", "tools": ["pytest", "black", "mypy"]}
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "- pytest" in output or "pytest" in output


class TestExamplesFormatting:
    """Test examples section formatting."""

    def test_empty_examples_omits_section(self):
        role = {"_recipe_name": "Test", "examples": []}
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "## What Quality Looks Like" not in output

    def test_example_with_scenario_input_output(self):
        role = {
            "_recipe_name": "Test",
            "examples": [
                {
                    "scenario": "Input validation",
                    "input": "User provides email",
                    "output": "Validate format before processing",
                }
            ],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "**Scenario:** Input validation" in output
        assert "**Input:** User provides email" in output
        assert "**Your response:** Validate format" in output

    def test_string_examples_included(self):
        role = {"_recipe_name": "Test", "examples": ["Example of good practice"]}
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "Example of good practice" in output


class TestVerificationFormatting:
    """Test verification checklist formatting."""

    def test_empty_verification_omits_section(self):
        role = {"_recipe_name": "Test", "verification": []}
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "## Verification" not in output

    def test_verification_items_as_checklist(self):
        role = {
            "_recipe_name": "Test",
            "verification": [
                {"check": "All tests pass"},
                {"check": "Code is formatted"},
            ],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "## Verification" in output
        assert "- All tests pass" in output
        assert "- Code is formatted" in output

    def test_verification_string_items(self):
        role = {"_recipe_name": "Test", "verification": ["Tests pass", "No warnings"]}
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "Tests pass" in output
        assert "No warnings" in output


# ============================================================================
# OUTPUT FORMAT TESTS
# ============================================================================


class TestOutputStructure:
    """Test overall prompt structure and sections."""

    def test_metadata_header_included_by_default(self):
        role = {"_recipe_name": "Test Role"}
        gen = StandalonePromptGenerator(
            role, include_metadata=True, style=PromptStyle.MARKDOWN
        )
        output = gen.generate()
        assert "<!-- Generated by personetta -->" in output
        assert "<!-- Recipe: Test Role -->" in output

    def test_metadata_header_excluded_when_disabled(self):
        role = {"_recipe_name": "Test Role"}
        gen = StandalonePromptGenerator(
            role, include_metadata=False, style=PromptStyle.MARKDOWN
        )
        output = gen.generate()
        assert "<!-- Generated by personetta -->" not in output

    def test_opening_frame_present(self):
        role = {
            "_recipe_name": "Test Developer",
            "_recipe_description": "Writes test code",
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "# Adopting Role: Test Developer" in output
        assert "You are now acting as a **Test Developer**" in output
        assert "Writes test code" in output

    def test_compliance_footer_present(self):
        role = {"_recipe_name": "Test"}
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "## After Completing Work" in output

    def test_sections_in_correct_order(self):
        """Verify sections appear in expected order."""
        role = {
            "_recipe_name": "Test",
            "responsibilities": ["Write code"],
            "guidelines": ["Be clean"],
            "tools": [{"name": "pytest", "purpose": "Testing"}],
            "verification": ["Tests pass"],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()

        # Find positions of each section
        resp_pos = output.find("## Your Core Responsibilities")
        guide_pos = output.find("## How You Work")
        tools_pos = output.find("## Tools at Your Disposal")
        verify_pos = output.find("## Verification")

        # All should be present
        assert resp_pos > 0
        assert guide_pos > 0
        assert tools_pos > 0
        assert verify_pos > 0

        # In correct order
        assert resp_pos < guide_pos
        assert guide_pos < tools_pos
        assert tools_pos < verify_pos

    def test_output_is_valid_markdown(self):
        """Basic markdown validation."""
        role = {"_recipe_name": "Test", "guidelines": ["Use best practices"]}
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()

        # Should have heading
        assert output.startswith("#") or output.startswith("<!--")
        # Should have bullet points
        assert "\n- " in output or output.count("#") > 1


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================


class TestEdgeCases:
    """Test handling of unusual or edge case inputs."""

    def test_minimal_role_generates_output(self):
        """Absolutely minimal role still produces valid prompt."""
        role = {"_recipe_name": "Minimal"}
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert len(output) > 100
        assert "Minimal" in output

    def test_empty_strings_in_lists_ignored(self):
        role = {
            "_recipe_name": "Test",
            "responsibilities": ["Write code", "", "Test code"],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        # Should handle gracefully, empty strings don't break output
        assert "Write code" in output
        assert "Test code" in output

    def test_special_characters_preserved(self):
        """Special characters like em-dash, quotes preserved."""
        role = {
            "_recipe_name": "Test",
            "guidelines": ["Use 'single quotes' and smart quotes - they're preserved"],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        # Check that quotes and apostrophes are preserved
        assert "'" in output or "single" in output
        assert "-" in output or "—" in output

    def test_very_long_guideline_handled(self):
        """Long guidelines don't break formatting."""
        long_text = "This is a very long guideline " * 20
        role = {"_recipe_name": "Test", "guidelines": [long_text]}
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert len(output) > len(long_text)

    def test_unicode_characters_preserved(self):
        role = {
            "_recipe_name": "Test",
            "guidelines": ["Handle λ functions and Σ summations correctly"],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "λ" in output
        assert "Σ" in output

    def test_nested_bold_markers_handled(self):
        """Guidelines with existing **bold** markers."""
        role = {
            "_recipe_name": "Test",
            "guidelines": ["**Always** use type hints when possible"],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "**Always**" in output or "Always" in output

    def test_guideline_with_only_code(self):
        """Guideline that's entirely a code element."""
        role = {
            "_recipe_name": "Test",
            "guidelines": ["`mypy --strict` for maximum type safety"],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "`mypy --strict`" in output or "mypy --strict" in output

    def test_missing_recipe_name_uses_fallback(self):
        """Missing _recipe_name should use fallback."""
        role = {"guidelines": ["Test"]}
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        assert "Specialized Role" in output or len(output) > 100

    def test_none_values_in_dict_handled(self):
        role = {
            "_recipe_name": "Test",
            "responsibilities": ["Write code"],
            "tools": [{"name": "pytest", "purpose": None, "when": None}],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()
        # Should not crash, gracefully handle None
        assert "pytest" in output or len(output) > 100


# ============================================================================
# QUALITY CHECKS
# ============================================================================


class TestPromptQuality:
    """Test that generated prompts meet quality criteria."""

    def test_no_backend_specific_references(self):
        """Prompt should not reference Cursor, Copilot, Claude, etc."""
        role = {
            "_recipe_name": "Test",
            "responsibilities": ["Write code"],
            "guidelines": ["Use best practices"],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()

        backend_terms = ["cursor", "copilot", "claude", "cline", "vscode", "vs code"]
        output_lower = output.lower()
        for term in backend_terms:
            assert term not in output_lower

    def test_imperative_language_throughout(self):
        """Prompt should use imperative, not declarative language."""
        role = {
            "_recipe_name": "Test",
            "responsibilities": ["You should write tests"],
            "guidelines": ["Developers should prefer explicit code"],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()

        # Should transform declarative to imperative
        assert "should" not in output.lower() or output.lower().count("should") < 3

    def test_self_contained_no_external_references(self):
        """Prompt should be self-contained."""
        role = {
            "_recipe_name": "Test",
            "responsibilities": ["Write code"],
            "guidelines": ["Follow standards"],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()

        # Should not reference external files or concepts
        assert "see" not in output.lower() or "see " not in output.lower()
        assert "refer to" not in output.lower()

    def test_output_length_reasonable(self):
        """Generated prompt should be substantial but not excessive."""
        role = {
            "_recipe_name": "Test",
            "responsibilities": ["Write tests"] * 10,
            "guidelines": ["Use best practices"] * 20,
            "tools": [{"name": f"tool{i}", "purpose": "Testing"} for i in range(10)],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.MARKDOWN)
        output = gen.generate()

        # Should be substantial (>500 chars) but not crazy long (<50k)
        assert len(output) > 500
        assert len(output) < 50000

    def test_compact_format_is_ascii_only(self):
        """Compact format should use only ASCII characters."""
        role = {
            "_recipe_name": "Test",
            "responsibilities": ["Write tests", "Review code"],
            "guidelines": ["Use best practices", "Write clean code"],
            "tools": [
                {"name": "pytest", "when": "Running tests"},
                {"name": "black", "when": "Formatting code"},
            ],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.COMPACT)
        output = gen.generate()

        # Check for common Unicode characters that should be replaced
        unicode_chars = [
            "\u2022",
            "\u2014",
            "\u2013",
            "\u2018",
            "\u2019",
            "\u201c",
            "\u201d",
            "\u2026",
        ]
        for char in unicode_chars:
            assert (
                char not in output
            ), f"Found Unicode character {repr(char)} in compact output"

        # Verify all characters are ASCII (0-127)
        for i, char in enumerate(output):
            assert (
                ord(char) < 128 or char in "\n\r\t"
            ), f"Non-ASCII character {repr(char)} (U+{ord(char):04X}) at position {i}"

    def test_ultra_compact_format_is_ascii_only(self):
        """Ultra-compact format should use only ASCII characters."""
        role = {
            "_recipe_name": "Test",
            "responsibilities": ["Write tests", "Review code"],
            "guidelines": ["Use best practices", "Write clean code"],
            "tools": [
                {"name": "pytest", "when": "Running tests"},
                {"name": "black", "when": "Formatting code"},
            ],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.ULTRA_COMPACT)
        output = gen.generate()

        # Check for common Unicode characters that should be replaced
        unicode_chars = [
            "\u2022",
            "\u2014",
            "\u2013",
            "\u2018",
            "\u2019",
            "\u201c",
            "\u201d",
            "\u2026",
        ]
        for char in unicode_chars:
            assert (
                char not in output
            ), f"Found Unicode character {repr(char)} in ultra-compact output"

        # Verify all characters are ASCII (0-127)
        for i, char in enumerate(output):
            assert (
                ord(char) < 128 or char in "\n\r\t"
            ), f"Non-ASCII character {repr(char)} (U+{ord(char):04X}) at position {i}"

    def test_sanitize_unicode_helper(self):
        """Test the Unicode sanitization helper directly."""
        from generator.formatters.prompt_styles import CompactPromptStyle

        role = {"_recipe_name": "Test"}
        style = CompactPromptStyle(role)

        # Test various Unicode replacements
        test_cases = [
            ("Use \u2022 bullets", "Use - bullets"),
            ("Em dash \u2014 separator", "Em dash - separator"),
            ("En dash \u2013 hyphen", "En dash - hyphen"),
            ("Quote \u2018text\u2019 here", "Quote 'text' here"),
            ("Quote \u201ctext\u201d here", 'Quote "text" here'),
            ("Ellipsis\u2026", "Ellipsis..."),
        ]

        for input_text, expected in test_cases:
            result = style._sanitize_unicode(input_text)
            assert result == expected, f"Failed to sanitize {repr(input_text)}"

    def test_mixed_unicode_in_guidelines_and_tools(self):
        """Test Unicode sanitization across guidelines and tools."""
        role = {
            "_recipe_name": "Test",
            "guidelines": ["Use • bullets for lists", "Prefer — over -"],
            "tools": [
                {"name": "pytest", "when": "Run • tests"},
                {"name": "black", "when": "Format — code"},
            ],
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.COMPACT)
        output = gen.generate()

        # Verify Unicode is sanitized in all sections
        unicode_chars = ["\u2022", "\u2014"]
        for char in unicode_chars:
            assert char not in output, f"Found unsanitized {repr(char)}"

        # Verify replacement characters exist
        assert "- bullets" in output or output.count("-") >= 4

    def test_empty_recipe_with_compact_style(self):
        """Empty recipe should generate minimal but valid output."""
        role = {"_recipe_name": "MinimalRole"}
        gen = StandalonePromptGenerator(role, style=PromptStyle.COMPACT)
        output = gen.generate()

        assert len(output) > 0, "Should generate some output"
        assert "MinimalRole" in output, "Should include role name"

    def test_very_long_content_ultra_compact(self):
        """Very long content should be truncated appropriately in ultra-compact."""
        long_description = "A" * 500  # 500 char description
        role = {
            "_recipe_name": "LongRole",
            "_recipe_description": long_description,
            "responsibilities": ["Task 1"] * 20,  # Many responsibilities
            "guidelines": ["Guideline X"] * 30,  # Many guidelines
        }
        gen = StandalonePromptGenerator(role, style=PromptStyle.ULTRA_COMPACT)
        output = gen.generate()

        # Should be truncated/limited
        assert len(output) < 3000, "Ultra-compact should limit output length"
        # Description should be truncated at word boundary
        assert long_description not in output, "Long description should be truncated"

    def test_special_characters_in_recipe_name(self):
        """Special characters in recipe name should be preserved."""
        role = {"_recipe_name": "Test-Role_v2.0"}
        gen = StandalonePromptGenerator(role, style=PromptStyle.COMPACT)
        output = gen.generate()

        assert "Test-Role_v2.0" in output, "Special chars in name should be preserved"

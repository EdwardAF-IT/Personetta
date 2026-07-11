"""Unit tests for generator/skills/composer.py.

Tests skill composition and rendering functions with focus on
uncovered lines and edge cases.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.skills.composer import SkillComposer


@pytest.fixture
def mock_template_dir(tmp_path: Path) -> Path:
    """Create mock template directory with sample templates."""
    template_dir = tmp_path / "templates"
    template_dir.mkdir(parents=True)

    # Create sample SKILL.md template
    skill_template = template_dir / "SKILL.md.template"
    skill_template.write_text(
        "# $name\n\n$description\n\n## When to Use\n$when_to_use\n\n"
        "## Procedure\n$procedure\n\n## Tools\n$tools\n\n"
        "## Verification\n$verification\n\n## Examples\n$examples\n\n"
        "## Related\n$related_skills\n\n## Argument Hint\n$argument_hint",
        encoding="utf-8",
    )

    # Create sample README.md template
    readme_template = template_dir / "README.md.template"
    readme_template.write_text(
        "# $skill_name\n\n$skill_description\n\n"
        "## Invocation\n- Copilot: $copilot_invocation\n"
        "- Claude: $claude_invocation\n- Cursor: $cursor_invocation\n\n"
        "## Use Cases\n$common_use_cases\n\n## Expectations\n$what_to_expect\n\n"
        "## Troubleshooting\n$troubleshooting\n\n## Related\n$related_skills\n\n"
        "## Scripts\n$scripts_info",
        encoding="utf-8",
    )

    return template_dir


@pytest.fixture
def composer(mock_template_dir: Path) -> SkillComposer:
    """Create SkillComposer instance with mock templates."""
    return SkillComposer(mock_template_dir)


class TestLoadTemplate:
    """Test template loading."""

    def test_load_existing_template(self, composer: SkillComposer):
        """Should load existing template file."""
        content = composer.load_template("SKILL.md.template")
        assert "# $name" in content
        assert "$description" in content

    def test_load_missing_template_raises(self, composer: SkillComposer):
        """Should raise FileNotFoundError for missing template."""
        with pytest.raises(FileNotFoundError, match="Template not found"):
            composer.load_template("missing.template")


class TestRenderSkillMd:
    """Test SKILL.md rendering."""

    def test_render_with_all_fields(self, composer: SkillComposer):
        """Should render all fields when provided."""
        data = {
            "name": "test-skill",
            "description": "Test description",
            "argument_hint": "@workspace /test <input>",
            "when_to_use": "- Use case 1\n- Use case 2",
            "procedure": "1. Step one\n2. Step two",
            "tools": "- Tool A\n- Tool B",
            "verification": "- [ ] Check A\n- [ ] Check B",
            "examples": "**Example 1**\nInput: test\nOutput: result",
            "related_skills": "- skill-a\n- skill-b",
        }

        result = composer.render_skill_md(data)

        assert "# test-skill" in result
        assert "Test description" in result
        assert "@workspace /test <input>" in result
        assert "Use case 1" in result
        assert "Step one" in result
        assert "Tool A" in result
        assert "Check A" in result
        assert "Example 1" in result
        assert "skill-a" in result

    def test_render_with_missing_fields(self, composer: SkillComposer):
        """Should use empty strings for missing fields."""
        data = {
            "name": "minimal-skill",
        }

        result = composer.render_skill_md(data)

        assert "# minimal-skill" in result
        # Should not crash with missing fields
        assert "## When to Use" in result
        assert "## Procedure" in result

    def test_render_with_missing_related_skills(self, composer: SkillComposer):
        """Should use default for missing related_skills."""
        data = {"name": "test"}

        result = composer.render_skill_md(data)

        assert "(No related skills found)" in result


class TestRenderReadme:
    """Test README.md rendering."""

    def test_render_with_custom_values(self, composer: SkillComposer):
        """Should use provided values over defaults."""
        result = composer.render_readme(
            skill_name="custom-skill",
            skill_description="Custom description",
            copilot_invocation="@workspace /custom",
        )

        assert "# custom-skill" in result
        assert "Custom description" in result
        assert "@workspace /custom" in result

    def test_render_uses_defaults(self, composer: SkillComposer):
        """Should use default values for unprovided fields."""
        result = composer.render_readme(skill_name="test-skill")

        assert "# test-skill" in result
        assert "workflow automation" in result  # Default description
        assert "@workspace /test-skill" in result  # Default copilot invocation
        assert "Reference this skill" in result  # Default claude invocation
        assert "Use the skills menu" in result  # Default cursor invocation

    def test_get_readme_defaults(self, composer: SkillComposer):
        """Should generate appropriate defaults based on skill name."""
        defaults = composer._get_readme_defaults({"skill_name": "my-skill"})

        assert defaults["skill_name"] == "my-skill"
        assert defaults["copilot_invocation"] == "@workspace /my-skill"
        assert defaults["skill_description"] == "workflow automation"
        assert defaults["common_use_cases"] == "Various tasks"
        assert defaults["troubleshooting"] == "Check inputs"
        assert defaults["related_skills"] == "(No related skills found)"
        assert defaults["scripts_info"] == ""

    def test_get_readme_defaults_no_skill_name(self, composer: SkillComposer):
        """Should use 'skill' as default when no name provided."""
        defaults = composer._get_readme_defaults({})

        assert defaults["skill_name"] == "skill"
        assert defaults["copilot_invocation"] == "@workspace /skill"


class TestRenderCriteria:
    """Test criteria.md rendering."""

    def test_render_criteria_with_guidelines(self, composer: SkillComposer):
        """Should format guidelines as criteria."""
        guidelines = "- Always validate input\n- Use type hints"

        result = composer.render_criteria(guidelines)

        assert "# Success Criteria" in result
        assert "Always validate input" in result
        assert "Use type hints" in result

    def test_render_criteria_empty(self, composer: SkillComposer):
        """Should handle empty guidelines."""
        result = composer.render_criteria("")

        assert "# Success Criteria" in result
        assert result.count("\n") >= 2  # Header + blank line


class TestRenderChecklist:
    """Test checklist.md rendering."""

    def test_render_checklist_with_items(self, composer: SkillComposer):
        """Should format verification items as checklist."""
        items = "- [ ] Tests pass\n- [ ] Code is formatted"

        result = composer.render_checklist(items)

        assert "# Verification Checklist" in result
        assert "Tests pass" in result
        assert "Code is formatted" in result

    def test_render_checklist_empty(self, composer: SkillComposer):
        """Should handle empty verification items."""
        result = composer.render_checklist("")

        assert "# Verification Checklist" in result


class TestExtractDescription:
    """Test description extraction."""

    def test_extract_description_present(self, composer: SkillComposer):
        """Should extract description from recipe."""
        recipe = {"description": "  Test description  "}

        result = composer.extract_description(recipe)

        assert result == "Test description"

    def test_extract_description_missing(self, composer: SkillComposer):
        """Should return empty string when missing."""
        recipe: dict[str, str] = {}

        result = composer.extract_description(recipe)

        assert result == ""

    def test_extract_description_empty(self, composer: SkillComposer):
        """Should handle empty description."""
        recipe = {"description": "   "}

        result = composer.extract_description(recipe)

        assert result == ""


class TestExtractWhenToUse:
    """Test when-to-use extraction."""

    def test_extract_when_list(self, composer: SkillComposer):
        """Should format when list items."""
        recipe = {
            "when": [
                "Need to test code",
                "Want to validate behavior",
            ]
        }

        result = composer.extract_when_to_use(recipe)

        assert "- Need to test code" in result
        assert "- Want to validate behavior" in result

    def test_extract_when_list_dict_items(self, composer: SkillComposer):
        """Should handle dict items in when list."""
        recipe = {
            "when": [
                {"description": "Test scenario 1"},
                {"description": "Test scenario 2"},
            ]
        }

        result = composer.extract_when_to_use(recipe)

        assert "- Test scenario 1" in result
        assert "- Test scenario 2" in result

    def test_extract_when_list_mixed_types(self, composer: SkillComposer):
        """Should handle mixed string and dict items."""
        recipe = {
            "when": [
                "Simple string",
                {"description": "Dict item"},
            ]
        }

        result = composer.extract_when_to_use(recipe)

        assert "- Simple string" in result
        assert "- Dict item" in result

    def test_extract_when_empty(self, composer: SkillComposer):
        """Should return empty string when when list is empty."""
        recipe: dict[str, list] = {"when": []}

        result = composer.extract_when_to_use(recipe)

        assert result == ""

    def test_extract_when_missing(self, composer: SkillComposer):
        """Should return empty string when when is missing."""
        recipe: dict[str, str] = {}

        result = composer.extract_when_to_use(recipe)

        assert result == ""


class TestExtractProcedure:
    """Test procedure extraction."""

    def test_extract_steps_list(self, composer: SkillComposer):
        """Should format steps as numbered list."""
        recipe = {
            "steps": [
                "First step",
                "Second step",
                "Third step",
            ]
        }

        result = composer.extract_procedure(recipe)

        assert "1. First step" in result
        assert "2. Second step" in result
        assert "3. Third step" in result

    def test_extract_steps_dict_items(self, composer: SkillComposer):
        """Should handle dict items in steps list."""
        recipe = {
            "steps": [
                {"action": "Initialize project"},
                {"action": "Run tests"},
            ]
        }

        result = composer.extract_procedure(recipe)

        assert "1. Initialize project" in result
        assert "2. Run tests" in result

    def test_extract_steps_mixed_types(self, composer: SkillComposer):
        """Should handle mixed string and dict items."""
        recipe = {
            "steps": [
                "Simple step",
                {"action": "Complex step"},
            ]
        }

        result = composer.extract_procedure(recipe)

        assert "1. Simple step" in result
        assert "2. Complex step" in result

    def test_extract_steps_empty(self, composer: SkillComposer):
        """Should return empty string when steps list is empty."""
        recipe: dict[str, list] = {"steps": []}

        result = composer.extract_procedure(recipe)

        assert result == ""

    def test_extract_steps_missing(self, composer: SkillComposer):
        """Should return empty string when steps is missing."""
        recipe: dict[str, str] = {}

        result = composer.extract_procedure(recipe)

        assert result == ""


class TestFormatWhenList:
    """Test when list formatting helper."""

    def test_format_when_list_strings(self, composer: SkillComposer):
        """Should format string items with bullets."""
        when_list = ["Item 1", "Item 2"]

        result = composer._format_when_list(when_list)

        assert result == "- Item 1\n- Item 2"

    def test_format_when_list_dicts(self, composer: SkillComposer):
        """Should extract description from dict items."""
        when_list = [
            {"description": "Dict item 1"},
            {"description": "Dict item 2"},
        ]

        result = composer._format_when_list(when_list)

        assert "- Dict item 1" in result
        assert "- Dict item 2" in result

    def test_format_when_list_dict_without_description(self, composer: SkillComposer):
        """Should convert to string if no description field."""
        when_list = [{"other": "value"}]

        result = composer._format_when_list(when_list)

        assert "- " in result  # Should have bullet point


class TestFormatSteps:
    """Test steps formatting helper."""

    def test_format_steps_strings(self, composer: SkillComposer):
        """Should format string items with numbers."""
        steps = ["Step A", "Step B"]

        result = composer._format_steps(steps)

        assert result == "1. Step A\n2. Step B"

    def test_format_steps_dicts(self, composer: SkillComposer):
        """Should extract action from dict items."""
        steps = [
            {"action": "Do this"},
            {"action": "Do that"},
        ]

        result = composer._format_steps(steps)

        assert "1. Do this" in result
        assert "2. Do that" in result

    def test_format_steps_dict_without_action(self, composer: SkillComposer):
        """Should convert to string if no action field."""
        steps = [{"other": "value"}]

        result = composer._format_steps(steps)

        assert "1. " in result  # Should have number

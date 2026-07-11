"""Tests for skill templates.

This module tests:
1. Template directory structure
2. SKILL.md template validation
3. Supporting template files (README, criteria, checklist)
4. Template placeholder validation
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.skills]


class TestTemplateDirectory:
    """Tests for template directory structure."""

    def test_templates_skill_directory_exists(self, project_root):
        """Verify data/templates/skill/ directory exists."""
        templates_dir = project_root / "data" / "templates" / "skill"
        assert templates_dir.exists(), "data/templates/skill/ directory should exist"
        assert templates_dir.is_dir(), "data/templates/skill/ should be a directory"


class TestSkillMdTemplate:
    """Tests for SKILL.md.template structure and content."""

    def test_skill_md_template_exists(self, project_root):
        """Verify SKILL.md.template file exists."""
        template_file = (
            project_root / "data" / "templates" / "skill" / "SKILL.md.template"
        )
        assert template_file.exists(), "SKILL.md.template should exist"
        assert template_file.is_file(), "SKILL.md.template should be a file"

    def test_skill_md_has_yaml_frontmatter_placeholders(self, project_root):
        """Test SKILL.md.template has required YAML frontmatter placeholders."""
        template_file = (
            project_root / "data" / "templates" / "skill" / "SKILL.md.template"
        )
        content = template_file.read_text(encoding="utf-8")

        # Check for frontmatter delimiters
        assert content.startswith("---\n"), "Template should start with YAML frontmatter"
        assert "\n---\n" in content, "Template should have closing frontmatter delimiter"

        # Check for required placeholders in frontmatter
        assert "${name}" in content, "Should have ${name} placeholder"
        assert "${description}" in content, "Should have ${description} placeholder"
        assert "${argument_hint}" in content, "Should have ${argument_hint} placeholder"

    def test_skill_md_has_required_sections(self, project_root):
        """Test SKILL.md.template has all required sections."""
        template_file = (
            project_root / "data" / "templates" / "skill" / "SKILL.md.template"
        )
        content = template_file.read_text(encoding="utf-8")

        # Required section headers
        required_sections = [
            "## When to Use",
            "## Procedure",
            "## Tools Used",
            "## Verification",
            "## Examples",
        ]

        for section in required_sections:
            assert section in content, f"Template should have '{section}' section"

    def test_skill_md_has_procedure_placeholders(self, project_root):
        """Test SKILL.md.template has procedure-related placeholders."""
        template_file = (
            project_root / "data" / "templates" / "skill" / "SKILL.md.template"
        )
        content = template_file.read_text(encoding="utf-8")

        assert "${when_to_use}" in content, "Should have ${when_to_use} placeholder"
        assert "${procedure}" in content, "Should have ${procedure} placeholder"

    def test_skill_md_has_tools_placeholder(self, project_root):
        """Test SKILL.md.template has tools placeholder."""
        template_file = (
            project_root / "data" / "templates" / "skill" / "SKILL.md.template"
        )
        content = template_file.read_text(encoding="utf-8")

        assert "${tools}" in content, "Should have ${tools} placeholder"

    def test_skill_md_has_verification_placeholder(self, project_root):
        """Test SKILL.md.template has verification placeholder."""
        template_file = (
            project_root / "data" / "templates" / "skill" / "SKILL.md.template"
        )
        content = template_file.read_text(encoding="utf-8")

        assert "${verification}" in content, "Should have ${verification} placeholder"

    def test_skill_md_has_examples_placeholder(self, project_root):
        """Test SKILL.md.template has examples placeholder."""
        template_file = (
            project_root / "data" / "templates" / "skill" / "SKILL.md.template"
        )
        content = template_file.read_text(encoding="utf-8")

        assert "${examples}" in content, "Should have ${examples} placeholder"

    def test_skill_md_is_valid_markdown(self, project_root):
        """Test SKILL.md.template is valid markdown structure."""
        template_file = (
            project_root / "data" / "templates" / "skill" / "SKILL.md.template"
        )
        content = template_file.read_text(encoding="utf-8")

        # Basic markdown validation
        # Should have headers (lines starting with #)
        lines = content.split("\n")
        has_headers = any(line.strip().startswith("#") for line in lines)
        assert has_headers, "Template should have markdown headers"


class TestReadmeTemplate:
    """Tests for README.md.template structure."""

    def test_readme_template_exists(self, project_root):
        """Verify README.md.template file exists."""
        template_file = (
            project_root / "data" / "templates" / "skill" / "README.md.template"
        )
        assert template_file.exists(), "README.md.template should exist"
        assert template_file.is_file(), "README.md.template should be a file"

    def test_readme_has_skill_name_placeholder(self, project_root):
        """Test README.md.template has skill name placeholder."""
        template_file = (
            project_root / "data" / "templates" / "skill" / "README.md.template"
        )
        content = template_file.read_text(encoding="utf-8")

        assert "${skill_name}" in content, "Should have ${skill_name} placeholder"

    def test_readme_has_usage_section(self, project_root):
        """Test README.md.template has usage instructions section."""
        template_file = (
            project_root / "data" / "templates" / "skill" / "README.md.template"
        )
        content = template_file.read_text(encoding="utf-8")

        # Should mention usage or how to invoke
        content_lower = content.lower()
        assert any(
            keyword in content_lower for keyword in ["usage", "how to", "invoke"]
        ), "README should have usage instructions"

    def test_readme_is_valid_markdown(self, project_root):
        """Test README.md.template is valid markdown."""
        template_file = (
            project_root / "data" / "templates" / "skill" / "README.md.template"
        )
        content = template_file.read_text(encoding="utf-8")

        # Should have markdown headers
        lines = content.split("\n")
        has_headers = any(line.strip().startswith("#") for line in lines)
        assert has_headers, "README should have markdown headers"


class TestCriteriaTemplate:
    """Tests for criteria.md.template structure."""

    def test_criteria_template_exists(self, project_root):
        """Verify criteria.md.template file exists."""
        template_file = (
            project_root / "data" / "templates" / "skill" / "criteria.md.template"
        )
        assert template_file.exists(), "criteria.md.template should exist"
        assert template_file.is_file(), "criteria.md.template should be a file"

    def test_criteria_has_guidelines_placeholder(self, project_root):
        """Test criteria.md.template has guidelines placeholder."""
        template_file = (
            project_root / "data" / "templates" / "skill" / "criteria.md.template"
        )
        content = template_file.read_text(encoding="utf-8")

        assert "${guidelines}" in content, "Should have ${guidelines} placeholder"

    def test_criteria_has_checklist_format(self, project_root):
        """Test criteria.md.template suggests checklist format."""
        template_file = (
            project_root / "data" / "templates" / "skill" / "criteria.md.template"
        )
        content = template_file.read_text(encoding="utf-8")

        # Should mention checklist or criteria
        content_lower = content.lower()
        assert any(
            keyword in content_lower for keyword in ["guideline", "criteria", "checklist"]
        ), "criteria.md should reference guidelines or checklist"

    def test_criteria_is_valid_markdown(self, project_root):
        """Test criteria.md.template is valid markdown."""
        template_file = (
            project_root / "data" / "templates" / "skill" / "criteria.md.template"
        )
        content = template_file.read_text(encoding="utf-8")

        lines = content.split("\n")
        has_headers = any(line.strip().startswith("#") for line in lines)
        assert has_headers, "criteria.md should have markdown headers"


class TestChecklistTemplate:
    """Tests for checklist.md.template structure."""

    def test_checklist_template_exists(self, project_root):
        """Verify checklist.md.template file exists."""
        template_file = (
            project_root / "data" / "templates" / "skill" / "checklist.md.template"
        )
        assert template_file.exists(), "checklist.md.template should exist"
        assert template_file.is_file(), "checklist.md.template should be a file"

    def test_checklist_has_verification_placeholder(self, project_root):
        """Test checklist.md.template has verification placeholder."""
        template_file = (
            project_root / "data" / "templates" / "skill" / "checklist.md.template"
        )
        content = template_file.read_text(encoding="utf-8")

        assert (
            "${verification_items}" in content
        ), "Should have ${verification_items} placeholder"

    def test_checklist_has_checkbox_format(self, project_root):
        """Test checklist.md.template suggests checkbox/checklist format."""
        template_file = (
            project_root / "data" / "templates" / "skill" / "checklist.md.template"
        )
        content = template_file.read_text(encoding="utf-8")

        # Should mention checklist or verification
        content_lower = content.lower()
        assert any(
            keyword in content_lower for keyword in ["checklist", "verification", "check"]
        ), "checklist.md should reference verification items"

    def test_checklist_is_valid_markdown(self, project_root):
        """Test checklist.md.template is valid markdown."""
        template_file = (
            project_root / "data" / "templates" / "skill" / "checklist.md.template"
        )
        content = template_file.read_text(encoding="utf-8")

        lines = content.split("\n")
        has_headers = any(line.strip().startswith("#") for line in lines)
        assert has_headers, "checklist.md should have markdown headers"


class TestTemplatePlaceholderConsistency:
    """Tests for consistent placeholder syntax across all templates."""

    def test_all_templates_use_string_template_syntax(self, project_root):
        """Verify all templates use ${placeholder} syntax (string.Template)."""
        templates_dir = project_root / "data" / "templates" / "skill"
        template_files = [
            "SKILL.md.template",
            "README.md.template",
            "criteria.md.template",
            "checklist.md.template",
        ]

        for template_name in template_files:
            template_file = templates_dir / template_name
            content = template_file.read_text(encoding="utf-8")

            # Should use ${placeholder} format (string.Template), not {placeholder} or {{placeholder}}
            # We allow ${...} but flag if we see { without $ before it (common mistake)
            if "{" in content:
                # If we have braces, ensure they're preceded by $ or are in code blocks
                # This is a basic check - we just verify ${} pattern exists
                assert (
                    "${" in content
                ), f"{template_name} should use ${{placeholder}} syntax for string.Template"

    def test_no_placeholder_collisions(self, project_root):
        """Verify placeholder names don't collide or have typos."""
        templates_dir = project_root / "data" / "templates" / "skill"
        skill_md = (templates_dir / "SKILL.md.template").read_text(encoding="utf-8")

        # Extract all placeholders from SKILL.md
        import re

        placeholders = re.findall(r"\$\{([^}]+)\}", skill_md)

        # Known expected placeholders
        expected = {
            "name",
            "description",
            "argument_hint",
            "when_to_use",
            "procedure",
            "tools",
            "verification",
            "examples",
            "related_skills",  # Phase 8 enhancement
        }

        # All placeholders should be in expected set (no typos)
        unexpected = set(placeholders) - expected
        assert (
            not unexpected
        ), f"Unexpected placeholders in SKILL.md.template: {unexpected}"

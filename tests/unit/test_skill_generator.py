"""Tests for SkillGenerator class.

Tests the main orchestrator for skill generation workflow.

Following TDD approach: write tests first, then implement.
"""

from __future__ import annotations

import sys
import pytest

from generator.project_layout import ProjectLayout
from generator.skills import SkillGenerator

# ============================================================================
# Phase 4.1: SkillGenerator Instantiation and Template Loading
# ============================================================================


class TestSkillGeneratorInstantiation:
    """Test SkillGenerator class instantiation."""

    def test_can_instantiate_skill_generator(self, tmp_path):
        """SkillGenerator can be instantiated with template directory."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        generator = SkillGenerator(template_dir)

        assert generator is not None
        assert generator.template_dir == template_dir

    def test_instantiation_without_template_dir_uses_default(self):
        """SkillGenerator uses default template directory if none provided."""
        generator = SkillGenerator()

        assert generator is not None
        # Default should be relative to generator module
        assert generator.template_dir.name == "skill"


class TestTemplateLoading:
    """Test template loading functionality."""

    def test_loads_skill_md_template(self, skill_generator_with_templates):
        """SkillGenerator loads SKILL.md.template."""
        generator = skill_generator_with_templates

        template = generator.load_template("SKILL.md.template")

        assert template is not None
        assert "${name}" in template
        assert "${description}" in template
        assert "${when_to_use}" in template

    def test_loads_readme_template(self, skill_generator_with_templates):
        """SkillGenerator loads README.md.template."""
        generator = skill_generator_with_templates

        template = generator.load_template("README.md.template")

        assert template is not None
        assert "${skill_name}" in template

    def test_loads_criteria_template(self, skill_generator_with_templates):
        """SkillGenerator loads criteria.md.template."""
        generator = skill_generator_with_templates

        template = generator.load_template("criteria.md.template")

        assert template is not None
        assert "${guidelines}" in template

    def test_loads_checklist_template(self, skill_generator_with_templates):
        """SkillGenerator loads checklist.md.template."""
        generator = skill_generator_with_templates

        template = generator.load_template("checklist.md.template")

        assert template is not None
        assert "${verification_items}" in template

    def test_raises_error_for_missing_template(self, skill_generator_with_templates):
        """SkillGenerator raises error when template file missing."""
        generator = skill_generator_with_templates

        with pytest.raises(FileNotFoundError):
            generator.load_template("nonexistent.template")


# ============================================================================
# Phase 4.2: Template Rendering
# ============================================================================


class TestTemplateRendering:
    """Test template rendering with string.Template."""

    def test_renders_skill_md_template(
        self, skill_generator_with_templates, sample_recipe_data
    ):
        """Renders SKILL.md from template with recipe data."""
        generator = skill_generator_with_templates

        rendered = generator.render_skill_md(sample_recipe_data)

        assert "name: python-testing" in rendered
        assert "Write pytest tests" in rendered
        assert "## When to Use" in rendered
        assert "## Procedure" in rendered

    def test_renders_readme_template(self, skill_generator_with_templates):
        """Renders README.md from template."""
        generator = skill_generator_with_templates

        rendered = generator.render_readme("python-testing")

        assert "# python-testing Skill" in rendered
        assert "SKILL.md" in rendered

    def test_renders_criteria_template(
        self, skill_generator_with_templates, sample_guidelines
    ):
        """Renders criteria.md from template with guidelines."""
        generator = skill_generator_with_templates

        rendered = generator.render_criteria(sample_guidelines)

        assert "## Guidelines" in rendered
        assert "Always reach for existing tools first" in rendered

    def test_renders_checklist_template(
        self, skill_generator_with_templates, sample_verification
    ):
        """Renders checklist.md from template with verification items."""
        generator = skill_generator_with_templates

        rendered = generator.render_checklist(sample_verification)

        assert "## Verification Items" in rendered
        assert "All tests pass" in rendered


# ============================================================================
# Phase 4.3: Data Extraction and Transformation
# ============================================================================


class TestDataExtraction:
    """Test extraction of data from merged recipe."""

    def test_extracts_description(
        self, skill_generator_with_templates, sample_merged_recipe
    ):
        """Extracts description from merged recipe."""
        generator = skill_generator_with_templates

        description = generator.extract_description(sample_merged_recipe)

        assert description == "Write pytest tests for Python backend code"

    def test_extracts_responsibilities_as_when_to_use(
        self, skill_generator_with_templates, sample_merged_recipe
    ):
        """Transforms responsibilities into 'When to Use' section."""
        generator = skill_generator_with_templates

        when_to_use = generator.extract_when_to_use(sample_merged_recipe)

        assert "Design test strategy" in when_to_use
        assert "Write tests that verify behavior" in when_to_use

    def test_transforms_responsibilities_to_procedure(
        self, skill_generator_with_templates, sample_merged_recipe
    ):
        """Transforms responsibilities into numbered procedure steps."""
        generator = skill_generator_with_templates

        procedure = generator.extract_procedure(sample_merged_recipe)

        assert "1." in procedure
        assert "2." in procedure
        assert "Design test strategy" in procedure

    def test_transforms_guidelines_to_criteria(
        self, skill_generator_with_templates, sample_merged_recipe
    ):
        """Transforms guidelines into criteria format."""
        generator = skill_generator_with_templates

        criteria = generator.extract_criteria(sample_merged_recipe)

        assert "Always reach for existing tools first" in criteria
        assert "Structure tests as Arrange-Act-Assert" in criteria

    def test_extracts_tools_section(
        self, skill_generator_with_templates, sample_merged_recipe
    ):
        """Extracts and formats tools section."""
        generator = skill_generator_with_templates

        tools = generator.extract_tools(sample_merged_recipe)

        assert "pytest" in tools
        assert "coverage.py" in tools

    def test_transforms_verification_to_checklist(
        self, skill_generator_with_templates, sample_merged_recipe
    ):
        """Transforms verification items into checklist format."""
        generator = skill_generator_with_templates

        checklist = generator.extract_verification(sample_merged_recipe)

        assert "All tests pass" in checklist
        assert "[ ]" in checklist  # Checkbox format

    def test_extracts_examples(
        self, skill_generator_with_templates, sample_merged_recipe
    ):
        """Extracts examples section."""
        generator = skill_generator_with_templates

        examples = generator.extract_examples(sample_merged_recipe)

        assert "shopping cart" in examples.lower()

    def test_generates_argument_hint(
        self, skill_generator_with_templates, sample_merged_recipe
    ):
        """Generates argument hint from examples or description."""
        generator = skill_generator_with_templates

        hint = generator.generate_argument_hint(sample_merged_recipe)

        assert len(hint) > 0
        assert len(hint) < 200  # Should be concise


# ============================================================================
# Phase 4.4: Handle Missing Sections
# ============================================================================


class TestMissingSections:
    """Test graceful handling of missing recipe sections."""

    def test_handles_missing_guidelines(self, skill_generator_with_templates):
        """Recipe with no guidelines skips criteria.md."""
        generator = skill_generator_with_templates
        recipe = {"name": "test", "description": "Test", "responsibilities": ["Do stuff"]}

        criteria = generator.extract_criteria(recipe)

        assert criteria is None

    def test_handles_missing_tools(self, skill_generator_with_templates):
        """Recipe with no tools skips tools section."""
        generator = skill_generator_with_templates
        recipe = {"name": "test", "description": "Test", "responsibilities": ["Do stuff"]}

        tools = generator.extract_tools(recipe)

        assert tools is None

    def test_handles_missing_examples(self, skill_generator_with_templates):
        """Recipe with no examples skips examples section."""
        generator = skill_generator_with_templates
        recipe = {"name": "test", "description": "Test", "responsibilities": ["Do stuff"]}

        examples = generator.extract_examples(recipe)

        assert examples is None

    def test_handles_missing_verification(self, skill_generator_with_templates):
        """Recipe with no verification skips checklist.md."""
        generator = skill_generator_with_templates
        recipe = {"name": "test", "description": "Test", "responsibilities": ["Do stuff"]}

        verification = generator.extract_verification(recipe)

        assert verification is None

    def test_prints_warning_for_missing_guidelines(
        self, skill_generator_with_templates, capsys
    ):
        """Prints warning when guidelines missing."""
        generator = skill_generator_with_templates
        recipe = {"name": "test", "description": "Test", "responsibilities": ["Do stuff"]}

        generator.extract_criteria(recipe)

        captured = capsys.readouterr()
        # Warning is printed to stderr
        assert "WARNING" in captured.err or "guidelines" in captured.err.lower()


# ============================================================================
# Phase 4.5: Directory Structure and File Creation
# ============================================================================


class TestDirectoryStructure:
    """Test directory and file creation."""

    def test_create_skill_directory(self, skill_generator_with_templates, tmp_path):
        """Creates skill root directory."""
        generator = skill_generator_with_templates
        skill_dir = tmp_path / "python-testing"

        generator.create_directory_structure(skill_dir)

        assert skill_dir.exists()
        assert skill_dir.is_dir()

    def test_creates_references_subdirectory(
        self, skill_generator_with_templates, tmp_path
    ):
        """Creates references/ subdirectory."""
        generator = skill_generator_with_templates
        skill_dir = tmp_path / "python-testing"

        generator.create_directory_structure(skill_dir)

        references = skill_dir / "references"
        assert references.exists()
        assert references.is_dir()

    def test_creates_templates_subdirectory(
        self, skill_generator_with_templates, tmp_path
    ):
        """Creates templates/ subdirectory (empty for Phase 4)."""
        generator = skill_generator_with_templates
        skill_dir = tmp_path / "python-testing"

        generator.create_directory_structure(skill_dir)

        templates = skill_dir / "templates"
        assert templates.exists()
        assert templates.is_dir()

    def test_writes_skill_md_file(
        self, skill_generator_with_templates, tmp_path, sample_recipe_data
    ):
        """Writes SKILL.md file."""
        generator = skill_generator_with_templates
        skill_dir = tmp_path / "python-testing"
        skill_dir.mkdir()

        content = generator.render_skill_md(sample_recipe_data)
        generator.write_file(skill_dir / "SKILL.md", content)

        skill_md = skill_dir / "SKILL.md"
        assert skill_md.exists()
        assert "name: python-testing" in skill_md.read_text()

    def test_writes_readme_file(self, skill_generator_with_templates, tmp_path):
        """Writes README.md file."""
        generator = skill_generator_with_templates
        skill_dir = tmp_path / "python-testing"
        skill_dir.mkdir()

        content = generator.render_readme("python-testing")
        generator.write_file(skill_dir / "README.md", content)

        readme = skill_dir / "README.md"
        assert readme.exists()
        assert "python-testing" in readme.read_text()

    def test_writes_criteria_file(
        self, skill_generator_with_templates, tmp_path, sample_guidelines
    ):
        """Writes references/criteria.md file."""
        generator = skill_generator_with_templates
        skill_dir = tmp_path / "python-testing"
        skill_dir.mkdir()
        (skill_dir / "references").mkdir()

        content = generator.render_criteria(sample_guidelines)
        generator.write_file(skill_dir / "references" / "criteria.md", content)

        criteria = skill_dir / "references" / "criteria.md"
        assert criteria.exists()

    def test_writes_checklist_file(
        self, skill_generator_with_templates, tmp_path, sample_verification
    ):
        """Writes references/checklist.md file."""
        generator = skill_generator_with_templates
        skill_dir = tmp_path / "python-testing"
        skill_dir.mkdir()
        (skill_dir / "references").mkdir()

        content = generator.render_checklist(sample_verification)
        generator.write_file(skill_dir / "references" / "checklist.md", content)

        checklist = skill_dir / "references" / "checklist.md"
        assert checklist.exists()

    def test_skips_criteria_file_when_no_guidelines(
        self, skill_generator_with_templates, tmp_path
    ):
        """Does NOT create criteria.md when guidelines missing."""
        generator = skill_generator_with_templates
        skill_dir = tmp_path / "python-testing"
        skill_dir.mkdir()
        (skill_dir / "references").mkdir()

        recipe = {"name": "test", "description": "Test", "responsibilities": ["Do stuff"]}
        generator.generate(recipe, "copilot", "python-testing", skill_dir)

        criteria = skill_dir / "references" / "criteria.md"
        assert not criteria.exists()


# ============================================================================
# Full Generation Workflow
# ============================================================================


class TestFullGeneration:
    """Test complete skill generation workflow."""

    def test_generates_complete_skill_from_recipe(
        self, skill_generator_with_templates, tmp_path, sample_merged_recipe
    ):
        """Generates complete skill with all files from full recipe."""
        generator = skill_generator_with_templates
        skill_dir = tmp_path / "python-testing"

        generator.generate(sample_merged_recipe, "copilot", "python-testing", skill_dir)

        # Check directory structure
        assert skill_dir.exists()
        assert (skill_dir / "references").exists()
        assert (skill_dir / "templates").exists()

        # Check files
        assert (skill_dir / "SKILL.md").exists()
        assert (skill_dir / "README.md").exists()
        assert (skill_dir / "references" / "criteria.md").exists()
        assert (skill_dir / "references" / "checklist.md").exists()

    def test_generates_minimal_skill_from_minimal_recipe(
        self, skill_generator_with_templates, tmp_path
    ):
        """Generates skill from minimal recipe (only required fields)."""
        generator = skill_generator_with_templates
        skill_dir = tmp_path / "minimal-skill"

        minimal_recipe = {
            "name": "minimal",
            "description": "Minimal test recipe",
            "responsibilities": ["Do one thing"],
        }

        generator.generate(minimal_recipe, "copilot", "minimal-skill", skill_dir)

        # Should have basic structure
        assert skill_dir.exists()
        assert (skill_dir / "SKILL.md").exists()
        assert (skill_dir / "README.md").exists()

        # Should NOT have optional files
        assert not (skill_dir / "references" / "criteria.md").exists()

    def test_skill_md_has_valid_yaml_frontmatter(
        self, skill_generator_with_templates, tmp_path, sample_merged_recipe
    ):
        """Generated SKILL.md has valid YAML frontmatter."""
        generator = skill_generator_with_templates
        skill_dir = tmp_path / "python-testing"

        generator.generate(sample_merged_recipe, "copilot", "python-testing", skill_dir)

        skill_md = (skill_dir / "SKILL.md").read_text()
        assert skill_md.startswith("---\n")
        assert "name: python-testing" in skill_md
        assert "description:" in skill_md
        assert "argument-hint:" in skill_md

    def test_generates_for_different_formats(
        self, skill_generator_with_templates, tmp_path, sample_merged_recipe
    ):
        """Generates skill for all formats (copilot, claude, cursor, cline)."""
        generator = skill_generator_with_templates

        for format_name in ["copilot", "claude", "cursor", "cline"]:
            skill_dir = tmp_path / f"{format_name}-skill"

            generator.generate(
                sample_merged_recipe, format_name, f"{format_name}-skill", skill_dir
            )

            assert skill_dir.exists()
            assert (skill_dir / "SKILL.md").exists()


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def skill_generator_with_templates():
    """SkillGenerator with actual templates from data/templates/skill/."""
    # Use real templates from repo - updated for new structure
    template_dir = ProjectLayout.from_file(__file__).templates / "skill"
    return SkillGenerator(template_dir)


@pytest.fixture
def sample_recipe_data():
    """Sample recipe data for testing rendering."""
    return {
        "name": "python-testing",
        "description": "Write pytest tests for Python backend code",
        "when_to_use": "When you need to write tests for Python code",
        "procedure": "1. Design test strategy\n2. Write tests\n3. Run coverage",
        "tools": "- pytest\n- coverage.py",
        "verification": "- [ ] All tests pass\n- [ ] Coverage > 80%",
        "examples": "Example: Testing a shopping cart total calculation",
        "argument_hint": "Specify the module or class to test",
    }


@pytest.fixture
def sample_guidelines():
    """Sample guidelines for testing criteria rendering."""
    return """
- Always reach for existing tools first
- Structure tests as Arrange-Act-Assert
- Test one logical behavior per test
    """.strip()


@pytest.fixture
def sample_verification():
    """Sample verification items for testing checklist rendering."""
    return """
- [ ] All tests pass
- [ ] Coverage > 80%
- [ ] No skipped tests
    """.strip()


@pytest.fixture
def sample_merged_recipe():
    """Sample merged recipe with all sections."""
    return {
        "_recipe_name": "test-python-backend",
        "_recipe_description": "Write pytest tests for Python backend code",
        "responsibilities": [
            "Design test strategy appropriate to the code under test",
            "Write tests that verify behavior, not implementation details",
            "Identify edge cases, boundary conditions, and failure modes",
        ],
        "guidelines": [
            "Always reach for existing tools first",
            "Structure tests as Arrange-Act-Assert (Given-When-Then)",
            "Test one logical behavior per test",
        ],
        "tools": [
            {
                "name": "pytest",
                "purpose": "Testing framework",
                "when": "All Python testing",
            },
            {
                "name": "coverage.py",
                "purpose": "Code coverage measurement",
                "when": "Measuring test coverage",
            },
        ],
        "verification": [
            {"check": "All tests pass", "method": "pytest"},
            {"check": "Coverage > 80%", "method": "coverage report"},
        ],
        "examples": [
            {
                "scenario": "Writing tests for a shopping cart total calculation",
                "input": "CartService.calculate_total(items)",
                "output": "Test suite covering happy path and edge cases",
            }
        ],
    }


@pytest.fixture
def sample_recipe_with_tools():
    """Sample merged recipe with tools section for script generation."""
    return {
        "_recipe_name": "test-python-backend",
        "tools": [
            {
                "name": "pytest",
                "purpose": "Run tests with coverage",
                "command": "pytest --cov --cov-report=html",
            },
            {
                "name": "black",
                "purpose": "Format Python code",
                "command": "black .",
            },
        ],
    }


@pytest.fixture
def sample_recipe_with_multiline_command():
    """Sample recipe with multi-line command in tools."""
    return {
        "_recipe_name": "build-project",
        "tools": [
            {
                "name": "docker-build",
                "purpose": "Build Docker image",
                "command": "docker build -t myapp:latest \\\n  --build-arg VERSION=1.0 \\\n  .",
            },
        ],
    }


@pytest.fixture
def sample_recipe_no_tools():
    """Sample recipe with no tools section."""
    return {
        "_recipe_name": "design-arch",
        "responsibilities": ["Design system architecture"],
    }


# ============================================================================
# Phase 7b: Script Bundling Tests
# ============================================================================


class TestExtractToolCommands:
    """Test extracting tool commands from recipe."""

    def test_extracts_tools_from_recipe(self, sample_recipe_with_tools):
        """Extracts tool commands from recipe tools section."""
        from generator.skills import extract_tool_commands

        tools = extract_tool_commands(sample_recipe_with_tools)

        assert len(tools) == 2
        assert tools[0]["name"] == "pytest"
        assert tools[0]["command"] == "pytest --cov --cov-report=html"
        assert tools[0]["purpose"] == "Run tests with coverage"

    def test_returns_empty_list_when_no_tools(self, sample_recipe_no_tools):
        """Returns empty list when recipe has no tools section."""
        from generator.skills import extract_tool_commands

        tools = extract_tool_commands(sample_recipe_no_tools)

        assert tools == []

    def test_skips_tools_without_command(self):
        """Skips tools that don't have a command field."""
        from generator.skills import extract_tool_commands

        recipe = {
            "tools": [
                {"name": "pytest", "command": "pytest"},
                {"name": "manual-tool", "purpose": "Manual review"},  # No command
            ]
        }

        tools = extract_tool_commands(recipe)

        assert len(tools) == 1
        assert tools[0]["name"] == "pytest"


class TestSanitizeScriptName:
    """Test script name sanitization."""

    def test_converts_to_lowercase(self):
        """Converts tool names to lowercase."""
        from generator.skills import sanitize_script_name

        result = sanitize_script_name("PyTest")

        assert result == "pytest"

    def test_replaces_dots_with_hyphens(self):
        """Replaces dots with hyphens."""
        from generator.skills import sanitize_script_name

        result = sanitize_script_name("coverage.py")

        assert result == "coverage-py"

    def test_replaces_spaces_with_hyphens(self):
        """Replaces spaces with hyphens."""
        from generator.skills import sanitize_script_name

        result = sanitize_script_name("Azure CLI")

        assert result == "azure-cli"

    def test_removes_special_characters(self):
        """Removes special characters."""
        from generator.skills import sanitize_script_name

        result = sanitize_script_name("tool@version#1")

        assert result == "tool-version-1"

    def test_collapses_multiple_hyphens(self):
        """Collapses multiple hyphens to single hyphen."""
        from generator.skills import sanitize_script_name

        result = sanitize_script_name("my---tool")

        assert result == "my-tool"


class TestGenerateShellScript:
    """Test generating shell scripts (.sh)."""

    def test_generates_shell_script_with_shebang(self):
        """Generated .sh script has proper shebang."""
        from generator.skills import generate_shell_script

        script = generate_shell_script("pytest", "pytest --cov", "Run tests")

        assert script.startswith("#!/bin/bash")

    def test_includes_tool_purpose_as_comment(self):
        """Generated script includes purpose as comment."""
        from generator.skills import generate_shell_script

        script = generate_shell_script(
            "pytest", "pytest --cov", "Run tests with coverage"
        )

        assert "# Run tests with coverage" in script

    def test_includes_command_in_script(self):
        """Generated script includes the actual command."""
        from generator.skills import generate_shell_script

        script = generate_shell_script(
            "pytest", "pytest --cov --cov-report=html", "Run tests"
        )

        assert "pytest --cov --cov-report=html" in script

    def test_preserves_multiline_commands(self):
        """Preserves multi-line commands with line continuations."""
        from generator.skills import generate_shell_script

        command = "docker build -t myapp:latest \\\n  --build-arg VERSION=1.0 \\\n  ."
        script = generate_shell_script("docker-build", command, "Build image")

        assert "\\" in script  # Line continuations preserved
        assert "--build-arg VERSION=1.0" in script


class TestGeneratePowerShellScript:
    """Test generating PowerShell scripts (.ps1)."""

    def test_generates_powershell_script_with_comment_header(self):
        """Generated .ps1 script has comment header."""
        from generator.skills import generate_powershell_script

        script = generate_powershell_script("pytest", "pytest --cov", "Run tests")

        assert script.startswith("#")
        assert "Run tests" in script.split("\n")[0]

    def test_includes_command_in_script(self):
        """Generated script includes the actual command."""
        from generator.skills import generate_powershell_script

        script = generate_powershell_script("pytest", "pytest --cov", "Run tests")

        assert "pytest --cov" in script

    def test_uses_powershell_line_continuation(self):
        """Uses PowerShell line continuation (backtick) for multi-line."""
        from generator.skills import generate_powershell_script

        # Bash-style continuation
        command = "docker build -t myapp:latest \\\n  --build-arg VERSION=1.0"
        script = generate_powershell_script("docker-build", command, "Build")

        # Should convert to PowerShell style (backtick)
        assert "`" in script or "docker build" in script


class TestScriptGeneration:
    """Test script generation in SkillGenerator.generate()."""

    def test_generates_scripts_directory(self, tmp_path, sample_recipe_with_tools):
        """Creates scripts/ directory when tools present."""
        generator = SkillGenerator()
        output_dir = tmp_path / "test-skill"

        generator.generate(
            recipe=[sample_recipe_with_tools],
            skill_name="test-skill",
            format="copilot",
            output_dir=output_dir,
        )

        scripts_dir = output_dir / "scripts"
        assert scripts_dir.exists()
        assert scripts_dir.is_dir()

    def test_generates_both_sh_and_ps1_scripts(self, tmp_path, sample_recipe_with_tools):
        """Generates both .sh and .ps1 for each tool."""
        generator = SkillGenerator()
        output_dir = tmp_path / "test-skill"

        generator.generate(
            recipe=[sample_recipe_with_tools],
            skill_name="test-skill",
            format="copilot",
            output_dir=output_dir,
        )

        scripts_dir = output_dir / "scripts"
        # Should have pytest.sh and pytest.ps1
        assert (scripts_dir / "run-pytest.sh").exists()
        assert (scripts_dir / "run-pytest.ps1").exists()

    def test_script_names_are_sanitized(self, tmp_path):
        """Script names are sanitized (dots replaced, etc.)."""
        recipe = {
            "_recipe_name": "test",
            "tools": [
                {
                    "name": "coverage.py",
                    "command": "coverage report",
                    "purpose": "Coverage",
                }
            ],
        }
        generator = SkillGenerator()
        output_dir = tmp_path / "test-skill"

        generator.generate(
            recipe=[recipe],
            skill_name="test-skill",
            format="copilot",
            output_dir=output_dir,
        )

        scripts_dir = output_dir / "scripts"
        # coverage.py -> coverage-py
        assert (scripts_dir / "run-coverage-py.sh").exists()
        assert (scripts_dir / "run-coverage-py.ps1").exists()

    def test_handles_duplicate_tool_names(self, tmp_path):
        """Handles duplicate tool names by suffixing."""
        recipe = {
            "_recipe_name": "test",
            "tools": [
                {"name": "pytest", "command": "pytest --unit", "purpose": "Unit tests"},
                {
                    "name": "pytest",
                    "command": "pytest --integration",
                    "purpose": "Integration tests",
                },
            ],
        }
        generator = SkillGenerator()
        output_dir = tmp_path / "test-skill"

        generator.generate(
            recipe=[recipe],
            skill_name="test-skill",
            format="copilot",
            output_dir=output_dir,
        )

        scripts_dir = output_dir / "scripts"
        # Should create pytest.sh, pytest-2.sh
        assert (scripts_dir / "run-pytest.sh").exists()
        assert (scripts_dir / "run-pytest-2.sh").exists()

    def test_skips_scripts_when_no_tools(self, tmp_path, sample_recipe_no_tools):
        """Doesn't create scripts/ directory when no tools."""
        generator = SkillGenerator()
        output_dir = tmp_path / "test-skill"

        generator.generate(
            recipe=[sample_recipe_no_tools],
            skill_name="test-skill",
            format="copilot",
            output_dir=output_dir,
        )

        scripts_dir = output_dir / "scripts"
        assert not scripts_dir.exists()

    def test_combines_tools_from_multiple_recipes(self, tmp_path):
        """Combines tools from all recipes in multi-recipe skill."""
        recipe1 = {
            "_recipe_name": "test",
            "tools": [{"name": "pytest", "command": "pytest", "purpose": "Test"}],
        }
        recipe2 = {
            "_recipe_name": "review",
            "tools": [{"name": "ruff", "command": "ruff .", "purpose": "Lint"}],
        }
        generator = SkillGenerator()
        output_dir = tmp_path / "combined-skill"

        generator.generate(
            recipe=[recipe1, recipe2],
            skill_name="combined-skill",
            format="copilot",
            output_dir=output_dir,
        )

        scripts_dir = output_dir / "scripts"
        # Should have scripts from both recipes
        assert (scripts_dir / "run-pytest.sh").exists()
        assert (scripts_dir / "run-ruff.sh").exists()

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix file permissions test")
    def test_shell_scripts_are_executable(self, tmp_path, sample_recipe_with_tools):
        """Shell scripts (.sh) have executable permissions on Unix."""
        import stat

        generator = SkillGenerator()
        output_dir = tmp_path / "test-skill"

        generator.generate(
            recipe=[sample_recipe_with_tools],
            skill_name="test-skill",
            format="copilot",
            output_dir=output_dir,
        )

        script_file = output_dir / "scripts" / "run-pytest.sh"
        file_stat = script_file.stat()
        # Check if executable bit is set
        assert file_stat.st_mode & stat.S_IXUSR  # User execute permission

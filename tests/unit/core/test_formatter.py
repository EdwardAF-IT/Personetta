from __future__ import annotations

import pytest

from generator.formatter import (
    _build_frontmatter,
    build_cursor_baseline_markdown,
    build_cursor_router_markdown,
    format_cursor,
    format_copilot,
    format_claude,
    format_cline,
    humanize,
    replace_cursor_frontmatter,
)
from generator.output_formats import format_role, get_formatter

pytestmark = [pytest.mark.unit, pytest.mark.core, pytest.mark.readonly]


def test_format_role_cursor_always_apply_kwarg(composed_role):
    out_false = format_role(composed_role, "cursor", cursor_always_apply=False)
    assert "alwaysApply: false" in out_false
    out_true = format_role(composed_role, "cursor", cursor_always_apply=True)
    assert "alwaysApply: true" in out_true


@pytest.fixture
def composed_role() -> dict:
    return {
        "_recipe_name": "implement-python-backend-perf",
        "_recipe_description": "Implement performance-sensitive Python backend code.",
        "_source_roles": [
            "implementation-developer",
            "backend-developer",
            "python-developer",
            "performance-focused",
        ],
        "responsibilities": [
            "Write clean code",
            "Design API contracts",
            "Write idiomatic Python",
            "Evaluate algorithmic complexity",
        ],
        "non_responsibilities": [
            "Write tests",
            "Architectural redesign",
        ],
        "guidelines": [
            "Prefer explicit over implicit",
            "Never trust client input",
            "Use type hints",
            "Measure before optimizing",
        ],
        "tools": [
            {"name": "pytest", "purpose": "Testing"},
            {
                "name": "black",
                "purpose": "Code formatting",
                "when": "auto-format on save or pre-commit; run before ruff",
            },
            {
                "name": "ruff",
                "purpose": "Linting",
                "when": "default linter for all Python files; supersedes flake8 and isort",
            },
        ],
        "_model_recommendation": {
            "min_tier": "standard",
            "reasoning": "standard",
            "rationale": "4 composed roles; 4 guidelines; 3 tools; tier set by performance-focused",
        },
        "verification": [
            {"check": "Code passes linting", "command": "ruff check ."},
            {"check": "Code is formatted", "command": "black --check ."},
            {"check": "Business logic separated from handlers"},
        ],
        "tone": "pragmatic-and-clean",
        "output_format": "code-with-explanation",
        "examples": [
            {
                "scenario": "Implementing a retry mechanism",
                "input": "Add retry logic for flaky API calls",
                "output": "Implement with exponential backoff and jitter",
            },
        ],
        "tags": ["implementation", "python", "backend", "performance"],
    }


@pytest.fixture
def minimal_role() -> dict:
    return {
        "_recipe_name": "minimal-test",
        "_recipe_description": "",
        "_source_roles": ["role-a"],
        "responsibilities": ["Do the thing"],
    }


class TestHumanize:
    def test_hyphens_to_title(self):
        assert humanize("pragmatic-and-clean") == "Pragmatic And Clean"

    def test_underscores_to_title(self):
        assert humanize("code_with_explanation") == "Code With Explanation"

    def test_single_word(self):
        assert humanize("concise") == "Concise"


class TestBuildFrontmatter:
    def test_basic_frontmatter(self):
        result = _build_frontmatter("A test description.")
        assert result == '---\ndescription: "A test description."\nalwaysApply: true\n---'

    def test_escapes_double_quotes(self):
        result = _build_frontmatter('Say "hello" world')
        assert r"\"hello\"" in result

    def test_always_apply_defaults_true(self):
        result = _build_frontmatter("anything")
        assert "alwaysApply: true" in result

    def test_always_apply_can_be_false(self):
        result = _build_frontmatter("cache entry", always_apply=False)
        assert "alwaysApply: false" in result

    def test_is_valid_yaml(self):
        import yaml

        result = _build_frontmatter("Some role description.")
        body = result.strip("-").strip()
        parsed = yaml.safe_load(body)
        assert parsed["description"] == "Some role description."
        assert parsed["alwaysApply"] is True

    def test_does_not_contain_globs(self):
        result = _build_frontmatter("Any description")
        assert "globs" not in result

    def test_has_exactly_two_fields(self):
        import yaml

        result = _build_frontmatter("Test")
        body = result.strip("-").strip()
        parsed = yaml.safe_load(body)
        assert sorted(parsed.keys()) == ["alwaysApply", "description"]

    def test_em_dash_in_description(self):
        import yaml

        desc = "Backend code \u2014 optimized for speed"
        result = _build_frontmatter(desc)
        body = result.strip("-").strip()
        parsed = yaml.safe_load(body)
        assert parsed["description"] == desc

    def test_colon_in_description(self):
        import yaml

        desc = "Step 1: initialize the system"
        result = _build_frontmatter(desc)
        body = result.strip("-").strip()
        parsed = yaml.safe_load(body)
        assert parsed["description"] == desc

    def test_single_quotes_in_description(self):
        import yaml

        desc = "Handle edge cases like 'null' inputs"
        result = _build_frontmatter(desc)
        body = result.strip("-").strip()
        parsed = yaml.safe_load(body)
        assert parsed["description"] == desc

    def test_long_description(self):
        import yaml

        desc = "A " * 500 + "very long description."
        result = _build_frontmatter(desc)
        body = result.strip("-").strip()
        parsed = yaml.safe_load(body)
        assert parsed["description"] == desc

    def test_starts_and_ends_with_fences(self):
        result = _build_frontmatter("test")
        lines = result.split("\n")
        assert lines[0] == "---"
        assert lines[-1] == "---"


class TestReplaceCursorFrontmatter:
    def test_prepends_frontmatter_when_body_has_no_fence(self):
        body = "# Title\n\nHello."
        out = replace_cursor_frontmatter(body, "New desc", always_apply=True)
        assert out.startswith("---\n")
        assert 'description: "New desc"' in out
        assert "alwaysApply: true" in out
        assert out.endswith("Hello.")

    def test_replaces_existing_frontmatter(self):
        body = '---\ndescription: "Old"\nalwaysApply: false\n---\n\n# Hi\n'
        out = replace_cursor_frontmatter(body, "Replaced", always_apply=True)
        assert 'description: "Replaced"' in out
        assert "alwaysApply: true" in out
        assert "# Hi" in out
        assert "Old" not in out

    def test_opening_fence_without_closing_prepends_new_frontmatter(self):
        body = "---\ndescription: broken\n# still no closing fence\n\nContent."
        out = replace_cursor_frontmatter(body, "Fixed", always_apply=False)
        assert out.count("---") >= 3
        assert 'description: "Fixed"' in out
        assert "alwaysApply: false" in out


class TestBuildCursorBaselineMarkdown:
    def test_baseline_references_operating_contract_and_active_file(self):
        out = build_cursor_baseline_markdown()
        assert out.startswith("---\n")
        assert "alwaysApply: true" in out
        assert "Operating contract" in out
        assert "personetta-active.md" in out
        assert "aicontext" not in out.lower()
        assert "Cursor Settings tab" in out
        assert "6. **Cursor Settings tab**" in out


class TestBuildCursorRouterMarkdown:
    def test_empty_recipe_rows_still_has_header_and_always_apply_false(self):
        out = build_cursor_router_markdown([])
        assert out.startswith("---\n")
        assert "alwaysApply: false" in out
        assert "# Personetta — recipe router" in out
        assert "## Recipe index" in out

    def test_router_warns_on_boundaries_violation_redirect(self):
        out = build_cursor_router_markdown([])
        assert "violates" in out and "Boundaries" in out
        assert "out-of-scope" in out
        assert "set-active" in out

    def test_includes_recipe_sections_and_activation_phrases(self):
        rows = [
            {
                "name": "demo-recipe",
                "description": "Does demo things.",
                "activation_phrases": ["Act as demo"],
            }
        ]
        out = build_cursor_router_markdown(rows)
        assert "`demo-recipe`" in out
        assert "Does demo things." in out
        assert "Act as demo" in out
        assert "set-active demo-recipe" in out


class TestCursorFormat:
    def test_includes_frontmatter(self, composed_role):
        output = format_cursor(composed_role)
        assert output.startswith("---\n")
        assert (
            'description: "Implement performance-sensitive Python backend code."'
            in output
        )
        assert "alwaysApply: true" in output

    def test_frontmatter_before_title(self, composed_role):
        output = format_cursor(composed_role)
        fm_end = output.index("---", 3) + 3
        title_pos = output.index("# Implement Python Backend Perf")
        assert fm_end < title_pos

    def test_no_frontmatter_without_description(self, minimal_role):
        output = format_cursor(minimal_role)
        assert not output.startswith("---")

    def test_no_frontmatter_with_whitespace_only_description(self):
        role = {
            "_recipe_name": "whitespace-test",
            "_recipe_description": "   \n  ",
            "_source_roles": ["role-a"],
            "responsibilities": ["Do things"],
        }
        output = format_cursor(role)
        assert not output.startswith("---")

    def test_frontmatter_is_parseable_yaml(self, composed_role):
        import yaml

        output = format_cursor(composed_role)
        first_fence = output.index("---")
        second_fence = output.index("---", first_fence + 3)
        fm_body = output[first_fence + 3 : second_fence].strip()
        parsed = yaml.safe_load(fm_body)
        assert isinstance(parsed, dict)
        assert parsed["alwaysApply"] is True
        assert (
            parsed["description"]
            == "Implement performance-sensitive Python backend code."
        )

    def test_frontmatter_description_matches_recipe_description(self, composed_role):
        import yaml

        output = format_cursor(composed_role)
        first_fence = output.index("---")
        second_fence = output.index("---", first_fence + 3)
        fm_body = output[first_fence + 3 : second_fence].strip()
        parsed = yaml.safe_load(fm_body)
        assert parsed["description"] == composed_role["_recipe_description"]

    def test_frontmatter_does_not_include_globs(self, composed_role):
        output = format_cursor(composed_role)
        first_fence = output.index("---")
        second_fence = output.index("---", first_fence + 3)
        fm_block = output[first_fence : second_fence + 3]
        assert "globs" not in fm_block

    def test_includes_title(self, composed_role):
        output = format_cursor(composed_role)
        assert "# Implement Python Backend Perf" in output

    def test_includes_operating_contract_and_recipe_anchor(self, composed_role):
        output = format_cursor(composed_role)
        assert "## Operating contract" in output
        assert "`implement-python-backend-perf`" in output

    def test_model_blockquote_before_main_title(self, composed_role):
        output = format_cursor(composed_role)
        op_pos = output.index("## Operating contract")
        title_pos = output.index("# Implement Python Backend Perf")
        assert op_pos < title_pos
        model_pos = output.index("**Model recommendation:")
        assert model_pos < title_pos

    def test_includes_responsibilities(self, composed_role):
        output = format_cursor(composed_role)
        assert "## Responsibilities" in output
        assert "- Write clean code" in output
        assert "- Evaluate algorithmic complexity" in output

    def test_includes_boundaries(self, composed_role):
        output = format_cursor(composed_role)
        assert "## Boundaries" in output
        assert "- Write tests" in output

    def test_includes_guidelines(self, composed_role):
        output = format_cursor(composed_role)
        assert "## Guidelines" in output
        assert "- Measure before optimizing" in output

    def test_includes_tools(self, composed_role):
        output = format_cursor(composed_role)
        assert "## Tools" in output
        assert "**pytest**" in output
        assert "**black**" in output

    def test_includes_tone(self, composed_role):
        output = format_cursor(composed_role)
        assert "## Tone" in output
        assert "Pragmatic And Clean" in output

    def test_includes_examples(self, composed_role):
        output = format_cursor(composed_role)
        assert "## Examples" in output
        assert "### Implementing a retry mechanism" in output

    def test_includes_source_roles(self, composed_role):
        output = format_cursor(composed_role)
        assert "implementation-developer" in output

    def test_handles_minimal_role(self, minimal_role):
        output = format_cursor(minimal_role)
        assert "# Minimal Test" in output
        assert "- Do the thing" in output
        assert "## Operating contract" in output
        assert "`minimal-test`" in output
        assert "## Tools" not in output
        assert "## Tone" not in output


class TestCopilotFormat:
    def test_includes_title(self, composed_role):
        output = format_copilot(composed_role)
        assert "# Implement Python Backend Perf" in output

    def test_uses_you_should_heading(self, composed_role):
        output = format_copilot(composed_role)
        assert "## You Should" in output

    def test_uses_you_should_not_heading(self, composed_role):
        output = format_copilot(composed_role)
        assert "## You Should Not" in output

    def test_includes_preferred_tools(self, composed_role):
        output = format_copilot(composed_role)
        assert "## Preferred Tools" in output

    def test_handles_minimal_role(self, minimal_role):
        output = format_copilot(minimal_role)
        assert "# Minimal Test" in output
        assert "- Do the thing" in output

    def test_no_frontmatter_in_copilot(self, composed_role):
        output = format_copilot(composed_role)
        assert not output.startswith("---")
        assert "alwaysApply" not in output


class TestClaudeFormat:
    def test_uses_markdown_structure(self, composed_role):
        output = format_claude(composed_role)
        # Claude now uses markdown format (same as Copilot per REQUIREMENTS.md)
        assert output.startswith("# ")
        assert "## You Should" in output

    def test_includes_responsibilities_markdown(self, composed_role):
        output = format_claude(composed_role)
        assert "## You Should" in output
        assert "- Write clean code" in output

    def test_includes_boundaries_markdown(self, composed_role):
        output = format_claude(composed_role)
        assert "## You Should Not" in output
        assert "- Write tests" in output

    def test_includes_guidelines_markdown(self, composed_role):
        output = format_claude(composed_role)
        assert "## Guidelines" in output

    def test_includes_tools_markdown(self, composed_role):
        output = format_claude(composed_role)
        assert "## Preferred Tools" in output
        assert "**pytest**" in output

    def test_includes_tone_markdown(self, composed_role):
        output = format_claude(composed_role)
        assert "## Tone: Pragmatic And Clean" in output

    def test_includes_examples_markdown(self, composed_role):
        output = format_claude(composed_role)
        assert "## Examples" in output

    def test_handles_minimal_role(self, minimal_role):
        output = format_claude(minimal_role)
        assert "# Minimal Test" in output
        assert "- Do the thing" in output
        assert "## Preferred Tools" not in output

    def test_no_frontmatter_in_claude(self, composed_role):
        output = format_claude(composed_role)
        assert not output.startswith("---")
        assert "alwaysApply" not in output


class TestToolWhenField:
    def test_cursor_renders_when(self, composed_role):
        output = format_cursor(composed_role)
        assert (
            "*(When: default linter for all Python files; supersedes flake8 and isort)*"
            in output
        )

    def test_cursor_omits_when_if_absent(self, composed_role):
        output = format_cursor(composed_role)
        line = [ln for ln in output.splitlines() if "**pytest**" in ln][0]
        assert "When:" not in line

    def test_copilot_renders_when(self, composed_role):
        output = format_copilot(composed_role)
        assert "*(When: auto-format on save or pre-commit; run before ruff)*" in output

    def test_claude_renders_when_as_markdown(self, composed_role):
        output = format_claude(composed_role)
        # Claude uses markdown format like Copilot
        assert (
            "*(When: default linter for all Python files; supersedes flake8 and isort)*"
            in output
        )

    def test_claude_omits_when_if_absent(self, composed_role):
        output = format_claude(composed_role)
        line = [ln for ln in output.splitlines() if "**pytest**" in ln][0]
        assert "When:" not in line


class TestModelRecommendation:
    def test_cursor_shows_recommendation(self, composed_role):
        output = format_cursor(composed_role)
        assert "**Model recommendation: Standard tier, standard thinking**" in output

    def test_cursor_shows_rationale(self, composed_role):
        output = format_cursor(composed_role)
        assert "tier set by performance-focused" in output

    def test_cursor_shows_surfacing_instruction(self, composed_role):
        output = format_cursor(composed_role)
        assert "Tell the user this recommendation before starting work" in output

    def test_copilot_shows_recommendation(self, composed_role):
        output = format_copilot(composed_role)
        assert "**Model recommendation: Standard tier, standard thinking**" in output

    def test_copilot_shows_surfacing_instruction(self, composed_role):
        output = format_copilot(composed_role)
        assert "Tell the user this recommendation before starting work" in output

    def test_claude_shows_recommendation_markdown(self, composed_role):
        output = format_claude(composed_role)
        # Claude uses markdown format like Copilot
        assert "**Model recommendation: Standard tier, standard thinking**" in output

    def test_claude_shows_surfacing_instruction(self, composed_role):
        output = format_claude(composed_role)
        assert "Tell the user this recommendation before starting work" in output

    def test_no_recommendation_when_absent(self, minimal_role):
        for fmt in [format_cursor, format_copilot, format_claude, format_cline]:
            output = fmt(minimal_role)
            assert "Model recommendation" not in output
            assert "model_recommendation" not in output

    def test_fast_tier_no_thinking_label(self):
        role = {
            "_recipe_name": "simple-test",
            "_recipe_description": "",
            "_source_roles": ["role-a"],
            "responsibilities": ["Do things"],
            "_model_recommendation": {
                "min_tier": "fast",
                "reasoning": "none",
                "rationale": "1 guideline; 0 tools",
            },
        }
        output = format_cursor(role)
        assert "Fast tier, no thinking" in output

    def test_advanced_tier_extended_thinking_label(self):
        role = {
            "_recipe_name": "complex-test",
            "_recipe_description": "",
            "_source_roles": ["role-a"],
            "responsibilities": ["Design systems"],
            "_model_recommendation": {
                "min_tier": "advanced",
                "reasoning": "extended",
                "rationale": "architecture work",
            },
        }
        output = format_cursor(role)
        assert "Advanced tier, extended thinking" in output


class TestVerificationSection:
    def test_cursor_renders_verification_heading(self, composed_role):
        output = format_cursor(composed_role)
        assert "## Verification" in output

    def test_cursor_renders_command_check(self, composed_role):
        output = format_cursor(composed_role)
        assert "- [ ] Code passes linting — `ruff check .`" in output

    def test_cursor_renders_self_assess_check(self, composed_role):
        output = format_cursor(composed_role)
        assert "- [ ] Business logic separated from handlers *(self-assess)*" in output

    def test_copilot_renders_verification(self, composed_role):
        output = format_copilot(composed_role)
        assert "## Verification" in output
        assert "- [ ] Code is formatted — `black --check .`" in output

    def test_cline_renders_verification(self, composed_role):
        output = format_cline(composed_role)
        assert output == format_copilot(composed_role)
        assert "## Verification" in output

    def test_claude_renders_verification_markdown(self, composed_role):
        output = format_claude(composed_role)
        # Claude uses markdown format like Copilot
        assert "## Verification" in output
        assert "- [ ] Code passes linting — `ruff check .`" in output

    def test_claude_self_assess_markdown(self, composed_role):
        output = format_claude(composed_role)
        assert "- [ ] Business logic separated from handlers *(self-assess)*" in output

    def test_no_verification_when_absent(self, minimal_role):
        for fmt in [format_cursor, format_copilot, format_cline]:
            output = fmt(minimal_role)
            assert "## Verification" not in output
        output = format_claude(minimal_role)
        assert "## Verification" not in output


class TestComplianceFooter:
    def test_cursor_has_compliance_section(self, composed_role):
        output = format_cursor(composed_role)
        assert "## Compliance" in output

    def test_cursor_compliance_after_verification(self, composed_role):
        output = format_cursor(composed_role)
        verification_pos = output.index("## Verification")
        compliance_pos = output.index("## Compliance")
        assert compliance_pos > verification_pos

    def test_cursor_compliance_instruction_content(self, composed_role):
        output = format_cursor(composed_role)
        assert "end with a **Role compliance** heading" in output
        assert "**Verification**" in output
        assert "**Guidelines**" in output
        assert "**Persona**" in output

    def test_copilot_has_compliance_section(self, composed_role):
        output = format_copilot(composed_role)
        assert "## Compliance" in output

    def test_cline_has_compliance_section(self, composed_role):
        output = format_cline(composed_role)
        assert "## Compliance" in output

    def test_claude_has_compliance_section(self, composed_role):
        output = format_claude(composed_role)
        # Claude uses markdown format like Copilot
        assert "## Compliance" in output
        assert "end your response with a **Role compliance** section" in output

    def test_minimal_role_still_has_compliance(self, minimal_role):
        output = format_cursor(minimal_role)
        assert "## Compliance" in output

    def test_compliance_is_last_section_cursor(self, composed_role):
        output = format_cursor(composed_role)
        last_heading_pos = output.rindex("## Compliance")
        no_heading_after = "## " not in output[last_heading_pos + len("## Compliance") :]
        assert no_heading_after


class TestGetFormatter:
    def test_returns_cursor_formatter(self):
        formatter = get_formatter("cursor")
        assert formatter is format_cursor

    def test_returns_copilot_formatter(self):
        formatter = get_formatter("copilot")
        assert formatter is format_copilot

    def test_returns_claude_formatter(self):
        formatter = get_formatter("claude")
        assert formatter is format_claude

    def test_returns_cline_formatter(self):
        formatter = get_formatter("cline")
        assert formatter is format_cline

    def test_unknown_format_raises(self):
        with pytest.raises(ValueError, match="Unknown format"):
            get_formatter("unknown-tool")


class TestFormatRole:
    def test_dispatches_to_correct_formatter(self, composed_role):
        cursor_output = format_role(composed_role, "cursor")
        copilot_output = format_role(composed_role, "copilot")
        claude_output = format_role(composed_role, "claude")
        cline_output = format_role(composed_role, "cline")

        assert "## Responsibilities" in cursor_output
        assert "## You Should" in copilot_output
        # Claude uses markdown like Copilot
        assert "## You Should" in claude_output
        assert cline_output == copilot_output

    def test_cline_matches_copilot_markdown(self, composed_role):
        assert format_cline(composed_role) == format_copilot(composed_role)

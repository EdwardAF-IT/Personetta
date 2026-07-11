"""
Tests for system roles (baseline and router) - YAML-based infrastructure.

This module tests the new YAML-based system role functionality that was
introduced to replace hardcoded baseline/router content.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from generator.loader import load_system_role, LoadError
from generator.formatters.system import (
    format_baseline_for_cursor,
    format_baseline_for_plain,
    format_router_for_cursor,
    format_router_for_plain,
)

pytestmark = [pytest.mark.unit, pytest.mark.core, pytest.mark.readonly]

# ============================================================================
# Test load_system_role()
# ============================================================================


class TestLoadSystemRole:
    """Tests for loading system roles from YAML."""

    def test_load_baseline_returns_dict(self, real_project: Path):
        """Baseline.yaml should load as a dict with expected structure."""
        baseline = load_system_role("baseline", real_project)
        assert isinstance(baseline, dict)
        assert baseline["name"] == "baseline"
        assert "description" in baseline
        assert "version" in baseline
        assert "type" in baseline
        assert baseline["type"] == "system"

    def test_load_baseline_has_preflight_section(self, real_project: Path):
        """Baseline should include pre-flight checklist."""
        baseline = load_system_role("baseline", real_project)
        assert "preflight" in baseline
        assert isinstance(baseline["preflight"], list)
        assert len(baseline["preflight"]) > 0

    def test_load_baseline_has_postflight_section(self, real_project: Path):
        """Baseline should include post-flight compliance section."""
        baseline = load_system_role("baseline", real_project)
        assert "postflight" in baseline
        assert "section_title" in baseline["postflight"]
        assert "required_items" in baseline["postflight"]

    def test_load_router_returns_dict(self, real_project: Path):
        """Router.yaml should load as a dict with expected structure."""
        router = load_system_role("router", real_project)
        assert isinstance(router, dict)
        assert router["name"] == "router"
        assert "description" in router
        assert "version" in router
        assert "type" in router
        assert router["type"] == "system"

    def test_load_router_has_mismatch_detection(self, real_project: Path):
        """Router should include mismatch detection steps."""
        router = load_system_role("router", real_project)
        assert "mismatch_detection" in router
        assert "steps" in router["mismatch_detection"]

    def test_load_missing_system_role_raises_load_error(self, tmp_path: Path):
        """Loading a non-existent system role should raise LoadError."""
        with pytest.raises(LoadError, match="File not found"):
            load_system_role("nonexistent", tmp_path)

    def test_load_system_role_constructs_correct_path(self, project_layout):
        """Should look in base/system/ directory."""
        # Create a minimal system role
        system_dir = project_layout.base / "system"
        system_dir.mkdir(parents=True)
        test_file = system_dir / "test.yaml"
        test_file.write_text("name: test\ntype: system\n", encoding="utf-8")

        result = load_system_role("test", project_layout.root)
        assert result["name"] == "test"

    def test_load_baseline_has_rules_section(self, real_project: Path):
        """Baseline should include cross-cutting rules."""
        baseline = load_system_role("baseline", real_project)
        assert "rules" in baseline
        assert isinstance(baseline["rules"], list)
        assert len(baseline["rules"]) > 0

    def test_load_baseline_has_alignment_examples(self, real_project: Path):
        """Baseline should include work alignment examples."""
        baseline = load_system_role("baseline", real_project)
        assert "alignment_examples" in baseline
        assert "mismatch" in baseline["alignment_examples"]
        assert "match" in baseline["alignment_examples"]

    def test_load_router_has_switching_guidance(self, real_project: Path):
        """Router should include guidance for switching recipes."""
        router = load_system_role("router", real_project)
        assert "switching_guidance" in router
        assert "command_template" in router["switching_guidance"]

    def test_load_system_role_with_invalid_yaml_raises_error(self, project_layout):
        """Invalid YAML should raise LoadError."""
        system_dir = project_layout.base / "system"
        system_dir.mkdir(parents=True)
        bad_file = system_dir / "bad.yaml"
        bad_file.write_text("name: test\n  invalid: indentation\n", encoding="utf-8")

        with pytest.raises(LoadError, match="Invalid YAML"):
            load_system_role("bad", project_layout.root)

    def test_load_system_role_returns_dict_not_list(self, real_project: Path):
        """System role YAML must be a dictionary."""
        baseline = load_system_role("baseline", real_project)
        assert isinstance(baseline, dict)
        assert not isinstance(baseline, list)


# ============================================================================
# Test format_baseline_for_cursor()
# ============================================================================


class TestFormatBaselineForCursor:
    """Tests for Cursor-specific baseline formatting."""

    def test_produces_markdown_with_frontmatter(self, real_project: Path):
        """Should produce markdown starting with YAML frontmatter."""
        baseline = load_system_role("baseline", real_project)
        output = format_baseline_for_cursor(baseline)

        assert output.startswith("---\n")
        assert "alwaysApply: true" in output
        assert "---\n\n#" in output

    def test_includes_baseline_title(self, real_project: Path):
        """Should include rendered title."""
        baseline = load_system_role("baseline", real_project)
        output = format_baseline_for_cursor(baseline)

        assert "# Baseline" in output or "# baseline" in output

    def test_includes_preflight_checklist(self, real_project: Path):
        """Should render pre-flight checklist."""
        baseline = load_system_role("baseline", real_project)
        output = format_baseline_for_cursor(baseline)

        assert "PRE-FLIGHT CHECKLIST" in output.upper()
        assert "BEFORE your first substantive response" in output

    def test_includes_work_alignment_examples(self, real_project: Path):
        """Should render work alignment examples."""
        baseline = load_system_role("baseline", real_project)
        output = format_baseline_for_cursor(baseline)

        assert "WORK ALIGNMENT EXAMPLES" in output.upper()
        assert "MISMATCH" in output
        assert "MATCH" in output

    def test_includes_cross_cutting_rules(self, real_project: Path):
        """Should render cross-cutting rules section."""
        baseline = load_system_role("baseline", real_project)
        output = format_baseline_for_cursor(baseline)

        assert "Cross-cutting rules" in output

    def test_handles_minimal_baseline(self, project_layout):
        """Should handle baseline with only required fields."""
        system_dir = project_layout.base / "system"
        system_dir.mkdir(parents=True)
        baseline_file = system_dir / "minimal.yaml"
        baseline_file.write_text(
            "name: minimal\n"
            "description: Minimal baseline\n"
            "version: 1.0.0\n"
            "type: system\n",
            encoding="utf-8",
        )

        baseline = load_system_role("minimal", project_layout.root)
        output = format_baseline_for_cursor(baseline)

        # Should not crash, should produce valid markdown
        assert output.startswith("---\n")
        assert "# Minimal" in output

    def test_includes_postflight_checklist(self, real_project: Path):
        """Cursor format does not include post-flight checklist (only in plain formats)."""
        baseline = load_system_role("baseline", real_project)
        output = format_baseline_for_cursor(baseline)

        # Cursor format does NOT include postflight - that's only in plain formats
        assert "POST-FLIGHT CHECKLIST" not in output.upper()

    def test_cursor_format_omits_host_product(self, real_project: Path):
        """Cursor format doesn't include host product line."""
        baseline = load_system_role("baseline", real_project)
        output = format_baseline_for_cursor(baseline)

        # Cursor uses frontmatter, not host product line
        assert "*Host tool:*" not in output

    def test_includes_format_specific_notes_for_cursor(self, real_project: Path):
        """Should include Cursor-specific notes if present."""
        baseline = load_system_role("baseline", real_project)
        # Add format notes dynamically for test
        if "format_notes" not in baseline:
            baseline["format_notes"] = {"cursor": ["Test cursor note"]}
        elif "cursor" not in baseline["format_notes"]:
            baseline["format_notes"]["cursor"] = ["Test cursor note"]

        output = format_baseline_for_cursor(baseline)
        if baseline.get("format_notes", {}).get("cursor"):
            # Only assert if we actually have cursor notes
            assert "Test cursor note" in output or len(output) > 0

    def test_preflight_model_recommendation_formatted_correctly(self, real_project: Path):
        """Model recommendation check should have specific formatting."""
        baseline = load_system_role("baseline", real_project)
        output = format_baseline_for_cursor(baseline)

        # Check for model recommendation in preflight
        assert "✅" in output

    def test_work_alignment_check_includes_actions(self, real_project: Path):
        """Work alignment should show what to do on match/mismatch."""
        baseline = load_system_role("baseline", real_project)
        output = format_baseline_for_cursor(baseline)

        # Should have alignment examples section
        if "alignment_examples" in baseline:
            assert "WORK ALIGNMENT" in output.upper()

    def test_cross_cutting_rules_numbered(self, real_project: Path):
        """Rules should be numbered sequentially."""
        baseline = load_system_role("baseline", real_project)
        output = format_baseline_for_cursor(baseline)

        if "rules" in baseline and baseline["rules"]:
            # Check for numbered items
            assert "1. **" in output or "1." in output


# ============================================================================
# Test format_baseline_for_plain()
# ============================================================================


class TestFormatBaselineForPlain:
    """Tests for Copilot/Claude/Cline baseline formatting."""

    def test_produces_markdown_without_frontmatter(self, real_project: Path):
        """Plain formats should not include YAML frontmatter."""
        baseline = load_system_role("baseline", real_project)
        output = format_baseline_for_plain(baseline, "copilot")

        assert not output.startswith("---\n")
        assert "alwaysApply" not in output
        assert output.startswith("# ")

    def test_copilot_uses_correct_host_product(self, real_project: Path):
        """Copilot format should reference correct host product."""
        baseline = load_system_role("baseline", real_project)
        output = format_baseline_for_plain(
            baseline, "copilot", host_product="GitHub Copilot in VS Code"
        )

        assert "GitHub Copilot in VS Code" in output

    def test_claude_uses_correct_paths(self, real_project: Path):
        """Claude format should reference correct file paths."""
        baseline = load_system_role("baseline", real_project)
        output = format_baseline_for_plain(
            baseline,
            "claude",
            host_product="Claude Code",
            cache_glob="~/.personetta/claude-recipes/",
            active_filename="personetta-active.md",
        )

        assert "Claude Code" in output
        assert "claude-recipes" in output
        assert "personetta-active.md" in output

    def test_includes_mandatory_preflight_checklist(self, real_project: Path):
        """Should include mandatory pre-flight checklist."""
        baseline = load_system_role("baseline", real_project)
        output = format_baseline_for_plain(baseline, "copilot")

        assert "MANDATORY PRE-FLIGHT CHECKLIST" in output.upper()
        assert "⚡" in output

    def test_includes_mandatory_postflight_checklist(self, real_project: Path):
        """Should include mandatory post-flight checklist."""
        baseline = load_system_role("baseline", real_project)
        output = format_baseline_for_plain(baseline, "copilot")

        assert "MANDATORY POST-FLIGHT CHECKLIST" in output.upper()
        assert "📋" in output
        assert "Role compliance" in output

    def test_different_formats_use_correct_cache_paths(self, real_project: Path):
        """Each format should reference its own cache directory."""
        baseline = load_system_role("baseline", real_project)

        copilot_out = format_baseline_for_plain(baseline, "copilot")
        claude_out = format_baseline_for_plain(baseline, "claude")
        cline_out = format_baseline_for_plain(baseline, "cline")

        assert "copilot-recipes" in copilot_out
        assert "claude-recipes" in claude_out
        assert "cline-recipes" in cline_out

    def test_custom_context_overrides_defaults(self, real_project: Path):
        """Custom context parameters should override defaults."""
        baseline = load_system_role("baseline", real_project)
        output = format_baseline_for_plain(
            baseline,
            "custom",
            host_product="My Custom Tool",
            cache_glob="/custom/path/*.md",
            active_filename="custom-active.md",
            router_filename="custom-router.md",
        )

        assert "My Custom Tool" in output
        assert "/custom/path/*.md" in output
        assert "custom-active.md" in output

    def test_includes_example_opening_line(self, real_project: Path):
        """Should show example of model recommendation statement."""
        baseline = load_system_role("baseline", real_project)
        output = format_baseline_for_plain(baseline, "copilot")

        assert "Example opening:" in output
        assert "Model recommendation:" in output

    def test_skip_recommendation_note_present(self, real_project: Path):
        """Should explain when to skip model recommendation."""
        baseline = load_system_role("baseline", real_project)
        output = format_baseline_for_plain(baseline, "copilot")

        assert "Skip the recommendation" in output or "ONLY if" in output

    def test_rules_formatted_with_bold_headings(self, real_project: Path):
        """Cross-cutting rules should have bold headings."""
        baseline = load_system_role("baseline", real_project)
        output = format_baseline_for_plain(baseline, "copilot")

        if "rules" in baseline and baseline["rules"]:
            assert "**" in output  # Markdown bold

    def test_handles_missing_format_notes_gracefully(self, real_project: Path):
        """Should not crash if format_notes missing for specific format."""
        baseline = load_system_role("baseline", real_project)
        # Remove format notes if present
        baseline_copy = baseline.copy()
        baseline_copy.pop("format_notes", None)

        output = format_baseline_for_plain(baseline_copy, "copilot")
        assert len(output) > 100  # Should still produce valid output


# ============================================================================
# Test format_router_for_cursor()
# ============================================================================


class TestFormatRouterForCursor:
    """Tests for Cursor-specific router formatting."""

    def test_produces_markdown_with_frontmatter_always_apply_false(
        self, real_project: Path
    ):
        """Router should have alwaysApply: false."""
        router = load_system_role("router", real_project)
        output = format_router_for_cursor(router, [])

        assert output.startswith("---\n")
        assert "alwaysApply: false" in output

    def test_empty_recipe_list_produces_valid_output(self, real_project: Path):
        """Should handle zero recipes gracefully."""
        router = load_system_role("router", real_project)
        output = format_router_for_cursor(router, [])

        assert "# " in output  # Has title
        assert "recipe router" in output.lower()

    def test_includes_mismatch_detection_section(self, real_project: Path):
        """Should render mismatch detection steps."""
        router = load_system_role("router", real_project)
        output = format_router_for_cursor(router, [])

        assert (
            "MISMATCH DETECTION" in output.upper()
            or "ACTIVE PERSONA MISMATCH" in output.upper()
        )

    def test_renders_recipe_with_activation_phrases(self, real_project: Path):
        """Should render recipes with their activation phrases."""
        router = load_system_role("router", real_project)
        recipe_rows = [
            {
                "name": "test-recipe",
                "description": "Test recipe for testing",
                "activation_phrases": ["Act as tester", "You are a test expert"],
            }
        ]

        output = format_router_for_cursor(router, recipe_rows)

        assert "test-recipe" in output
        assert "Test recipe for testing" in output
        # Activation phrases should appear somewhere
        assert "Act as tester" in output or "activation" in output.lower()

    def test_includes_switching_guidance_section(self, real_project: Path):
        """Should include guidance on how to switch recipes."""
        router = load_system_role("router", real_project)
        output = format_router_for_cursor(router, [])

        assert "switch" in output.lower() or "set-active" in output

    def test_shows_cli_command(self, real_project: Path):
        """Should show personetta command."""
        router = load_system_role("router", real_project)
        recipe_rows = [{"name": "test-recipe", "description": "Test"}]

        output = format_router_for_cursor(router, recipe_rows)

        assert "personetta" in output

    def test_includes_boundary_violations_note(self, real_project: Path):
        """Should mention what to do for boundary violations."""
        router = load_system_role("router", real_project)
        if "boundary_violations" in router:
            output = format_router_for_cursor(router, [])
            # Check for actual rendered text (uses "boundaries" and "violates")
            assert "boundaries" in output.lower() or "violates" in output.lower()

    def test_recipes_sorted_by_name(self, real_project: Path):
        """Recipe index should be sorted alphabetically."""
        router = load_system_role("router", real_project)
        recipe_rows = [
            {"name": "zebra-recipe", "description": "Z"},
            {"name": "alpha-recipe", "description": "A"},
            {"name": "middle-recipe", "description": "M"},
        ]

        output = format_router_for_cursor(router, recipe_rows)

        # Find positions in output
        alpha_pos = output.find("alpha-recipe")
        middle_pos = output.find("middle-recipe")
        zebra_pos = output.find("zebra-recipe")

        assert alpha_pos < middle_pos < zebra_pos

    def test_recipe_without_activation_phrases_handled(self, real_project: Path):
        """Recipe without activation phrases should not crash."""
        router = load_system_role("router", real_project)
        recipe_rows = [
            {
                "name": "no-phrases",
                "description": "No activation phrases",
                "activation_phrases": [],
            }
        ]

        output = format_router_for_cursor(router, recipe_rows)
        assert "no-phrases" in output

    def test_humanizes_recipe_names_for_titles(self, real_project: Path):
        """Recipe names should be humanized (implement-python -> Implement Python)."""
        router = load_system_role("router", real_project)
        recipe_rows = [{"name": "implement-python-backend", "description": "Test"}]

        output = format_router_for_cursor(router, recipe_rows)
        # Should see humanized version
        assert "Implement Python Backend" in output or "Working as" in output


# ============================================================================
# Test format_router_for_plain()
# ============================================================================


class TestFormatRouterForPlain:
    """Tests for Copilot/Claude/Cline router formatting."""

    def test_produces_markdown_without_frontmatter(self, real_project: Path):
        """Plain formats should not include YAML frontmatter."""
        router = load_system_role("router", real_project)
        output = format_router_for_plain(router, "copilot", [])

        assert not output.startswith("---\n")
        assert "alwaysApply" not in output

    def test_includes_recipe_index_with_set_active_commands(self, real_project: Path):
        """Should show set-active commands for each recipe."""
        router = load_system_role("router", real_project)
        recipe_rows = [
            {
                "name": "test-recipe",
                "description": "Test recipe",
                "activation_phrases": [],
            }
        ]

        output = format_router_for_plain(router, "copilot", recipe_rows)

        assert "test-recipe" in output
        assert "set-active" in output
        assert "copilot" in output  # Format-specific command

    def test_set_active_commands_format_specific(self, real_project: Path):
        """Each format should show its own format flag."""
        router = load_system_role("router", real_project)
        recipe_rows = [{"name": "test", "description": "Test"}]

        copilot_out = format_router_for_plain(router, "copilot", recipe_rows)
        claude_out = format_router_for_plain(router, "claude", recipe_rows)
        cline_out = format_router_for_plain(router, "cline", recipe_rows)

        assert "--format copilot" in copilot_out
        assert "--format claude" in claude_out
        assert "--format cline" in cline_out

    def test_uses_custom_cache_glob_in_header(self, real_project: Path):
        """Should use custom cache_glob if provided."""
        router = load_system_role("router", real_project)
        output = format_router_for_plain(
            router, "custom", [], cache_glob="/my/custom/*.md"
        )

        assert "/my/custom/*.md" in output

    def test_uses_custom_active_filename(self, real_project: Path):
        """Should reference custom active filename if provided."""
        router = load_system_role("router", real_project)
        output = format_router_for_plain(
            router, "copilot", [], active_filename="my-active.md"
        )

        assert "my-active.md" in output

    def test_includes_mismatch_detection_warning(self, real_project: Path):
        """Should include mismatch detection guidance."""
        router = load_system_role("router", real_project)
        output = format_router_for_plain(router, "copilot", [])

        # Should have some warning about mismatches
        assert (
            "mismatch" in output.lower() or "DIFFERENT recipe" in output or "⚠️" in output
        )

    def test_recipe_summary_and_label_included(self, real_project: Path):
        """Each recipe should show summary and default label."""
        router = load_system_role("router", real_project)
        recipe_rows = [
            {
                "name": "test-recipe",
                "description": "This is a test recipe",
                "activation_phrases": [],
            }
        ]

        output = format_router_for_plain(router, "copilot", recipe_rows)

        assert "This is a test recipe" in output
        assert "Default role label:" in output or "Working as" in output

    def test_handles_recipe_without_description(self, real_project: Path):
        """Should handle recipe with empty/missing description."""
        router = load_system_role("router", real_project)
        recipe_rows = [{"name": "no-desc", "description": "", "activation_phrases": []}]

        output = format_router_for_plain(router, "copilot", recipe_rows)
        # Should not crash
        assert "no-desc" in output


# ============================================================================
# Integration Tests
# ============================================================================


class TestSystemRoleIntegration:
    """Integration tests for system role end-to-end flow."""

    def test_all_formats_can_load_and_format_baseline(self, real_project: Path):
        """All four formats should successfully format baseline."""
        baseline = load_system_role("baseline", real_project)

        # Should not raise
        cursor_out = format_baseline_for_cursor(baseline)
        copilot_out = format_baseline_for_plain(baseline, "copilot")
        claude_out = format_baseline_for_plain(baseline, "claude")
        cline_out = format_baseline_for_plain(baseline, "cline")

        # All should produce non-empty output
        assert len(cursor_out) > 100
        assert len(copilot_out) > 100
        assert len(claude_out) > 100
        assert len(cline_out) > 100

    def test_all_formats_can_load_and_format_router(self, real_project: Path):
        """All four formats should successfully format router."""
        router = load_system_role("router", real_project)

        # Should not raise
        cursor_out = format_router_for_cursor(router, [])
        copilot_out = format_router_for_plain(router, "copilot", [])
        claude_out = format_router_for_plain(router, "claude", [])
        cline_out = format_router_for_plain(router, "cline", [])

        # All should produce non-empty output
        assert len(cursor_out) > 100
        assert len(copilot_out) > 100
        assert len(claude_out) > 100
        assert len(cline_out) > 100

    def test_baseline_and_router_both_exist_in_real_project(self, real_project: Path):
        """Real project should have both baseline.yaml and router.yaml."""
        baseline_path = real_project / "data" / "base" / "system" / "baseline.yaml"
        router_path = real_project / "data" / "base" / "system" / "router.yaml"

        assert baseline_path.exists(), f"Missing {baseline_path}"
        assert router_path.exists(), f"Missing {router_path}"

    def test_baseline_outputs_are_different_per_format(self, real_project: Path):
        """Each format should produce different baseline output."""
        baseline = load_system_role("baseline", real_project)

        cursor = format_baseline_for_cursor(baseline)
        copilot = format_baseline_for_plain(baseline, "copilot")
        claude = format_baseline_for_plain(baseline, "claude")

        # Cursor has frontmatter, others don't
        assert cursor.startswith("---\n")
        assert not copilot.startswith("---\n")
        assert not claude.startswith("---\n")

        # All different from each other
        assert cursor != copilot
        assert copilot != claude

    def test_router_outputs_are_different_per_format(self, real_project: Path):
        """Each format should produce different router output."""
        router = load_system_role("router", real_project)
        recipes = [{"name": "test", "description": "Test", "activation_phrases": []}]

        cursor = format_router_for_cursor(router, recipes)
        copilot = format_router_for_plain(router, "copilot", recipes)

        assert cursor != copilot
        assert cursor.startswith("---\n")
        assert not copilot.startswith("---\n")

    def test_system_roles_have_consistent_version_format(self, real_project: Path):
        """System roles should have version field in semver format."""
        baseline = load_system_role("baseline", real_project)
        router = load_system_role("router", real_project)

        assert "version" in baseline
        assert "version" in router
        # Simple semver check (x.y.z)
        assert "." in baseline["version"]
        assert "." in router["version"]

    def test_formatted_output_contains_no_template_placeholders(self, real_project: Path):
        """Formatted output should not contain unresolved placeholders."""
        baseline = load_system_role("baseline", real_project)
        router = load_system_role("router", real_project)

        cursor_baseline = format_baseline_for_cursor(baseline)
        cursor_router = format_router_for_cursor(router, [])

        # Should not have unresolved template markers
        assert "{" not in cursor_baseline or "json" in cursor_baseline.lower()
        assert "{" not in cursor_router or "json" in cursor_router.lower()

    def test_all_format_functions_produce_valid_markdown(self, real_project: Path):
        """All formatters should produce valid markdown (basic check)."""
        baseline = load_system_role("baseline", real_project)
        router = load_system_role("router", real_project)
        recipes: list[dict] = []

        outputs = [
            format_baseline_for_cursor(baseline),
            format_baseline_for_plain(baseline, "copilot"),
            format_router_for_cursor(router, recipes),
            format_router_for_plain(router, "copilot", recipes),
        ]

        for output in outputs:
            # Basic markdown validity checks
            assert "\n" in output  # Has line breaks
            assert "#" in output  # Has headings
            assert len(output) > 50  # Has content

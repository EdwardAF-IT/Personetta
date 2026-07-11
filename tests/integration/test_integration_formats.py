from __future__ import annotations


import pytest


from generator.loader import (
    load_recipe,
    load_recipe_roles,
    load_merge_config,
    list_recipes,
)
from generator.merger import compose_recipe
from generator.output_formats import FORMAT_NAMES, format_role

from tests.integration.helpers import add_recipe, install_all_for_format

pytestmark = [pytest.mark.integration, pytest.mark.slow]


class TestInstallAllMultiFormat:
    """Test install-all across different output formats."""

    def test_install_all_copilot(self, populated_project, tmp_path):
        target = tmp_path / "output"
        install_all_for_format(populated_project, target, "copilot")

        inst = target / ".copilot" / "instructions"
        active = inst / "personetta-active.instructions.md"
        assert active.exists()
        content = active.read_text(encoding="utf-8")
        assert "## You Should" in content
        assert content.startswith("---")
        assert "applyTo:" in content

    def test_install_all_claude(self, populated_project, tmp_path):
        target = tmp_path / "output"
        install_all_for_format(populated_project, target, "claude")

        rules_dir = target / ".claude" / "rules"
        assert {f.name for f in rules_dir.glob("*.md")} == {
            "personetta-active.md",
            "personetta-baseline.md",
            "personetta-router.md",
        }
        recipes = list_recipes(populated_project)
        cache_names = sorted(
            f.stem for f in (target / ".personetta" / "claude-recipes").glob("*.md")
        )
        assert cache_names == sorted(r["name"] for r in recipes)
        active = (rules_dir / "personetta-active.md").read_text(encoding="utf-8")
        assert "## You Should" in active

    def test_install_all_cline(self, populated_project, tmp_path):
        target = tmp_path / "output"
        install_all_for_format(populated_project, target, "cline")

        cline_dir = target / "Documents" / "Cline" / "Rules"
        assert {f.name for f in cline_dir.glob("*.md")} == {
            "personetta-active.md",
            "personetta-baseline.md",
            "personetta-router.md",
        }
        recipes = list_recipes(populated_project)
        cache_names = sorted(
            f.stem for f in (target / ".personetta" / "cline-recipes").glob("*.md")
        )
        assert cache_names == sorted(r["name"] for r in recipes)
        active = (cline_dir / "personetta-active.md").read_text(encoding="utf-8")
        assert "## You Should" in active

    # --- Pairwise coexistence ---

    def test_cursor_and_claude_coexist(self, populated_project, tmp_path):
        target = tmp_path / "output"
        for fmt in ["cursor", "claude"]:
            install_all_for_format(populated_project, target, fmt)

        recipes = list_recipes(populated_project)
        cursor_cache = sorted(
            f.stem for f in (target / ".personetta" / "cursor-recipes").glob("*.md")
        )
        claude_cache = sorted(
            f.stem for f in (target / ".personetta" / "claude-recipes").glob("*.md")
        )
        assert cursor_cache == claude_cache == sorted(r["name"] for r in recipes)
        rules_md = {f.name for f in (target / ".cursor" / "rules").glob("*.md")}
        assert rules_md == {
            "personetta-active.md",
            "personetta-baseline.md",
            "personetta-router.md",
        }

    def test_cursor_and_copilot_coexist(self, populated_project, tmp_path):
        target = tmp_path / "output"
        for fmt in ["cursor", "copilot"]:
            install_all_for_format(populated_project, target, fmt)

        assert (target / ".cursor" / "rules").exists()
        assert (
            target / ".copilot" / "instructions" / "personetta-active.instructions.md"
        ).exists()
        cursor_files = list((target / ".cursor" / "rules").glob("*.md"))
        assert len(cursor_files) == 3

    def test_claude_and_copilot_coexist(self, populated_project, tmp_path):
        target = tmp_path / "output"
        for fmt in ["claude", "copilot"]:
            install_all_for_format(populated_project, target, fmt)

        assert (target / ".claude" / "rules").exists()
        assert (
            target / ".copilot" / "instructions" / "personetta-active.instructions.md"
        ).exists()
        claude_rules = list((target / ".claude" / "rules").glob("*.md"))
        assert len(claude_rules) == 3

    def test_cursor_and_cline_coexist(self, populated_project, tmp_path):
        target = tmp_path / "output"
        for fmt in ["cursor", "cline"]:
            install_all_for_format(populated_project, target, fmt)

        recipes = list_recipes(populated_project)
        cursor_cache = sorted(
            f.stem for f in (target / ".personetta" / "cursor-recipes").glob("*.md")
        )
        cline_cache = sorted(
            f.stem for f in (target / ".personetta" / "cline-recipes").glob("*.md")
        )
        assert cursor_cache == cline_cache == sorted(r["name"] for r in recipes)

    # --- All output formats simultaneously ---

    def test_all_formats_coexist(self, populated_project, tmp_path):
        target = tmp_path / "output"
        for fmt in FORMAT_NAMES:
            install_all_for_format(populated_project, target, fmt)

        recipes = list_recipes(populated_project)
        cursor_dir = target / ".cursor" / "rules"
        claude_rules = target / ".claude" / "rules"
        cline_dir = target / "Documents" / "Cline" / "Rules"
        copilot_inst = target / ".copilot" / "instructions"

        assert cursor_dir.exists()
        assert claude_rules.exists()
        assert cline_dir.exists()
        assert copilot_inst.exists()

        cursor_cache_names = sorted(
            f.stem for f in (target / ".personetta" / "cursor-recipes").glob("*.md")
        )
        claude_cache = sorted(
            f.stem for f in (target / ".personetta" / "claude-recipes").glob("*.md")
        )
        cline_cache = sorted(
            f.stem for f in (target / ".personetta" / "cline-recipes").glob("*.md")
        )
        recipe_names = sorted(r["name"] for r in recipes)

        assert cursor_cache_names == recipe_names
        assert claude_cache == recipe_names
        assert cline_cache == recipe_names
        assert {f.name for f in cursor_dir.glob("*.md")} == {
            "personetta-active.md",
            "personetta-baseline.md",
            "personetta-router.md",
        }

    def test_all_formats_have_distinct_markers(self, populated_project, tmp_path):
        target = tmp_path / "output"
        for fmt in FORMAT_NAMES:
            install_all_for_format(populated_project, target, fmt)

        cursor_content = (target / ".personetta" / "cursor-recipes").glob("*.md")
        cursor_content = next(
            iter(sorted(cursor_content, key=lambda p: p.name))
        ).read_text(encoding="utf-8")
        copilot_content = (
            target / ".copilot" / "instructions" / "personetta-active.instructions.md"
        ).read_text(encoding="utf-8")
        claude_content = (
            target / ".claude" / "rules" / "personetta-active.md"
        ).read_text(encoding="utf-8")
        cline_content = (
            target / "Documents" / "Cline" / "Rules" / "personetta-active.md"
        ).read_text(encoding="utf-8")

        assert cursor_content.startswith("---\n")
        assert "alwaysApply: false" in cursor_content
        assert "## Responsibilities" in cursor_content
        active = (target / ".cursor" / "rules" / "personetta-active.md").read_text(
            encoding="utf-8"
        )
        assert "alwaysApply: true" in active

        assert copilot_content.startswith("---")
        assert "applyTo:" in copilot_content
        assert "## You Should" in copilot_content

        assert not claude_content.startswith("---")
        assert "## You Should" in claude_content

        assert not cline_content.startswith("---")
        assert "## You Should" in cline_content

    # --- Format isolation ---

    def test_installing_cursor_does_not_create_claude_or_copilot(
        self, populated_project, tmp_path
    ):
        target = tmp_path / "output"
        install_all_for_format(populated_project, target, "cursor")

        assert (target / ".cursor" / "rules").exists()
        assert not (target / ".claude").exists()
        assert not (target / ".copilot").exists()

    def test_installing_claude_does_not_create_cursor_or_copilot(
        self, populated_project, tmp_path
    ):
        target = tmp_path / "output"
        install_all_for_format(populated_project, target, "claude")

        assert (target / ".claude" / "rules").exists()
        assert not (target / ".cursor").exists()
        assert not (target / ".copilot").exists()

    def test_installing_copilot_does_not_create_cursor_or_claude(
        self, populated_project, tmp_path
    ):
        target = tmp_path / "output"
        install_all_for_format(populated_project, target, "copilot")

        assert (target / ".copilot" / "instructions").exists()
        assert not (target / ".cursor").exists()
        assert not (target / ".claude").exists()
        assert not (target / "Documents" / "Cline" / "Rules").exists()

    def test_installing_cline_does_not_create_cursor_claude_or_copilot(
        self, populated_project, tmp_path
    ):
        target = tmp_path / "output"
        install_all_for_format(populated_project, target, "cline")

        assert (target / "Documents" / "Cline" / "Rules").exists()
        assert not (target / ".cursor").exists()
        assert not (target / ".claude").exists()
        assert not (target / ".copilot").exists()

    def test_reinstalling_one_format_does_not_alter_another(
        self, populated_project, tmp_path
    ):
        target = tmp_path / "output"
        install_all_for_format(populated_project, target, "cursor")
        install_all_for_format(populated_project, target, "claude")

        cursor_before = {}
        for f in (target / ".cursor" / "rules").glob("*.md"):
            cursor_before[f.name] = f.read_text(encoding="utf-8")

        install_all_for_format(populated_project, target, "claude")

        for f in (target / ".cursor" / "rules").glob("*.md"):
            assert (
                f.read_text(encoding="utf-8") == cursor_before[f.name]
            ), f"Reinstalling claude altered cursor file {f.name}"

    # --- Content consistency across formats ---

    def test_same_responsibilities_across_all_formats(self, populated_project, tmp_path):
        recipes = list_recipes(populated_project)
        merge_config = load_merge_config(populated_project)

        for recipe_info in recipes:
            recipe = load_recipe(recipe_info["name"], populated_project)
            compose_roles, mixin_roles = load_recipe_roles(recipe, populated_project)
            composed, _ = compose_recipe(recipe, compose_roles, mixin_roles, merge_config)

            cursor_out = format_role(composed, "cursor")
            copilot_out = format_role(composed, "copilot")
            claude_out = format_role(composed, "claude")
            cline_out = format_role(composed, "cline")

            for resp in composed.get("responsibilities", []):
                assert (
                    resp in cursor_out
                ), f"{recipe_info['name']}: cursor missing responsibility '{resp}'"
                assert (
                    resp in copilot_out
                ), f"{recipe_info['name']}: copilot missing responsibility '{resp}'"
                assert (
                    resp in claude_out
                ), f"{recipe_info['name']}: claude missing responsibility '{resp}'"
                assert (
                    resp in cline_out
                ), f"{recipe_info['name']}: cline missing responsibility '{resp}'"

    def test_same_boundaries_across_all_formats(self, populated_project, tmp_path):
        recipes = list_recipes(populated_project)
        merge_config = load_merge_config(populated_project)

        for recipe_info in recipes:
            recipe = load_recipe(recipe_info["name"], populated_project)
            compose_roles, mixin_roles = load_recipe_roles(recipe, populated_project)
            composed, _ = compose_recipe(recipe, compose_roles, mixin_roles, merge_config)

            cursor_out = format_role(composed, "cursor")
            copilot_out = format_role(composed, "copilot")
            claude_out = format_role(composed, "claude")
            cline_out = format_role(composed, "cline")

            for boundary in composed.get("non_responsibilities", []):
                assert (
                    boundary in cursor_out
                ), f"{recipe_info['name']}: cursor missing boundary '{boundary}'"
                assert (
                    boundary in copilot_out
                ), f"{recipe_info['name']}: copilot missing boundary '{boundary}'"
                assert (
                    boundary in claude_out
                ), f"{recipe_info['name']}: claude missing boundary '{boundary}'"
                assert (
                    boundary in cline_out
                ), f"{recipe_info['name']}: cline missing boundary '{boundary}'"

    def test_same_guidelines_across_all_formats(self, populated_project, tmp_path):
        recipes = list_recipes(populated_project)
        merge_config = load_merge_config(populated_project)

        for recipe_info in recipes:
            recipe = load_recipe(recipe_info["name"], populated_project)
            compose_roles, mixin_roles = load_recipe_roles(recipe, populated_project)
            composed, _ = compose_recipe(recipe, compose_roles, mixin_roles, merge_config)

            cursor_out = format_role(composed, "cursor")
            copilot_out = format_role(composed, "copilot")
            claude_out = format_role(composed, "claude")
            cline_out = format_role(composed, "cline")

            for guideline in composed.get("guidelines", []):
                assert (
                    guideline in cursor_out
                ), f"{recipe_info['name']}: cursor missing guideline '{guideline}'"
                assert (
                    guideline in copilot_out
                ), f"{recipe_info['name']}: copilot missing guideline '{guideline}'"
                assert (
                    guideline in claude_out
                ), f"{recipe_info['name']}: claude missing guideline '{guideline}'"
                assert (
                    guideline in cline_out
                ), f"{recipe_info['name']}: cline missing guideline '{guideline}'"

    def test_same_tool_names_across_all_formats(self, populated_project, tmp_path):
        recipes = list_recipes(populated_project)
        merge_config = load_merge_config(populated_project)

        for recipe_info in recipes:
            recipe = load_recipe(recipe_info["name"], populated_project)
            compose_roles, mixin_roles = load_recipe_roles(recipe, populated_project)
            composed, _ = compose_recipe(recipe, compose_roles, mixin_roles, merge_config)

            if not composed.get("tools"):
                continue

            cursor_out = format_role(composed, "cursor")
            copilot_out = format_role(composed, "copilot")
            claude_out = format_role(composed, "claude")
            cline_out = format_role(composed, "cline")

            for tool in composed["tools"]:
                assert (
                    tool["name"] in cursor_out
                ), f"{recipe_info['name']}: cursor missing tool '{tool['name']}'"
                assert (
                    tool["name"] in copilot_out
                ), f"{recipe_info['name']}: copilot missing tool '{tool['name']}'"
                assert (
                    tool["name"] in claude_out
                ), f"{recipe_info['name']}: claude missing tool '{tool['name']}'"
                assert (
                    tool["name"] in cline_out
                ), f"{recipe_info['name']}: cline missing tool '{tool['name']}'"

    # --- File count semantics per format ---

    def test_cursor_cache_one_markdown_per_recipe_and_three_rule_files(
        self, populated_project, tmp_path
    ):
        """Cache holds one composed file per recipe; .cursor/rules has exactly baseline, router, active."""
        add_recipe(
            populated_project,
            "extra-recipe",
            "Extra recipe.",
            ["base/lifecycle/test-developer"],
        )
        target = tmp_path / "output"
        install_all_for_format(populated_project, target, "cursor")

        recipes = list_recipes(populated_project)
        cache = list((target / ".personetta" / "cursor-recipes").glob("*.md"))
        rules = list((target / ".cursor" / "rules").glob("*.md"))
        assert len(cache) == len(recipes)
        assert len(rules) == 3

    def test_claude_cache_one_markdown_per_recipe_and_three_rule_files(
        self, populated_project, tmp_path
    ):
        add_recipe(
            populated_project,
            "extra-recipe",
            "Extra recipe.",
            ["base/lifecycle/test-developer"],
        )
        target = tmp_path / "output"
        install_all_for_format(populated_project, target, "claude")

        recipes = list_recipes(populated_project)
        cache = list((target / ".personetta" / "claude-recipes").glob("*.md"))
        rules = list((target / ".claude" / "rules").glob("*.md"))
        assert len(cache) == len(recipes)
        assert len(rules) == 3

    def test_cline_cache_one_markdown_per_recipe_and_three_rule_files(
        self, populated_project, tmp_path
    ):
        add_recipe(
            populated_project,
            "extra-recipe",
            "Extra recipe.",
            ["base/lifecycle/test-developer"],
        )
        target = tmp_path / "output"
        install_all_for_format(populated_project, target, "cline")

        recipes = list_recipes(populated_project)
        cache = list((target / ".personetta" / "cline-recipes").glob("*.md"))
        rules = list((target / "Documents" / "Cline" / "Rules").glob("*.md"))
        assert len(cache) == len(recipes)
        assert len(rules) == 3

    def test_copilot_cache_one_markdown_per_recipe_and_three_instruction_files(
        self, populated_project, tmp_path
    ):
        add_recipe(
            populated_project,
            "extra-recipe",
            "Extra recipe.",
            ["base/lifecycle/test-developer"],
        )
        target = tmp_path / "output"
        install_all_for_format(populated_project, target, "copilot")

        recipes = list_recipes(populated_project)
        cache = list((target / ".personetta" / "copilot-recipes").glob("*.md"))
        inst = list((target / ".copilot" / "instructions").glob("*.instructions.md"))
        assert len(cache) == len(recipes)
        assert len(inst) == 3

    def test_copilot_default_active_is_lexicographically_first_recipe(
        self, populated_project, tmp_path
    ):
        add_recipe(
            populated_project,
            "zzz-last-recipe",
            "Should not be default unless first alphabetically.",
            ["base/lifecycle/test-developer"],
        )
        target = tmp_path / "output"
        install_all_for_format(populated_project, target, "copilot")

        content = (
            target / ".copilot" / "instructions" / "personetta-active.instructions.md"
        ).read_text(encoding="utf-8")
        assert "Zzz Last Recipe" not in content

    # --- Frontmatter: Cursor rules + Copilot instructions use YAML ---

    def test_cursor_and_copilot_use_yaml_frontmatter_where_required(
        self, populated_project, tmp_path
    ):
        target = tmp_path / "output"
        for fmt in FORMAT_NAMES:
            install_all_for_format(populated_project, target, fmt)

        for f in (target / ".cursor" / "rules").glob("*.md"):
            assert f.read_text(encoding="utf-8").startswith(
                "---\n"
            ), f"Cursor file {f.name} missing frontmatter"

        copilot_active = (
            target / ".copilot" / "instructions" / "personetta-active.instructions.md"
        ).read_text(encoding="utf-8")
        assert copilot_active.startswith("---")
        assert "applyTo:" in copilot_active

        for f in (target / ".claude" / "rules").glob("*.md"):
            assert not f.read_text(encoding="utf-8").startswith(
                "---"
            ), f"Claude rules file {f.name} should not use YAML frontmatter"

        for f in (target / "Documents" / "Cline" / "Rules").glob("*.md"):
            assert not f.read_text(encoding="utf-8").startswith(
                "---"
            ), f"Cline rules file {f.name} should not use YAML frontmatter"

    # --- Real data multi-format ---

    def test_all_real_recipes_install_all_formats(self, real_project, tmp_path):
        target = tmp_path / "real_multi"
        for fmt in FORMAT_NAMES:
            install_all_for_format(real_project, target, fmt)

        recipes = list_recipes(real_project)
        recipe_names = sorted(r["name"] for r in recipes)

        cursor_cache = sorted(
            f.stem for f in (target / ".personetta" / "cursor-recipes").glob("*.md")
        )
        claude_cache = sorted(
            f.stem for f in (target / ".personetta" / "claude-recipes").glob("*.md")
        )
        cline_cache = sorted(
            f.stem for f in (target / ".personetta" / "cline-recipes").glob("*.md")
        )

        assert cursor_cache == recipe_names
        assert claude_cache == recipe_names
        assert cline_cache == recipe_names
        assert {f.name for f in (target / ".cursor" / "rules").glob("*.md")} == {
            "personetta-active.md",
            "personetta-baseline.md",
            "personetta-router.md",
        }
        assert (
            target / ".copilot" / "instructions" / "personetta-active.instructions.md"
        ).exists()

    def test_real_data_content_consistency_across_formats(self, real_project, tmp_path):
        recipes = list_recipes(real_project)
        merge_config = load_merge_config(real_project)

        for recipe_info in recipes:
            recipe = load_recipe(recipe_info["name"], real_project)
            compose_roles, mixin_roles = load_recipe_roles(recipe, real_project)
            composed, _ = compose_recipe(recipe, compose_roles, mixin_roles, merge_config)

            outputs = {fmt: format_role(composed, fmt) for fmt in FORMAT_NAMES}

            for resp in composed.get("responsibilities", []):
                for fmt, out in outputs.items():
                    assert (
                        resp in out
                    ), f"Real recipe '{recipe_info['name']}': {fmt} missing '{resp}'"

    def test_each_layout_uses_correct_format_name(self, populated_project, tmp_path):
        """Regression test: Ensure each layout calls format_role() with its own format name.

        This prevents copy-paste errors where a layout calls format_role(composed, "copilot")
        when it should use its own format name like "claude" or "cline".
        """
        from unittest.mock import patch
        from generator import claude_layout, cline_layout, copilot_layout, cursor_layout

        # Test claude_layout uses "claude"
        with patch("generator.layout_base.format_role") as mock:
            mock.return_value = "# Test Output"
            try:
                claude_layout.install_all_claude(populated_project, tmp_path / "claude")
            except Exception:
                pass  # We don't care about completion, just format_role calls

            # Ensure all calls used "claude" not "copilot"
            if mock.call_count > 0:
                for call_args in mock.call_args_list:
                    format_arg = call_args[0][1]  # Second positional arg
                    assert (
                        format_arg == "claude"
                    ), f"claude_layout called format_role with '{format_arg}' instead of 'claude'"

        # Test cline_layout uses "cline"
        with patch("generator.layout_base.format_role") as mock:
            mock.return_value = "# Test Output"
            try:
                cline_layout.install_all_cline(populated_project, tmp_path / "cline")
            except Exception:
                pass

            if mock.call_count > 0:
                for call_args in mock.call_args_list:
                    format_arg = call_args[0][1]
                    assert (
                        format_arg == "cline"
                    ), f"cline_layout called format_role with '{format_arg}' instead of 'cline'"

        # Test copilot_layout uses "copilot"
        with patch("generator.layout_base.format_role") as mock:
            mock.return_value = "# Test Output"
            try:
                copilot_layout.install_all_copilot(
                    populated_project, tmp_path / "copilot"
                )
            except Exception:
                pass

            if mock.call_count > 0:
                for call_args in mock.call_args_list:
                    format_arg = call_args[0][1]
                    assert (
                        format_arg == "copilot"
                    ), f"copilot_layout called format_role with '{format_arg}' instead of 'copilot'"

        # Test cursor_layout uses "cursor"
        with patch("generator.layout_base.format_role") as mock:
            mock.return_value = "# Test Output"
            try:
                cursor_layout.install_all_cursor(populated_project, tmp_path / "cursor")
            except Exception:
                pass

            if mock.call_count > 0:
                for call_args in mock.call_args_list:
                    format_arg = call_args[0][1]
                    assert (
                        format_arg == "cursor"
                    ), f"cursor_layout called format_role with '{format_arg}' instead of 'cursor'"

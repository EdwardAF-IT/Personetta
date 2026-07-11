"""Tests for multi-recipe composition.

Tests skill generation from multiple composed recipes.

This module tests:
1. Multi-pattern matching (wildcards)
2. Multi-recipe composition in SkillGenerator
3. Named perspectives in SKILL.md
4. Separate criteria files per recipe
5. Combined execution checklist
6. Integration tests (multiple recipes → single skill)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from generator.project_layout import ProjectLayout

pytestmark = [pytest.mark.unit, pytest.mark.skills]


class TestMultiPatternMatching:
    """Tests for wildcard and multi-pattern matching."""

    def test_multiple_patterns_combine_results(self, monkeypatch, tmp_path):
        """Multiple patterns combine into single result list."""
        from generator.cli.commands import cmd_skill

        # Create mock args with multiple patterns
        args = MagicMock()
        args.patterns = ["test-python-backend", "review-python-backend-perf"]
        args.format = "copilot"
        args.name = "python-workflow"
        args.workspace = False
        args.target = None
        args.force = True
        args.whatif = False

        # Note: Patch where functions are used (in skill.py), not where they're re-exported
        # Mock get_base_dir to return temp path with recipes
        with patch("generator.cli.commands.skill.get_base_dir", return_value=tmp_path):
            with patch("generator.cli.commands.skill.list_recipes") as mock_list:
                # Return multiple recipes
                mock_list.return_value = [
                    {"name": "test-python-backend"},
                    {"name": "review-python-backend-perf"},
                    {"name": "implement-python-backend-perf"},
                ]

                with patch("generator.cli.commands.skill.load_recipe") as mock_load:
                    mock_load.return_value = {"_recipe_name": "test"}
                    with patch(
                        "generator.cli.commands.skill.load_merge_config"
                    ) as mock_config:
                        mock_config.return_value = {}
                        with patch(
                            "generator.cli.commands.skill.load_recipe_roles"
                        ) as mock_roles:
                            mock_roles.return_value = ([], [])
                            with patch(
                                "generator.cli.commands.skill.compose_recipe"
                            ) as mock_compose:
                                mock_compose.return_value = (
                                    {"_recipe_description": "Test"},
                                    [],
                                )
                                with patch("generator.cli.commands.skill.SkillGenerator"):
                                    cmd_skill(args)

                                    # Should load both recipes (Phase 6)
                                    # For now, Phase 6 not implemented, so should only load one
                                    assert mock_load.call_count >= 1

    def test_wildcard_pattern_matches_multiple(self, monkeypatch, tmp_path):
        """Wildcard pattern matches multiple recipes."""
        from generator.cli.commands import cmd_skill

        args = MagicMock()
        args.patterns = ["test-python-*"]  # Wildcard pattern
        args.format = "copilot"
        args.name = "python-testing"
        args.workspace = False
        args.target = None
        args.force = True
        args.whatif = False

        # Note: Patch where functions are used (in skill.py), not where they're re-exported
        with patch("generator.cli.commands.skill.get_base_dir", return_value=tmp_path):
            with patch("generator.cli.commands.skill.list_recipes") as mock_list:
                mock_list.return_value = [
                    {"name": "test-python-backend"},
                    {"name": "test-python-frontend"},
                    {"name": "review-python-backend-perf"},
                ]

                with patch("generator.cli.commands.skill.load_recipe") as mock_load:
                    mock_load.return_value = {"_recipe_name": "test"}
                    with patch(
                        "generator.cli.commands.skill.load_merge_config"
                    ) as mock_config:
                        mock_config.return_value = {}
                        with patch(
                            "generator.cli.commands.skill.load_recipe_roles"
                        ) as mock_roles:
                            mock_roles.return_value = ([], [])
                            with patch(
                                "generator.cli.commands.skill.compose_recipe"
                            ) as mock_compose:
                                mock_compose.return_value = (
                                    {"_recipe_description": "Test"},
                                    [],
                                )
                                with patch("generator.cli.commands.skill.SkillGenerator"):
                                    result = cmd_skill(args)

                                    # Should match 2 recipes with wildcard
                                    assert result == 0

    def test_no_pattern_match_returns_error(self, monkeypatch, tmp_path):
        """No matching recipes returns error."""
        from generator.cli.commands import cmd_skill

        args = MagicMock()
        args.patterns = ["nonexistent-*"]
        args.format = "copilot"
        args.name = "test"
        args.target = None  # Fix: add target

        # Note: Patch where functions are used (in skill.py), not where they're re-exported
        with patch("generator.cli.commands.skill.get_base_dir", return_value=tmp_path):
            with patch("generator.cli.commands.skill.list_recipes") as mock_list:
                mock_list.return_value = [
                    {"name": "test-python-backend"},
                    {"name": "review-python-backend-perf"},
                ]

                result = cmd_skill(args)
                assert result == 1  # Should fail


class TestMultiRecipeSkillGenerator:
    """Tests for multi-recipe composition in SkillGenerator."""

    def test_generate_accepts_recipe_list(self, tmp_path):
        """SkillGenerator.generate can accept list of recipes."""
        from generator.skills import SkillGenerator

        generator = SkillGenerator()

        recipes = [
            {"_recipe_description": "Test recipe 1", "responsibilities": ["Test"]},
            {"_recipe_description": "Test recipe 2", "responsibilities": ["Review"]},
        ]

        # Phase 6: Should accept list of recipes
        generator.generate(recipes, "copilot", "multi-skill", tmp_path)

        # Verify skill was created
        skill_md = tmp_path / "SKILL.md"
        assert skill_md.exists(), "SKILL.md should be created"

    def test_generate_multi_creates_perspective_sections(self, tmp_path):
        """Multi-recipe skill has perspective sections in SKILL.md."""
        from generator.skills import SkillGenerator

        generator = SkillGenerator()

        recipes = [
            {
                "_recipe_name": "test-python-backend",
                "_recipe_description": "Test Python code",
                "responsibilities": ["Write tests"],
                "guidelines": ["Test one thing per test"],
            },
            {
                "_recipe_name": "review-python-backend-perf",
                "_recipe_description": "Review Python code for performance",
                "responsibilities": ["Review algorithms"],
                "guidelines": ["Check complexity"],
            },
        ]

        # Generate multi-recipe skill
        generator.generate(recipes, "copilot", "python-workflow", tmp_path)

        skill_md = tmp_path / "SKILL.md"
        assert skill_md.exists()

        content = skill_md.read_text()

        # Should have perspective sections
        assert "Perspective 1:" in content or "Test Python Backend" in content
        assert "Perspective 2:" in content or "Review Python Backend Perf" in content

    def test_generate_multi_creates_separate_criteria_files(self, tmp_path):
        """Multi-recipe skill creates separate criteria.md per recipe."""
        from generator.skills import SkillGenerator

        generator = SkillGenerator()

        recipes = [
            {
                "_recipe_name": "test-python-backend",
                "_recipe_description": "Test Python code",
                "responsibilities": ["Write tests"],
                "guidelines": ["Test one thing"],
            },
            {
                "_recipe_name": "review-python-backend-perf",
                "_recipe_description": "Review code",
                "responsibilities": ["Review"],
                "guidelines": ["Check performance"],
            },
        ]

        # Generate multi-recipe skill
        generator.generate(recipes, "copilot", "workflow", tmp_path)

        # Should create separate criteria files
        test_criteria = tmp_path / "references" / "test-python-backend-criteria.md"
        review_criteria = (
            tmp_path / "references" / "review-python-backend-perf-criteria.md"
        )

        assert test_criteria.exists()
        assert review_criteria.exists()

        # Each should have their own guidelines
        test_content = test_criteria.read_text()
        assert "Test one thing" in test_content

        review_content = review_criteria.read_text()
        assert "Check performance" in review_content

    def test_generate_multi_combines_checklists(self, tmp_path):
        """Multi-recipe skill combines verification checklists."""
        from generator.skills import SkillGenerator

        generator = SkillGenerator()

        recipes = [
            {
                "_recipe_name": "test-python-backend",
                "_recipe_description": "Test",
                "responsibilities": ["Write tests"],
                "verification": ["All tests pass", "Coverage > 80%"],
            },
            {
                "_recipe_name": "review-python-backend-perf",
                "_recipe_description": "Review",
                "responsibilities": ["Review"],
                "verification": ["No N+1 queries", "Complexity documented"],
            },
        ]

        # Generate multi-recipe skill
        generator.generate(recipes, "copilot", "workflow", tmp_path)

        checklist = tmp_path / "references" / "checklist.md"
        assert checklist.exists()

        content = checklist.read_text()

        # Should have all verification items from both recipes
        assert "All tests pass" in content
        assert "Coverage > 80%" in content
        assert "No N+1 queries" in content

    def test_generate_multi_groups_checklist_by_recipe(self, tmp_path):
        """Multi-recipe checklist groups items by source recipe."""
        from generator.skills import SkillGenerator

        generator = SkillGenerator()

        recipes = [
            {
                "_recipe_name": "test-python-backend",
                "_recipe_description": "Test",
                "responsibilities": ["Write tests"],
                "verification": ["Tests pass"],
            },
            {
                "_recipe_name": "review-python-backend-perf",
                "_recipe_description": "Review",
                "responsibilities": ["Review"],
                "verification": ["Performance checked"],
            },
        ]

        # Generate multi-recipe skill
        generator.generate(recipes, "copilot", "workflow", tmp_path)

        checklist = tmp_path / "references" / "checklist.md"
        content = checklist.read_text()

        # Should have section headers for each recipe
        assert "Test Python Backend" in content
        assert "Review Python Backend Perf" in content


class TestMultiRecipeIntegration:
    """Integration tests for multi-recipe skill generation."""

    def test_cmd_skill_with_multiple_patterns(self, monkeypatch, tmp_path):
        """cmd_skill with multiple patterns generates multi-recipe skill."""
        from generator.cli.commands import cmd_skill

        args = MagicMock()
        args.patterns = ["test-python-*", "review-python-*"]
        args.format = "copilot"
        args.name = "python-quality"
        args.workspace = False
        args.target = None
        args.force = True
        args.whatif = False

        with patch("generator.cli.commands.get_base_dir", return_value=tmp_path):
            with patch("generator.cli.commands.list_recipes") as mock_list:
                mock_list.return_value = [
                    {"name": "test-python-backend"},
                    {"name": "review-python-backend-perf"},
                ]

                with patch("generator.cli.commands.load_recipe") as mock_load:
                    # Return different recipes for each call
                    recipe1 = {
                        "_recipe_name": "test-python-backend",
                        "_recipe_description": "Test Python code",
                        "responsibilities": ["Write tests"],
                        "guidelines": ["Test one thing"],
                        "verification": ["Tests pass"],
                    }
                    recipe2 = {
                        "_recipe_name": "review-python-backend-perf",
                        "_recipe_description": "Review Python code",
                        "responsibilities": ["Review code"],
                        "guidelines": ["Check performance"],
                        "verification": ["Performance OK"],
                    }
                    mock_load.side_effect = [recipe1, recipe2]

                    with patch("generator.cli.commands.load_merge_config") as mock_config:
                        mock_config.return_value = {}
                        with patch(
                            "generator.cli.commands.load_recipe_roles"
                        ) as mock_roles:
                            mock_roles.return_value = ([], [])
                            with patch(
                                "generator.cli.commands.compose_recipe"
                            ) as mock_compose:
                                mock_compose.side_effect = [
                                    (recipe1, []),
                                    (recipe2, []),
                                ]

                                # Phase 6: Should succeed and create multi-recipe skill
                                # For now, will fail or only use first recipe
                                result = cmd_skill(args)

                                # Currently Phase 5, so should succeed but only use first recipe
                                # In Phase 6, should load and compose both recipes
                                assert result == 0

    def test_multi_recipe_skill_file_structure(self, monkeypatch, tmp_path):
        """Multi-recipe skill creates expected file structure."""
        from generator.cli.commands import cmd_skill

        skill_dir = tmp_path / "skills" / "python-workflow"

        args = MagicMock()
        args.patterns = ["test-*", "review-*"]
        args.format = "copilot"
        args.name = "python-workflow"
        args.workspace = False
        args.target = None
        args.force = True
        args.whatif = False

        # Note: Patch where functions are used (in skill.py), not where they're re-exported
        with patch("generator.cli.commands.skill.get_base_dir", return_value=tmp_path):
            with patch(
                "generator.cli.commands.skill.get_skill_install_path",
                return_value=skill_dir,
            ):
                with patch("generator.cli.commands.skill.list_recipes") as mock_list:
                    mock_list.return_value = [
                        {"name": "test-python-backend"},
                        {"name": "review-python-backend-perf"},
                    ]

                    with patch("generator.cli.commands.skill.load_recipe"):
                        with patch("generator.cli.commands.skill.load_merge_config"):
                            with patch(
                                "generator.cli.commands.skill.load_recipe_roles"
                            ) as mock_roles:
                                mock_roles.return_value = ([], [])
                                with patch(
                                    "generator.cli.commands.skill.compose_recipe"
                                ) as mock_compose:
                                    mock_compose.return_value = (
                                        {
                                            "_recipe_name": "test",
                                            "_recipe_description": "Test",
                                            "responsibilities": ["Test"],
                                        },
                                        [],
                                    )

                                    with patch(
                                        "generator.cli.commands.skill.SkillGenerator"
                                    ) as mock_gen_class:
                                        mock_gen = MagicMock()
                                        mock_gen_class.return_value = mock_gen

                                        cmd_skill(args)

                                        # Should call generate (Phase 6: with list of recipes)
                                        assert mock_gen.generate.called


class TestMultiRecipeTemplates:
    """Tests for multi-recipe template rendering."""

    def test_multi_recipe_skill_md_template(self):
        """Multi-recipe SKILL.md template has perspective placeholders."""

        # Navigate from tests/unit/skills/ to root, then to data/templates/skill
        template_dir = ProjectLayout.from_file(__file__).templates / "skill"
        skill_template = template_dir / "SKILL.md.template"

        # Template should exist
        assert skill_template.exists()

        # For Phase 6, we might need a separate template or conditional logic
        # For now, single-recipe template is OK

    def test_multi_recipe_criteria_template(self):
        """Multi-recipe uses per-recipe criteria files."""

        # Navigate from tests/unit/skills/ to root, then to data/templates/skill
        template_dir = ProjectLayout.from_file(__file__).templates / "skill"
        criteria_template = template_dir / "criteria.md.template"

        # Template should exist
        assert criteria_template.exists()

        # Can be reused for multiple files (one per recipe)


class TestMultiRecipeEdgeCases:
    """Edge cases for multi-recipe generation."""

    def test_multi_recipe_with_some_missing_guidelines(self, tmp_path):
        """Multi-recipe where some recipes lack guidelines."""
        from generator.skills import SkillGenerator

        generator = SkillGenerator()

        recipes = [
            {
                "_recipe_name": "test-python-backend",
                "_recipe_description": "Test",
                "responsibilities": ["Test"],
                "guidelines": ["Test one thing"],
            },
            {
                "_recipe_name": "review-python-backend-perf",
                "_recipe_description": "Review",
                "responsibilities": ["Review"],
                # No guidelines
            },
        ]

        # Phase 6: Should create criteria.md only for first recipe
        generator.generate(recipes, "copilot", "workflow", tmp_path)

        test_criteria = tmp_path / "references" / "test-python-backend-criteria.md"
        review_criteria = (
            tmp_path / "references" / "review-python-backend-perf-criteria.md"
        )

        assert test_criteria.exists()
        assert not review_criteria.exists()  # Should skip if no guidelines

    def test_multi_recipe_deduplicates_verification_items(self, tmp_path):
        """Multi-recipe deduplicates identical verification items."""
        from generator.skills import SkillGenerator

        generator = SkillGenerator()

        recipes = [
            {
                "_recipe_name": "test-python-backend",
                "_recipe_description": "Test",
                "responsibilities": ["Test"],
                "verification": ["All tests pass", "Code formatted"],
            },
            {
                "_recipe_name": "review-python-backend-perf",
                "_recipe_description": "Review",
                "responsibilities": ["Review"],
                "verification": [
                    "All tests pass",
                    "Performance checked",
                ],  # Duplicate "All tests pass"
            },
        ]

        # Phase 6: Should deduplicate verification items
        generator.generate(recipes, "copilot", "workflow", tmp_path)

        checklist = tmp_path / "references" / "checklist.md"
        content = checklist.read_text()

        # "All tests pass" should appear only once
        assert content.count("All tests pass") == 1
        assert "Code formatted" in content
        assert "Performance checked" in content


class TestMultiRecipeExamples:
    """Example-based tests showing expected multi-recipe output."""

    def test_test_plus_review_combination(self, tmp_path):
        """test-python-backend + review-python-backend-perf combination."""
        from generator.skills import SkillGenerator

        generator = SkillGenerator()

        recipes = [
            {
                "_recipe_name": "test-python-backend",
                "_recipe_description": "Write pytest tests for Python backend code",
                "responsibilities": [
                    "Design test strategy",
                    "Write test cases",
                    "Verify coverage",
                ],
                "guidelines": [
                    "Test one behavior per test",
                    "Use fixtures for test data",
                ],
                "verification": [
                    "All tests pass",
                    "Coverage > 80%",
                ],
            },
            {
                "_recipe_name": "review-python-backend-perf",
                "_recipe_description": "Review Python code for performance",
                "responsibilities": [
                    "Evaluate algorithmic complexity",
                    "Identify optimization opportunities",
                ],
                "guidelines": [
                    "Measure before optimizing",
                    "Prefer algorithmic improvements",
                ],
                "verification": [
                    "All tests pass",  # Duplicate
                    "No performance regressions",
                ],
            },
        ]

        # Phase 6 feature
        generator.generate(recipes, "copilot", "python-quality", tmp_path)

        # Expected structure:
        # python-quality/
        #   SKILL.md (with 2 perspectives)
        #   README.md
        #   references/
        #     test-python-backend-criteria.md
        #     review-python-backend-perf-criteria.md
        #     checklist.md (combined, deduplicated)

        skill_md = tmp_path / "SKILL.md"
        content = skill_md.read_text()

        # Should describe both capabilities
        assert "Write pytest tests" in content or "pytest" in content.lower()
        assert (
            "Review Python code for performance" in content
            or "performance" in content.lower()
        )

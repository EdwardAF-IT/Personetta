from __future__ import annotations

import pytest

from generator.merge.strategies import (
    merge_union,
    merge_union_dedup,
    merge_union_by_key,
    merge_append,
    merge_priority,
    merge_deep,
    deep_merge_dict,
    merge_roles,
)
from generator.merge.conflict_detection import detect_conflicts
from generator.merge.model_requirements import aggregate_model_requirements
from generator.merger import (
    merge_mixins,
    apply_overrides,
    compose_recipe,
)

pytestmark = [pytest.mark.unit, pytest.mark.core, pytest.mark.readonly]


class TestMergeUnion:
    def test_combines_unique_items(self):
        roles = [
            {"items": ["a", "b"]},
            {"items": ["c", "d"]},
        ]
        assert merge_union(roles, "items") == ["a", "b", "c", "d"]

    def test_deduplicates_exact_matches(self):
        roles = [
            {"items": ["a", "b", "c"]},
            {"items": ["b", "c", "d"]},
        ]
        assert merge_union(roles, "items") == ["a", "b", "c", "d"]

    def test_preserves_first_occurrence_order(self):
        roles = [
            {"items": ["c", "a"]},
            {"items": ["b", "a"]},
        ]
        assert merge_union(roles, "items") == ["c", "a", "b"]

    def test_handles_missing_field(self):
        roles = [
            {"items": ["a"]},
            {"other": "value"},
            {"items": ["b"]},
        ]
        assert merge_union(roles, "items") == ["a", "b"]

    def test_empty_roles(self):
        assert merge_union([], "items") == []


class TestMergeUnionDedup:
    def test_same_as_union_for_exact_matches(self):
        roles = [
            {"g": ["guideline A", "guideline B"]},
            {"g": ["guideline B", "guideline C"]},
        ]
        assert merge_union_dedup(roles, "g") == [
            "guideline A",
            "guideline B",
            "guideline C",
        ]


class TestMergeUnionByKey:
    def test_deduplicates_by_key(self):
        roles = [
            {"tools": [{"name": "pytest", "purpose": "Testing"}]},
            {"tools": [{"name": "black", "purpose": "Formatting"}]},
        ]
        result = merge_union_by_key(roles, "tools", "name")
        assert len(result) == 2
        assert result[0]["name"] == "pytest"
        assert result[1]["name"] == "black"

    def test_first_wins_on_key_collision(self):
        roles = [
            {"tools": [{"name": "pytest", "purpose": "Unit testing"}]},
            {"tools": [{"name": "pytest", "purpose": "Integration testing"}]},
        ]
        result = merge_union_by_key(roles, "tools", "name")
        assert len(result) == 1
        assert result[0]["purpose"] == "Unit testing"

    def test_handles_missing_field(self):
        roles = [
            {"tools": [{"name": "pytest", "purpose": "Testing"}]},
            {"other": "value"},
        ]
        result = merge_union_by_key(roles, "tools", "name")
        assert len(result) == 1


class TestMergeAppend:
    def test_keeps_all_including_duplicates(self):
        roles = [
            {"examples": [{"scenario": "A"}]},
            {"examples": [{"scenario": "A"}, {"scenario": "B"}]},
        ]
        result = merge_append(roles, "examples")
        assert len(result) == 3

    def test_handles_missing_field(self):
        roles = [
            {"examples": [{"scenario": "A"}]},
            {"other": "value"},
        ]
        result = merge_append(roles, "examples")
        assert len(result) == 1


class TestMergePriority:
    def test_first_non_none_wins(self):
        roles = [
            {"tone": "analytical"},
            {"tone": "friendly"},
        ]
        assert merge_priority(roles, "tone") == "analytical"

    def test_skips_missing_fields(self):
        roles = [
            {"other": "value"},
            {"tone": "friendly"},
        ]
        assert merge_priority(roles, "tone") == "friendly"

    def test_returns_none_when_all_missing(self):
        roles = [
            {"other": "a"},
            {"other": "b"},
        ]
        assert merge_priority(roles, "tone") is None

    def test_skips_none_values(self):
        roles = [
            {"tone": None},
            {"tone": "pragmatic"},
        ]
        assert merge_priority(roles, "tone") == "pragmatic"


class TestDeepMerge:
    def test_merges_flat_dicts(self):
        result = deep_merge_dict({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_later_values_override(self):
        result = deep_merge_dict({"a": 1}, {"a": 2})
        assert result == {"a": 2}

    def test_recursive_merge(self):
        base = {"nested": {"a": 1, "b": 2}}
        overlay = {"nested": {"b": 3, "c": 4}}
        result = deep_merge_dict(base, overlay)
        assert result == {"nested": {"a": 1, "b": 3, "c": 4}}

    def test_does_not_mutate_original(self):
        base = {"a": 1}
        overlay = {"b": 2}
        result = deep_merge_dict(base, overlay)
        assert "b" not in base
        assert result == {"a": 1, "b": 2}

    def test_merge_deep_across_roles(self):
        roles = [
            {"context": {"framework": "django", "version": "4.2"}},
            {"context": {"database": "postgres", "version": "16"}},
        ]
        result = merge_deep(roles, "context")
        assert result == {
            "framework": "django",
            "database": "postgres",
            "version": "16",
        }


class TestMergeRoles:
    def test_merges_all_field_types(
        self,
        sample_lifecycle_role,
        sample_layer_role,
        sample_language_role,
    ):
        roles = [sample_lifecycle_role, sample_layer_role, sample_language_role]
        result = merge_roles(roles)

        assert "Write clean code" in result["responsibilities"]
        assert "Design API contracts" in result["responsibilities"]
        assert "Write idiomatic Python" in result["responsibilities"]

        assert result["tone"] == "pragmatic-and-clean"

        assert len(result["tools"]) == 2

        combined_tags = result["tags"]
        assert "development" in combined_tags
        assert "backend" in combined_tags
        assert "python" in combined_tags

    def test_deduplicates_shared_guidelines(
        self,
        sample_layer_role,
        sample_mixin_role,
    ):
        result = merge_roles([sample_layer_role, sample_mixin_role])
        never_trust = [g for g in result["guidelines"] if g == "Never trust client input"]
        assert len(never_trust) == 1


class TestMergeMixins:
    def test_mixins_do_not_override_tone(
        self,
        sample_lifecycle_role,
        sample_mixin_role,
    ):
        composed = merge_roles([sample_lifecycle_role])
        sample_mixin_role["tone"] = "aggressive"
        result = merge_mixins(composed, [sample_mixin_role])
        assert result["tone"] == "pragmatic-and-clean"

    def test_mixins_add_responsibilities(
        self,
        sample_lifecycle_role,
        sample_mixin_role,
    ):
        composed = merge_roles([sample_lifecycle_role])
        result = merge_mixins(composed, [sample_mixin_role])
        assert "Identify injection risks" in result["responsibilities"]
        assert "Write clean code" in result["responsibilities"]

    def test_mixins_do_not_override_output_format(
        self,
        sample_lifecycle_role,
        sample_mixin_role,
    ):
        composed = merge_roles([sample_lifecycle_role])
        sample_mixin_role["output_format"] = "mixin-format"
        result = merge_mixins(composed, [sample_mixin_role])
        assert result["output_format"] == "code-with-explanation"


class TestApplyOverrides:
    def test_overrides_existing_field(self):
        composed = {"tone": "analytical", "responsibilities": ["a"]}
        result = apply_overrides(composed, {"tone": "concise"})
        assert result["tone"] == "concise"
        assert result["responsibilities"] == ["a"]

    def test_adds_new_field(self):
        composed = {"tone": "analytical"}
        result = apply_overrides(composed, {"custom_field": "custom_value"})
        assert result["custom_field"] == "custom_value"

    def test_does_not_mutate_original(self):
        composed = {"tone": "analytical"}
        result = apply_overrides(composed, {"tone": "concise"})
        assert composed["tone"] == "analytical"
        assert result["tone"] == "concise"


class TestDetectConflicts:
    def test_detects_responsibility_contradiction(self):
        composed = {
            "responsibilities": ["Write tests", "Write clean code"],
            "non_responsibilities": ["Write tests"],
        }
        warnings = detect_conflicts(composed)
        assert len(warnings) == 1
        assert warnings[0].severity == "error"
        assert "Write tests" in warnings[0].message

    def test_no_contradiction_passes(self):
        composed = {
            "responsibilities": ["Write code"],
            "non_responsibilities": ["Write tests"],
        }
        warnings = detect_conflicts(composed)
        assert len(warnings) == 0

    def test_detects_mutually_exclusive_tools(self):
        composed = {
            "tools": [
                {"name": "pylint", "purpose": "Linting"},
                {"name": "ruff", "purpose": "Fast linting"},
            ],
        }
        warnings = detect_conflicts(composed)
        assert len(warnings) == 1
        assert warnings[0].severity == "error"
        assert "pylint" in warnings[0].message or "ruff" in warnings[0].message

    def test_non_conflicting_tools_pass(self):
        composed = {
            "tools": [
                {"name": "pytest", "purpose": "Testing"},
                {"name": "black", "purpose": "Formatting"},
            ],
        }
        warnings = detect_conflicts(composed)
        assert len(warnings) == 0

    def test_uses_merge_config_for_known_conflicts(self):
        composed = {
            "tools": [
                {"name": "toolA", "purpose": "A"},
                {"name": "toolB", "purpose": "B"},
            ],
        }
        config = {
            "conflict_detection": [
                {
                    "type": "mutually-exclusive-tools",
                    "known_conflicts": [["toolA", "toolB"]],
                },
            ],
        }
        warnings = detect_conflicts(composed, config)
        assert len(warnings) == 1

    def test_empty_composed_no_errors(self):
        warnings = detect_conflicts({})
        assert len(warnings) == 0


class TestComposeRecipe:
    def test_full_composition(
        self,
        sample_lifecycle_role,
        sample_layer_role,
        sample_language_role,
        sample_mixin_role,
    ):
        recipe = {
            "name": "full-test",
            "description": "Full composition test.",
            "compose": ["a", "b", "c"],
            "mixins": ["d"],
        }
        composed, warnings = compose_recipe(
            recipe,
            [sample_lifecycle_role, sample_layer_role, sample_language_role],
            [sample_mixin_role],
        )
        assert composed["_recipe_name"] == "full-test"
        assert "Write clean code" in composed["responsibilities"]
        assert "Identify injection risks" in composed["responsibilities"]
        assert composed["tone"] == "pragmatic-and-clean"
        assert len(warnings) == 0

    def test_composition_with_overrides(
        self,
        sample_lifecycle_role,
    ):
        recipe = {
            "name": "override-test",
            "compose": ["a"],
            "overrides": {"tone": "concise"},
        }
        composed, _ = compose_recipe(recipe, [sample_lifecycle_role], [])
        assert composed["tone"] == "concise"

    def test_records_source_roles(
        self,
        sample_lifecycle_role,
        sample_mixin_role,
    ):
        recipe = {"name": "source-test", "compose": ["a"], "mixins": ["b"]}
        composed, _ = compose_recipe(recipe, [sample_lifecycle_role], [sample_mixin_role])
        assert "test-developer" in composed["_source_roles"]
        assert "test-security" in composed["_source_roles"]

    def test_includes_model_recommendation(
        self,
        sample_lifecycle_role,
    ):
        recipe = {"name": "rec-test", "compose": ["a"]}
        composed, _ = compose_recipe(recipe, [sample_lifecycle_role], [])
        assert "_model_recommendation" in composed
        assert "min_tier" in composed["_model_recommendation"]
        assert "reasoning" in composed["_model_recommendation"]

    def test_recipe_model_override(
        self,
        sample_lifecycle_role,
    ):
        recipe = {
            "name": "override-rec-test",
            "compose": ["a"],
            "model_recommendation": {
                "min_tier": "advanced",
                "reasoning": "extended",
                "rationale": "Complex architecture work",
            },
        }
        composed, _ = compose_recipe(recipe, [sample_lifecycle_role], [])
        assert composed["_model_recommendation"]["min_tier"] == "advanced"
        assert composed["_model_recommendation"]["reasoning"] == "extended"
        assert (
            composed["_model_recommendation"]["rationale"] == "Complex architecture work"
        )


class TestAggregateModelRequirements:
    def test_defaults_to_fast_none(self):
        roles = [{"name": "simple", "guidelines": ["a"]}]
        composed = {"guidelines": ["a"]}
        recipe = {"name": "test"}
        result = aggregate_model_requirements(roles, composed, recipe)
        assert result["min_tier"] == "fast"
        assert result["reasoning"] == "none"

    def test_takes_max_tier(self):
        roles = [
            {"name": "role-a", "model_requirements": {"min_tier": "fast"}},
            {"name": "role-b", "model_requirements": {"min_tier": "standard"}},
            {"name": "role-c", "model_requirements": {"min_tier": "fast"}},
        ]
        composed = {"guidelines": ["a", "b"]}
        recipe = {"name": "test"}
        result = aggregate_model_requirements(roles, composed, recipe)
        assert result["min_tier"] == "standard"

    def test_takes_max_reasoning(self):
        roles = [
            {"name": "role-a", "model_requirements": {"reasoning": "none"}},
            {"name": "role-b", "model_requirements": {"reasoning": "extended"}},
            {"name": "role-c", "model_requirements": {"reasoning": "standard"}},
        ]
        composed = {"guidelines": ["a"]}
        recipe = {"name": "test"}
        result = aggregate_model_requirements(roles, composed, recipe)
        assert result["reasoning"] == "extended"

    def test_composition_bonus_bumps_tier_at_30_guidelines(self):
        roles = [{"name": "simple"}]
        composed = {"guidelines": [f"g{i}" for i in range(31)]}
        recipe = {"name": "test"}
        result = aggregate_model_requirements(roles, composed, recipe)
        assert result["min_tier"] == "standard"

    def test_no_composition_bonus_under_30_guidelines(self):
        roles = [{"name": "simple"}]
        composed = {"guidelines": [f"g{i}" for i in range(20)]}
        recipe = {"name": "test"}
        result = aggregate_model_requirements(roles, composed, recipe)
        assert result["min_tier"] == "fast"

    def test_composition_bonus_bumps_reasoning_at_50_guidelines(self):
        roles = [{"name": "simple"}]
        composed = {"guidelines": [f"g{i}" for i in range(51)]}
        recipe = {"name": "test"}
        result = aggregate_model_requirements(roles, composed, recipe)
        assert result["reasoning"] == "standard"

    def test_recipe_override_wins(self):
        roles = [
            {
                "name": "role-a",
                "model_requirements": {"min_tier": "standard", "reasoning": "extended"},
            },
        ]
        composed = {"guidelines": ["a"]}
        recipe = {
            "name": "test",
            "model_recommendation": {"min_tier": "fast", "reasoning": "none"},
        }
        result = aggregate_model_requirements(roles, composed, recipe)
        assert result["min_tier"] == "fast"
        assert result["reasoning"] == "none"

    def test_rationale_mentions_role_count(self):
        roles = [
            {"name": "role-a"},
            {"name": "role-b"},
            {"name": "role-c"},
        ]
        composed = {"guidelines": ["a", "b"], "tools": [{"name": "t1"}]}
        recipe = {"name": "test"}
        result = aggregate_model_requirements(roles, composed, recipe)
        assert "3 composed roles" in result["rationale"]

    def test_rationale_mentions_tier_driver(self):
        roles = [
            {"name": "fast-role"},
            {"name": "standard-role", "model_requirements": {"min_tier": "standard"}},
        ]
        composed = {"guidelines": ["a"]}
        recipe = {"name": "test"}
        result = aggregate_model_requirements(roles, composed, recipe)
        assert "standard-role" in result["rationale"]

    def test_advanced_tier_beats_standard(self):
        roles = [
            {"name": "role-a", "model_requirements": {"min_tier": "standard"}},
            {"name": "role-b", "model_requirements": {"min_tier": "advanced"}},
        ]
        composed = {"guidelines": ["a"]}
        recipe = {"name": "test"}
        result = aggregate_model_requirements(roles, composed, recipe)
        assert result["min_tier"] == "advanced"


class TestVerificationMerge:
    def test_deduplicates_by_check_key(self):
        roles = [
            {"verification": [{"check": "Tests pass", "command": "pytest"}]},
            {"verification": [{"check": "Tests pass", "command": "dotnet test"}]},
        ]
        result = merge_union_by_key(roles, "verification", "check")
        assert len(result) == 1
        assert result[0]["command"] == "pytest"

    def test_combines_different_checks(self):
        roles = [
            {"verification": [{"check": "Linting passes", "command": "ruff check ."}]},
            {
                "verification": [
                    {"check": "Code is formatted", "command": "black --check ."}
                ]
            },
        ]
        result = merge_union_by_key(roles, "verification", "check")
        assert len(result) == 2

    def test_handles_checks_without_command(self):
        roles = [
            {"verification": [{"check": "Business logic separated"}]},
            {"verification": [{"check": "Input validated at boundary"}]},
        ]
        result = merge_union_by_key(roles, "verification", "check")
        assert len(result) == 2
        assert "command" not in result[0]

    def test_verification_in_compose_recipe(
        self,
        sample_lifecycle_role,
        sample_language_role,
    ):
        sample_lifecycle_role["verification"] = [
            {"check": "Tests pass"},
        ]
        sample_language_role["verification"] = [
            {"check": "Linting passes", "command": "ruff check ."},
        ]
        recipe = {"name": "verify-test", "compose": ["a", "b"]}
        composed, _ = compose_recipe(
            recipe,
            [sample_lifecycle_role, sample_language_role],
            [],
        )
        assert len(composed["verification"]) == 2
        checks = [v["check"] for v in composed["verification"]]
        assert "Tests pass" in checks
        assert "Linting passes" in checks

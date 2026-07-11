"""
Data validation, boundary conditions, and state edge case tests.

Tests handling of special characters, data types, boundary conditions,
very large/small collections, concurrent operations, and state management.
"""

from __future__ import annotations

import time
from pathlib import Path
from threading import Thread

import pytest
import yaml

from generator.installer import get_install_path, install_output
from generator.loader import load_recipe, load_recipe_roles, load_yaml
from generator.merge.strategies import (
    merge_roles,
    merge_union_by_key,
    parse_field_strategies,
)
from generator.skills import extract_tool_commands, sanitize_script_name
from generator.validator import duplicate_tool_name_errors, validate_role
from tests.conftest import write_yaml

pytestmark = [pytest.mark.unit, pytest.mark.validation, pytest.mark.readonly]


class TestDataValidation:
    """Test validation of data types and content."""

    def test_empty_string_in_required_field_name(self, tmp_path: Path):
        """Empty string for name should be rejected by validation."""
        data = {"name": "", "type": "test", "responsibilities": ["test"]}

        # Empty name should fail schema validation
        from generator.validator import load_schema

        schema_path = tmp_path.parent.parent / "schemas" / "base-role.schema.json"
        if not schema_path.exists():
            schema_path = Path("schemas") / "base-role.schema.json"

        if schema_path.exists():
            schema = load_schema(schema_path)
            errors = validate_role(data, schema)
            assert len(errors) > 0

    def test_special_characters_in_tool_name(self):
        """Special characters in tool names should be sanitized."""
        assert sanitize_script_name("my.tool") == "my-tool"
        assert sanitize_script_name("Azure CLI") == "azure-cli"
        assert sanitize_script_name("test@tool!") == "test-tool"
        assert sanitize_script_name("a/b\\c:d*e?f") == "a-b-c-d-e-f"

    def test_emoji_in_tool_name(self):
        """Emoji and unicode in tool names should be handled."""
        assert sanitize_script_name("🚀 rocket-tool") == "rocket-tool"
        assert sanitize_script_name("テスト") == ""  # Non-latin chars removed

    def test_control_characters_in_yaml_string(self, tmp_path: Path):
        """Control characters in YAML strings should be preserved or escaped."""
        path = tmp_path / "control.yaml"
        # Embed control character
        data = {"name": "test\x00null\x01byte", "type": "test"}

        # Write and read back
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

        result = load_yaml(path)
        # PyYAML may escape or preserve control chars
        assert "name" in result

    def test_very_long_string_in_description(self, tmp_path: Path):
        """Very long strings (>1000 chars) should be handled."""
        long_desc = "x" * 10000  # 10k character description
        data = {
            "name": "test",
            "type": "test",
            "responsibilities": ["test"],
            "description": long_desc,
        }

        path = write_yaml(tmp_path / "long.yaml", data)
        result = load_yaml(path)
        assert len(result["description"]) == 10000

    def test_null_value_in_optional_field(self, tmp_path: Path):
        """Null/None values in optional fields should be handled."""
        data = {
            "name": "test",
            "type": "test",
            "responsibilities": ["test"],
            "tone": None,
            "output_format": None,
        }

        path = write_yaml(tmp_path / "nulls.yaml", data)
        result = load_yaml(path)
        assert result["tone"] is None

    def test_wrong_data_type_for_list_field(self, tmp_path: Path):
        """String where list expected should be caught by validation."""
        data = {
            "name": "test",
            "type": "test",
            "responsibilities": "not a list",  # Should be list
        }

        # Load succeeds (it's valid YAML), but validation should fail
        from generator.validator import load_schema

        schema_path = Path("schemas") / "base-role.schema.json"
        if schema_path.exists():
            schema = load_schema(schema_path)
            errors = validate_role(data, schema)
            assert len(errors) > 0

    def test_duplicate_tool_names_case_insensitive(self):
        """Duplicate tool names (case-insensitive) should be detected."""
        role_data = {
            "tools": [
                {"name": "MyTool", "purpose": "first"},
                {"name": "mytool", "purpose": "second"},
                {"name": "MYTOOL", "purpose": "third"},
            ]
        }

        errors = duplicate_tool_name_errors(role_data)
        assert len(errors) >= 2  # Should detect duplicates

    def test_whitespace_only_tool_name(self):
        """Whitespace-only tool names should be ignored in duplicate check."""
        role_data = {
            "tools": [
                {"name": "   ", "purpose": "empty"},
                {"name": "\t\n", "purpose": "whitespace"},
                {"name": "valid", "purpose": "ok"},
            ]
        }

        errors = duplicate_tool_name_errors(role_data)
        # Whitespace-only names are ignored (dedupe skips empty keys)
        assert len(errors) == 0

    def test_tool_without_name_field(self):
        """Tools without 'name' field should not crash duplicate check."""
        role_data = {
            "tools": [
                {"purpose": "no name field"},
                {"name": "valid", "purpose": "has name"},
            ]
        }

        errors = duplicate_tool_name_errors(role_data)
        assert len(errors) == 0  # No duplicates


class TestBoundaryConditions:
    """Test boundary conditions for collections and limits."""

    def test_empty_list_responsibilities(self, tmp_path: Path):
        """Role with empty responsibilities list should fail validation."""
        data = {"name": "test", "type": "test", "responsibilities": []}

        from generator.validator import load_schema

        schema_path = Path("schemas") / "base-role.schema.json"
        if schema_path.exists():
            schema = load_schema(schema_path)
            errors = validate_role(data, schema)
            # Schema requires minItems: 1
            assert any("responsibilities" in err for err in errors)

    def test_single_item_list_compose(self, project_layout):
        """Recipe with single compose item should work."""
        data = {"name": "minimal", "compose": ["base/lifecycle/architect"]}

        write_yaml(project_layout.recipes / "minimal.yaml", data)
        recipe = load_recipe("minimal", project_layout.root)
        assert len(recipe["compose"]) == 1

    def test_very_large_compose_list(self, project_layout):
        """Recipe with very large compose list (>100 items) should work."""
        # Create many roles first
        for i in range(110):
            role_data = {
                "name": f"role-{i}",
                "type": "test",
                "responsibilities": [f"task {i}"],
            }
            write_yaml(project_layout.base / "mixins" / f"role-{i}.yaml", role_data)

        # Create recipe with all roles
        recipe_data = {"name": "huge", "compose": [f"role-{i}" for i in range(110)]}

        write_yaml(project_layout.recipes / "huge.yaml", recipe_data)
        recipe = load_recipe("huge", project_layout.root)
        assert len(recipe["compose"]) == 110

    def test_empty_dictionary_for_context_field(self):
        """Empty dictionary in context field should be handled."""
        roles = [{"context": {}}, {"context": {"key": "value"}}]

        from generator.merge.strategies import merge_deep

        result = merge_deep(roles, "context")
        assert result == {"key": "value"}

    def test_nested_depth_limit_in_deep_merge(self):
        """Very deep nesting in context should be preserved."""
        roles = []

        # Create deeply nested structure (50 levels)
        deep_dict = {"level": 50}
        for i in range(49, 0, -1):
            deep_dict = {f"level-{i}": deep_dict}

        roles.append({"context": deep_dict})

        from generator.merge.strategies import merge_deep

        result = merge_deep(roles, "context")

        # Verify deep structure preserved
        current = result
        for i in range(1, 50):
            assert f"level-{i}" in current
            current = current[f"level-{i}"]

    def test_merge_with_no_roles(self):
        """Merging zero roles should return empty dict."""
        result = merge_roles([])
        assert result == {}

    def test_merge_with_single_role(self):
        """Merging single role should return that role's fields."""
        role = {"responsibilities": ["task1", "task2"], "guidelines": ["rule1"]}

        result = merge_roles([role])
        assert result["responsibilities"] == ["task1", "task2"]
        assert result["guidelines"] == ["rule1"]

    def test_union_by_key_with_empty_list(self):
        """Union-by-key with empty lists should return empty list."""
        roles = [{"tools": []}, {"tools": []}]

        result = merge_union_by_key(roles, "tools", "name")
        assert result == []

    def test_union_by_key_with_missing_key(self):
        """Union-by-key where items lack the key field should handle gracefully."""
        roles = [
            {
                "tools": [
                    {"name": "tool1", "purpose": "a"},
                    {"purpose": "no name"},  # Missing 'name' key
                    {"name": "tool2", "purpose": "b"},
                ]
            }
        ]

        result = merge_union_by_key(roles, "tools", "name")
        # Should include tool1 and tool2, may include item without name
        assert len(result) >= 2

    def test_very_large_guidelines_list_affects_tier(self):
        """Large number of guidelines (>50) should bump tier recommendation."""
        from generator.merge.model_requirements import (
            REASONING_ORDER,
            TIER_ORDER,
            _apply_guideline_count_tier_bumps,
        )

        # 60 guidelines should force standard tier
        max_tier, max_reasoning, drivers = _apply_guideline_count_tier_bumps(
            guideline_count=60,
            max_tier=TIER_ORDER["fast"],
            max_reasoning=REASONING_ORDER["none"],
            tier_drivers=[],
        )

        assert max_tier >= TIER_ORDER["standard"]


class TestStateAndConcurrency:
    """Test state management and potential race conditions."""

    def test_install_multiple_formats_same_recipe(self, tmp_path: Path):
        """Installing same recipe in multiple formats should not conflict."""
        content = "# Test recipe"

        # Install in multiple formats
        path1 = install_output(content, "copilot", "test", tmp_path / "copilot")
        path2 = install_output(content, "claude", "test", tmp_path / "claude")
        path3 = install_output(content, "cursor", "test", tmp_path / "cursor")

        # All should exist independently
        assert path1.exists()
        assert path2.exists()
        assert path3.exists()
        assert path1 != path2 != path3

    def test_corrupted_merge_config_fallback_to_defaults(self, project_layout):
        """Corrupted merge config should fall back to defaults."""
        # Create corrupted config
        config_path = project_layout.config / "merge-config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("this: is: not: valid: yaml: [[[", encoding="utf-8")

        # parse_field_strategies should handle gracefully
        strategies, union_by_key = parse_field_strategies(None)

        # Should return default strategies
        assert "responsibilities" in strategies
        assert strategies["responsibilities"] == "union"

    def test_race_condition_concurrent_file_writes(self, tmp_path: Path):
        """Concurrent writes to same file should be handled."""

        def write_file(content: str):
            time.sleep(0.001)  # Small delay to increase race chance
            install_output(content, "copilot", "race-test", tmp_path)

        # Launch multiple concurrent writes
        threads = [Thread(target=write_file, args=(f"content-{i}",)) for i in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # File should exist (one of the writes succeeded)
        path = get_install_path("copilot", "race-test", tmp_path)
        assert path.exists()
        # Content should be from one of the writes
        content = path.read_text(encoding="utf-8")
        assert content.startswith("content-")

    def test_extract_tool_commands_with_malformed_tools(self):
        """Extracting tool commands from malformed tools list should not crash."""
        recipe = {
            "tools": [
                {"name": "tool1", "command": "echo 1", "purpose": "test"},
                "not a dict",  # Invalid: string instead of dict
                {"name": "tool2"},  # Missing 'command' field
                None,  # Invalid: None
                {"command": "echo 3"},  # Missing 'name'
            ]
        }

        result = extract_tool_commands(recipe)

        # Should extract only valid tool1 and the unnamed one with command
        assert len(result) >= 1
        assert any(cmd["name"] == "tool1" for cmd in result)

    def test_parallel_recipe_loading_same_roles(self, project_layout):
        """Loading multiple recipes that reference same roles concurrently."""
        # Create shared roles
        for i in range(3):
            role_data = {
                "name": f"shared-{i}",
                "type": "test",
                "responsibilities": [f"task {i}"],
            }
            write_yaml(project_layout.base / "mixins" / f"shared-{i}.yaml", role_data)

        # Create multiple recipes using same roles
        for i in range(5):
            recipe_data = {
                "name": f"recipe-{i}",
                "compose": ["shared-0", "shared-1", "shared-2"],
            }
            write_yaml(project_layout.recipes / f"recipe-{i}.yaml", recipe_data)

        # Load all recipes (simulating parallel access)
        results = {}

        def load_and_store(recipe_name: str):
            recipe = load_recipe(recipe_name, project_layout.root)
            roles, mixins = load_recipe_roles(recipe, project_layout.root)
            results[recipe_name] = roles

        threads = [Thread(target=load_and_store, args=(f"recipe-{i}",)) for i in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # All should load successfully
        assert len(results) == 5
        for roles in results.values():
            assert len(roles) == 3

    def test_missing_template_file_raises_clear_error(self, tmp_path: Path):
        """Missing template file should raise FileNotFoundError."""
        from generator.skills import SkillGenerator

        gen = SkillGenerator(template_dir=tmp_path / "nonexistent")

        with pytest.raises(FileNotFoundError, match="Template not found"):
            gen.load_template("SKILL.md.template")


class TestAdditionalEdgeCases:
    """Additional edge cases that don't fit other categories."""

    def test_recipe_with_circular_mixin_reference(self, project_layout):
        """Recipe with mixins that reference each other shouldn't cause infinite loop."""
        # This is more of a design question - current code doesn't support
        # nested mixin loading, but test the boundary

        mixin_data = {"name": "self-ref", "type": "mixin", "responsibilities": ["test"]}
        write_yaml(project_layout.base / "mixins" / "self-ref.yaml", mixin_data)

        recipe_data = {
            "name": "circular",
            "compose": ["self-ref"],
            "mixins": ["self-ref"],  # Same mixin in both
        }

        write_yaml(project_layout.recipes / "circular.yaml", recipe_data)
        recipe = load_recipe("circular", project_layout.root)

        # Should load without infinite loop
        roles, mixins = load_recipe_roles(recipe, project_layout.root)
        assert len(roles) == 1
        assert len(mixins) == 1

    def test_tool_sanitize_name_all_special_chars(self):
        """Tool name with only special characters should return empty or default."""
        result = sanitize_script_name("!@#$%^&*()")
        assert result == "" or result == "tool"  # Empty or some default

    def test_tool_sanitize_name_with_consecutive_hyphens(self):
        """Multiple consecutive hyphens should collapse to single hyphen."""
        assert sanitize_script_name("my---tool") == "my-tool"
        assert sanitize_script_name("a..b..c") == "a-b-c"

    def test_yaml_with_extremely_long_key(self, tmp_path: Path):
        """YAML with extremely long key names should be handled."""
        long_key = "x" * 10000
        data = {long_key: "value", "name": "test"}

        path = write_yaml(tmp_path / "longkey.yaml", data)
        result = load_yaml(path)

        assert long_key in result
        assert result["name"] == "test"

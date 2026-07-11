"""
YAML validation edge case tests.

Tests handling of malformed YAML, invalid syntax, missing required fields,
and other YAML-specific edge cases.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.exceptions import LoadError
from generator.loader import load_recipe, load_role, load_yaml
from tests.conftest import write_yaml

pytestmark = [pytest.mark.unit, pytest.mark.validation, pytest.mark.readonly]


class TestInvalidYAML:
    """Test handling of malformed and invalid YAML files."""

    def test_malformed_yaml_syntax_raises_load_error(self, tmp_path: Path):
        """Malformed YAML syntax should raise LoadError with helpful message."""
        path = tmp_path / "malformed.yaml"
        path.write_text("key: value\n  - invalid indentation\n[broken", encoding="utf-8")

        with pytest.raises(LoadError, match="Invalid YAML"):
            load_yaml(path)

    def test_yaml_with_tabs_mixed_indentation(self, tmp_path: Path):
        """YAML with mixed tabs and spaces should fail gracefully."""
        path = tmp_path / "tabs.yaml"
        # Mix tabs and spaces (YAML disallows tabs for indentation)
        path.write_text("name: test\n\tkey:\n  value: bad", encoding="utf-8")

        with pytest.raises(LoadError, match="Invalid YAML"):
            load_yaml(path)

    def test_yaml_with_duplicate_keys(self, tmp_path: Path):
        """YAML with duplicate keys should be handled (PyYAML uses last value)."""
        path = tmp_path / "duplicate.yaml"
        path.write_text("name: first\nname: second\ntype: test", encoding="utf-8")

        # PyYAML accepts duplicate keys, keeps last value
        result = load_yaml(path)
        assert result["name"] == "second"

    def test_yaml_anchor_and_alias_circular_reference(self, tmp_path: Path):
        """Circular YAML aliases are handled by PyYAML (creates recursive structure)."""
        path = tmp_path / "circular.yaml"
        # Create self-referencing anchor
        path.write_text("a: &anchor\n  b: *anchor", encoding="utf-8")

        # PyYAML actually handles this gracefully - creates recursive structure
        result = load_yaml(path)
        assert "a" in result
        # The structure is circular: result["a"]["b"] is result["a"]

    def test_yaml_bomb_deeply_nested(self, tmp_path: Path):
        """Deeply nested YAML structures are handled by PyYAML (with limits)."""
        path = tmp_path / "nested.yaml"
        # Create deeply nested structure (but not exponential like billion laughs)
        yaml_content = "level0:\n"
        indent = "  "
        for i in range(1, 30):  # 30 levels deep
            yaml_content += f"{indent * i}level{i}:\n"
        yaml_content += f"{indent * 30}value: deepest\n"

        path.write_text(yaml_content, encoding="utf-8")

        # PyYAML can handle deep nesting up to reasonable limits
        result = load_yaml(path)
        assert "level0" in result
        # Navigate deep and verify structure loaded
        current = result
        for i in range(30):
            assert f"level{i}" in current
            current = current[f"level{i}"]

    def test_role_missing_required_field_name(self, project_layout):
        """Role without 'name' field should raise specific error."""
        data = {"type": "test", "responsibilities": ["do things"]}
        write_yaml(project_layout.base / "mixins" / "noname.yaml", data)

        with pytest.raises(LoadError, match="missing required field 'name'"):
            load_role("noname", project_layout.root)

    def test_role_missing_required_field_responsibilities(self, project_layout):
        """Role without 'responsibilities' field should raise specific error."""
        data = {"name": "incomplete", "type": "test"}
        write_yaml(project_layout.base / "mixins" / "incomplete.yaml", data)

        with pytest.raises(LoadError, match="missing required field 'responsibilities'"):
            load_role("incomplete", project_layout.root)

    def test_recipe_missing_required_field_compose(self, project_layout):
        """Recipe without 'compose' field should raise specific error."""
        data = {"name": "bad-recipe", "description": "Missing compose"}
        write_yaml(project_layout.recipes / "bad.yaml", data)

        with pytest.raises(LoadError, match="missing or empty 'compose' field"):
            load_recipe("bad", project_layout.root)

    def test_recipe_empty_compose_list(self, project_layout):
        """Recipe with empty compose list should raise error."""
        data = {"name": "empty-recipe", "compose": []}
        write_yaml(project_layout.recipes / "empty.yaml", data)

        with pytest.raises(LoadError, match="missing or empty 'compose' field"):
            load_recipe("empty", project_layout.root)

    def test_yaml_with_binary_data(self, tmp_path: Path):
        """YAML containing binary data should be handled gracefully."""
        path = tmp_path / "binary.yaml"
        # Write binary data that's not valid UTF-8
        path.write_bytes(b"name: test\ndata: \xff\xfe\x00\x01")

        with pytest.raises((LoadError, UnicodeDecodeError)):
            load_yaml(path)

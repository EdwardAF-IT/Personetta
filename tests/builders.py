"""
Test data builders for creating role and recipe test fixtures.

Provides builder pattern for constructing test data, reducing verbosity in tests
and providing a single source of truth for valid role/recipe structure.

Example usage:
    # Create a simple role
    role = RoleBuilder().with_name("test-developer") \\
        .with_responsibilities("Write code", "Handle errors") \\
        .build()
    
    # Create a recipe
    recipe = RecipeBuilder().with_name("test-recipe") \\
        .with_compose("base/lifecycle/developer") \\
        .build()
"""

from __future__ import annotations

from typing import Any


class RoleBuilder:
    """Builder for creating role dictionaries in tests."""

    def __init__(self):
        """Initialize with minimal valid role structure."""
        self.data: dict[str, Any] = {
            "name": "test-role",
            "description": "A test role.",
            "version": "1.0.0",
            "type": "lifecycle",
            "responsibilities": [],
        }

    def with_name(self, name: str) -> RoleBuilder:
        """Set role name."""
        self.data["name"] = name
        return self

    def with_description(self, description: str) -> RoleBuilder:
        """Set role description."""
        self.data["description"] = description
        return self

    def with_type(self, role_type: str) -> RoleBuilder:
        """Set role type (lifecycle, layer, language, mixin)."""
        self.data["type"] = role_type
        return self

    def with_responsibilities(self, *items: str) -> RoleBuilder:
        """Add responsibilities."""
        self.data.setdefault("responsibilities", []).extend(items)
        return self

    def with_non_responsibilities(self, *items: str) -> RoleBuilder:
        """Add non-responsibilities."""
        self.data.setdefault("non_responsibilities", []).extend(items)
        return self

    def with_guidelines(self, *items: str) -> RoleBuilder:
        """Add guidelines."""
        self.data.setdefault("guidelines", []).extend(items)
        return self

    def with_tools(self, *tools: dict) -> RoleBuilder:
        """Add tools. Each tool should be a dict with 'name' and optionally 'purpose', 'when'."""
        self.data.setdefault("tools", []).extend(tools)
        return self

    def with_tool(self, name: str, purpose: str = "", when: str = "") -> RoleBuilder:
        """Add a single tool."""
        tool = {"name": name}
        if purpose:
            tool["purpose"] = purpose
        if when:
            tool["when"] = when
        self.data.setdefault("tools", []).append(tool)
        return self

    def with_verification(self, *checks: dict | str) -> RoleBuilder:
        """Add verification checks. Each check can be a dict or a string."""
        for check in checks:
            if isinstance(check, str):
                self.data.setdefault("verification", []).append({"check": check})
            else:
                self.data.setdefault("verification", []).append(check)
        return self

    def with_tone(self, tone: str) -> RoleBuilder:
        """Set tone."""
        self.data["tone"] = tone
        return self

    def with_output_format(self, output_format: str) -> RoleBuilder:
        """Set output format."""
        self.data["output_format"] = output_format
        return self

    def with_tags(self, *tags: str) -> RoleBuilder:
        """Add tags."""
        self.data.setdefault("tags", []).extend(tags)
        return self

    def with_examples(self, *examples: dict) -> RoleBuilder:
        """Add examples."""
        self.data.setdefault("examples", []).extend(examples)
        return self

    def with_model_requirements(
        self,
        tier: str | None = None,
        reasoning: str | None = None,
        drivers: list[str] | None = None,
    ) -> RoleBuilder:
        """Set model requirements."""
        req: dict[str, Any] = {}
        if tier:
            req["tier"] = tier
        if reasoning:
            req["reasoning"] = reasoning
        if drivers:
            req["drivers"] = drivers
        if req:
            self.data["model_requirements"] = req
        return self

    def build(self) -> dict:
        """Return the constructed role dictionary."""
        return dict(self.data)


class RecipeBuilder:
    """Builder for creating recipe dictionaries in tests."""

    def __init__(self):
        """Initialize with minimal valid recipe structure."""
        self.data: dict[str, Any] = {
            "name": "test-recipe",
            "description": "A test recipe.",
            "compose": [],
        }

    def with_name(self, name: str) -> RecipeBuilder:
        """Set recipe name."""
        self.data["name"] = name
        return self

    def with_description(self, description: str) -> RecipeBuilder:
        """Set recipe description."""
        self.data["description"] = description
        return self

    def with_compose(self, *role_refs: str) -> RecipeBuilder:
        """Add role references to compose list."""
        self.data.setdefault("compose", []).extend(role_refs)
        return self

    def with_mixins(self, *mixin_refs: str) -> RecipeBuilder:
        """Add mixin references."""
        self.data.setdefault("mixins", []).extend(mixin_refs)
        return self

    def with_overrides(self, **overrides: Any) -> RecipeBuilder:
        """Set recipe overrides."""
        self.data.setdefault("overrides", {}).update(overrides)
        return self

    def with_activation_phrases(self, *phrases: str) -> RecipeBuilder:
        """Add activation phrases."""
        self.data.setdefault("activation_phrases", []).extend(phrases)
        return self

    def with_model_requirements(
        self,
        tier: str | None = None,
        reasoning: str | None = None,
    ) -> RecipeBuilder:
        """Set model requirements override."""
        req = {}
        if tier:
            req["tier"] = tier
        if reasoning:
            req["reasoning"] = reasoning
        if req:
            self.data.setdefault("overrides", {})["model_requirements"] = req
        return self

    def build(self) -> dict:
        """Return the constructed recipe dictionary."""
        return dict(self.data)


class MergeWarningBuilder:
    """Builder for creating MergeWarning instances in tests."""

    def __init__(self):
        """Initialize with default warning."""
        self.severity = "warning"
        self.message = "Test warning"

    def as_error(self) -> MergeWarningBuilder:
        """Set severity to error."""
        self.severity = "error"
        return self

    def as_warning(self) -> MergeWarningBuilder:
        """Set severity to warning."""
        self.severity = "warning"
        return self

    def as_info(self) -> MergeWarningBuilder:
        """Set severity to info."""
        self.severity = "info"
        return self

    def with_message(self, message: str) -> MergeWarningBuilder:
        """Set message."""
        self.message = message
        return self

    def build(self):
        """Return the constructed MergeWarning."""
        from generator.merger import MergeWarning

        return MergeWarning(severity=self.severity, message=self.message)


# ━━━ Convenience Functions ━━━


def make_role(
    name: str,
    role_type: str = "lifecycle",
    responsibilities: list[str] | None = None,
    **kwargs,
) -> dict:
    """Quick role creation without builder pattern."""
    builder = RoleBuilder().with_name(name).with_type(role_type)
    if responsibilities:
        builder.with_responsibilities(*responsibilities)
    for key, value in kwargs.items():
        if key == "guidelines" and isinstance(value, list):
            builder.with_guidelines(*value)
        elif key == "tools" and isinstance(value, list):
            builder.with_tools(*value)
        elif key == "tags" and isinstance(value, list):
            builder.with_tags(*value)
        else:
            builder.data[key] = value
    return builder.build()


def make_recipe(name: str, compose: list[str], **kwargs) -> dict:
    """Quick recipe creation without builder pattern."""
    builder = RecipeBuilder().with_name(name).with_compose(*compose)
    for key, value in kwargs.items():
        if key == "mixins" and isinstance(value, list):
            builder.with_mixins(*value)
        elif key == "activation_phrases" and isinstance(value, list):
            builder.with_activation_phrases(*value)
        else:
            builder.data[key] = value
    return builder.build()

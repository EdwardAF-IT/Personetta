from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import yaml

from generator.project_layout import ProjectLayout


def load_schema(schema_path: Path) -> dict:
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _schema_instance_errors(instance: dict, schema: dict) -> list[str]:
    validator = jsonschema.Draft7Validator(schema)
    lines: list[str] = []
    for error in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in error.absolute_path) or "(root)"
        lines.append(f"{path}: {error.message}")
    return lines


def validate_role(role_data: dict, schema: dict) -> list[str]:
    return _schema_instance_errors(role_data, schema)


def validate_recipe(recipe_data: dict, schema: dict) -> list[str]:
    return _schema_instance_errors(recipe_data, schema)


def duplicate_tool_name_errors(role_data: dict) -> list[str]:
    """Flag duplicate tool entries in one role (same name after strip + casefold)."""
    tools = role_data.get("tools")
    if not isinstance(tools, list):
        return []

    seen: dict[str, str] = {}
    errors: list[str] = []
    for item in tools:
        if not isinstance(item, dict):
            continue
        raw = item.get("name")
        if not isinstance(raw, str):
            continue
        key = raw.strip().casefold()
        if not key:
            continue
        if key in seen:
            errors.append(
                f"tools: duplicate tool name {raw!r} (same as {seen[key]!r} after trim/casefold)",
            )
        else:
            seen[key] = raw
    return errors


def validate_all(base_dir: Path) -> dict[str, list[str]]:
    results: dict[str, list[str]] = {}

    # Use ProjectLayout to get correct paths
    layout = ProjectLayout(base_dir)
    role_schema_path = layout.schemas / "base-role.schema.json"
    recipe_schema_path = layout.schemas / "recipe.schema.json"

    role_schema = load_schema(role_schema_path)
    recipe_schema = load_schema(recipe_schema_path)

    for pattern in ["data/base/**/*.yaml", "data/language_specific/**/*.yaml"]:
        for path in sorted(base_dir.glob(pattern)):
            # Skip system roles (baseline, router) - they have a different structure
            if "base/system" in path.relative_to(base_dir).as_posix():
                continue
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                results[str(path.relative_to(base_dir))] = ["Not a valid YAML mapping"]
                continue
            rel = str(path.relative_to(base_dir))
            errors = validate_role(data, role_schema)
            errors.extend(duplicate_tool_name_errors(data))
            if errors:
                results[rel] = errors

    recipe_dir = base_dir / "recipes"
    if recipe_dir.exists():
        for path in sorted(recipe_dir.glob("*.yaml")):
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                results[str(path.relative_to(base_dir))] = ["Not a valid YAML mapping"]
                continue
            errors = validate_recipe(data, recipe_schema)
            if errors:
                results[str(path.relative_to(base_dir))] = errors

    return results

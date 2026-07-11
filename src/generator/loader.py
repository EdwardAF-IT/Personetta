from __future__ import annotations

import yaml
from pathlib import Path

from generator.exceptions import LoadError
from generator.project_layout import ProjectLayout


def load_yaml(path: Path) -> dict:
    if not path.exists():
        raise LoadError(f"File not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise LoadError(f"Invalid YAML in {path}: {e}") from e
    if not isinstance(data, dict):
        raise LoadError(f"Expected a YAML mapping in {path}, got {type(data).__name__}")
    return data


def resolve_role_path(ref: str, base_dir: Path) -> Path:
    """Resolve role reference to file path using project layout."""
    layout = ProjectLayout(base_dir)
    if "/" in ref:
        # Handle prefixed paths (e.g., "base/lifecycle/...", "language_specific/python/...")
        # Also support legacy "language-specific/" format for backwards compatibility
        if ref.startswith("base/"):
            # Strip "base/" prefix since layout.base already points to data/base/
            return layout.base / f"{ref[5:]}.yaml"
        elif ref.startswith("language_specific/"):
            # Strip "language_specific/" prefix
            return layout.language_specific / f"{ref[18:]}.yaml"
        elif ref.startswith("language-specific/"):
            # Legacy format - convert to new path
            return layout.language_specific / f"{ref[18:]}.yaml"
        else:
            # Assume it's under base/ if no prefix
            return layout.base / f"{ref}.yaml"
    return layout.base / "mixins" / f"{ref}.yaml"


def load_role(ref: str, base_dir: Path) -> dict:
    path = resolve_role_path(ref, base_dir)
    role = load_yaml(path)
    if "name" not in role:
        raise LoadError(f"Role at {path} missing required field 'name'")
    if "responsibilities" not in role:
        raise LoadError(
            f"Role '{role.get('name', '?')}' at {path} missing required field 'responsibilities'"
        )
    return role


def load_recipe(name_or_path: str, base_dir: Path) -> dict:
    """Load recipe using project layout."""
    layout = ProjectLayout(base_dir)
    if name_or_path.endswith(".yaml"):
        path = Path(name_or_path)
        if not path.is_absolute():
            path = layout.root / path
    else:
        path = layout.recipes / f"{name_or_path}.yaml"
    recipe = load_yaml(path)
    if "name" not in recipe:
        raise LoadError(f"Recipe at {path} missing required field 'name'")
    if "compose" not in recipe or not recipe["compose"]:
        raise LoadError(
            f"Recipe '{recipe['name']}' at {path} missing or empty 'compose' field"
        )
    return recipe


def load_recipe_roles(recipe: dict, base_dir: Path) -> tuple[list[dict], list[dict]]:
    compose_roles = []
    for ref in recipe["compose"]:
        compose_roles.append(load_role(ref, base_dir))

    mixin_roles = []
    for ref in recipe.get("mixins", []):
        mixin_roles.append(load_role(ref, base_dir))

    return compose_roles, mixin_roles


def load_merge_config(base_dir: Path) -> dict:
    """Load merge configuration using project layout."""
    layout = ProjectLayout(base_dir)
    path = layout.config / "merge-config.yaml"
    return load_yaml(path)


def list_roles(base_dir: Path) -> list[dict]:
    """List all roles using project layout."""
    layout = ProjectLayout(base_dir)
    roles = []
    # Search in base and language-specific directories
    for search_dir in [layout.base, layout.language_specific]:
        for path in sorted(search_dir.rglob("*.yaml")):
            try:
                role = load_yaml(path)
                roles.append(
                    {
                        "name": role.get("name", path.stem),
                        "type": role.get("type", "unknown"),
                        "description": role.get("description", "").strip().split("\n")[0],
                        "path": str(path.relative_to(layout.root)),
                    }
                )
            except LoadError:
                continue
    return roles


def list_recipes(base_dir: Path) -> list[dict]:
    """List all recipes using project layout."""
    layout = ProjectLayout(base_dir)
    recipes: list[dict] = []
    if not layout.recipes.exists():
        return recipes
    for path in sorted(layout.recipes.glob("*.yaml")):
        try:
            recipe = load_yaml(path)
            recipes.append(
                {
                    "name": recipe.get("name", path.stem),
                    "description": recipe.get("description", "").strip().split("\n")[0],
                    "compose": recipe.get("compose", []),
                    "mixins": recipe.get("mixins", []),
                    "activation_phrases": recipe.get("activation_phrases") or [],
                    "path": str(path.relative_to(layout.root)),
                }
            )
        except LoadError:
            continue
    return recipes


def load_system_role(role_name: str, base_dir: Path) -> dict:
    """Load a system role (baseline or router) from base/system/ using project layout."""
    layout = ProjectLayout(base_dir)
    path = layout.base / "system" / f"{role_name}.yaml"
    return load_yaml(path)

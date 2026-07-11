"""
Merge composed roles and mixins. Field strategies and union-by-key columns are
read from ``config/merge-config.yaml`` (with safe defaults for missing keys).
"""

from __future__ import annotations

# Import from merge subpackage
from generator.merge import (
    MergeWarning,
    Severity,
    aggregate_model_requirements,
    detect_conflicts,
    merge_roles,
)

# Re-export for backward compatibility
__all__ = [
    "Severity",
    "MergeWarning",
    "merge_mixins",
    "apply_overrides",
    "compose_recipe",
]

# Priority fields preserved during mixin merging
PRIORITY_FIELDS = {"tone", "output_format"}


def merge_mixins(
    composed: dict, mixin_roles: list[dict], merge_config: dict | None = None
) -> dict:
    """
    Merge mixin roles into composed role, preserving priority fields.

    Priority fields (tone, output_format) from composed role are preserved
    after merging mixins.

    Args:
        composed: The base composed role
        mixin_roles: List of mixin roles to merge in
        merge_config: Optional merge configuration

    Returns:
        Merged role dictionary
    """
    # Preserve priority fields from composed role
    preserved = {}
    for pf in PRIORITY_FIELDS:
        if pf in composed:
            preserved[pf] = composed[pf]

    # Merge all roles together
    all_roles = [composed] + mixin_roles
    result = merge_roles(all_roles, merge_config)

    # Restore priority fields
    for pf, value in preserved.items():
        result[pf] = value

    return result


def apply_overrides(composed: dict, overrides: dict) -> dict:
    """
    Apply recipe-level overrides to composed role.

    Args:
        composed: The composed role dictionary
        overrides: Dictionary of field overrides

    Returns:
        Updated role dictionary
    """
    result = dict(composed)
    for key, value in overrides.items():
        result[key] = value
    return result


def compose_recipe(
    recipe: dict,
    compose_roles: list[dict],
    mixin_roles: list[dict],
    merge_config: dict | None = None,
) -> tuple[dict, list[MergeWarning]]:
    """
    Compose a complete recipe from roles, mixins, and overrides.

    This is the main entry point for recipe composition. It:
    1. Merges compose roles
    2. Merges mixin roles (if any)
    3. Applies recipe overrides (if any)
    4. Adds recipe metadata
    5. Aggregates model requirements
    6. Detects conflicts

    Args:
        recipe: Recipe dictionary with name, description, and optional overrides
        compose_roles: List of primary roles to compose
        mixin_roles: List of mixin roles to add
        merge_config: Optional merge configuration

    Returns:
        Tuple of (composed_role_dict, list_of_warnings)
    """
    # Merge compose roles
    result = merge_roles(compose_roles, merge_config)

    # Merge mixins (if any)
    if mixin_roles:
        result = merge_mixins(result, mixin_roles, merge_config)

    # Apply recipe-level overrides (if any)
    if recipe.get("overrides"):
        result = apply_overrides(result, recipe["overrides"])

    # Add recipe metadata
    result["_recipe_name"] = recipe["name"]
    result["_recipe_description"] = recipe.get("description", "")

    # Track source roles
    source_names = [r.get("name", "?") for r in compose_roles + mixin_roles]
    result["_source_roles"] = source_names

    # Aggregate model requirements
    result["_model_recommendation"] = aggregate_model_requirements(
        compose_roles + mixin_roles,
        result,
        recipe,
    )

    # Detect conflicts
    warnings = detect_conflicts(result, merge_config)

    return result, warnings

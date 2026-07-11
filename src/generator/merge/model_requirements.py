"""Model requirement aggregation for role composition.

Determines minimum model tier and reasoning level based on role complexity,
guideline counts, and recipe-level overrides.
"""

from __future__ import annotations

# Model tier and reasoning thresholds based on guideline count complexity
# These values are derived from:
# - Fast tier: <30 guidelines (~8K token context, simple decision trees)
# - Standard tier: 30-50 guidelines (~32K context, moderate complexity)
# - Extended reasoning: 50+ guidelines (complex multi-step reasoning required)
GUIDELINE_COUNT_FORCE_STANDARD_TIER = 30
GUIDELINE_COUNT_FORCE_STANDARD_REASONING = 50

# Tier and reasoning level orderings (for comparison)
TIER_ORDER = {"fast": 0, "standard": 1, "advanced": 2}
REASONING_ORDER = {"none": 0, "standard": 1, "extended": 2}
TIER_NAMES = {v: k for k, v in TIER_ORDER.items()}
REASONING_NAMES = {v: k for k, v in REASONING_ORDER.items()}


def _aggregate_tier_and_reasoning_from_roles(
    all_roles: list[dict],
) -> tuple[int, int, list[str]]:
    """
    Extract maximum tier and reasoning from all roles.

    Returns:
        Tuple of (max_tier_index, max_reasoning_index, tier_driver_names)
    """
    max_tier = 0
    max_reasoning = 0
    tier_drivers: list[str] = []

    for role in all_roles:
        reqs = role.get("model_requirements", {})
        tier = TIER_ORDER.get(reqs.get("min_tier", "fast"), 0)
        reasoning = REASONING_ORDER.get(reqs.get("reasoning", "none"), 0)

        if tier > max_tier:
            max_tier = tier
            tier_drivers = [role.get("name", "?")]
        elif tier == max_tier and tier > 0:
            tier_drivers.append(role.get("name", "?"))

        max_reasoning = max(max_reasoning, reasoning)

    return max_tier, max_reasoning, tier_drivers


def _apply_guideline_count_tier_bumps(
    guideline_count: int,
    max_tier: int,
    max_reasoning: int,
    tier_drivers: list[str],
) -> tuple[int, int, list[str]]:
    """
    Bump tier/reasoning based on guideline count thresholds.

    Returns:
        Updated (max_tier, max_reasoning, tier_drivers)
    """
    if (
        guideline_count > GUIDELINE_COUNT_FORCE_STANDARD_TIER
        and max_tier < TIER_ORDER["standard"]
    ):
        max_tier = TIER_ORDER["standard"]
        tier_drivers = [f"{guideline_count} guidelines in composed output"]

    if (
        guideline_count > GUIDELINE_COUNT_FORCE_STANDARD_REASONING
        and max_reasoning < REASONING_ORDER["standard"]
    ):
        max_reasoning = REASONING_ORDER["standard"]

    return max_tier, max_reasoning, tier_drivers


def _apply_recipe_model_override(
    recipe: dict,
    max_tier: int,
    max_reasoning: int,
) -> tuple[int, int, str | None]:
    """
    Apply recipe-level model_recommendation override.

    Returns:
        Tuple of (max_tier, max_reasoning, override_rationale_or_none)
    """
    override = recipe.get("model_recommendation")
    if not override:
        return max_tier, max_reasoning, None

    if "min_tier" in override:
        max_tier = TIER_ORDER.get(override["min_tier"], max_tier)
    if "reasoning" in override:
        max_reasoning = REASONING_ORDER.get(override["reasoning"], max_reasoning)

    rationale = override.get("rationale", "")
    return max_tier, max_reasoning, rationale


def _generate_model_requirement_rationale(
    role_count: int,
    guideline_count: int,
    tool_count: int,
    tier_drivers: list[str],
) -> str:
    """Generate rationale string describing why certain tier/reasoning was chosen."""
    parts = []
    if role_count > 1:
        parts.append(f"{role_count} composed roles")
    parts.append(f"{guideline_count} guidelines")
    if tool_count > 0:
        parts.append(f"{tool_count} tools")
    if tier_drivers:
        parts.append(f"tier set by {', '.join(tier_drivers)}")
    return "; ".join(parts)


def aggregate_model_requirements(
    all_roles: list[dict],
    composed: dict,
    recipe: dict,
) -> dict:
    """
    Aggregate model requirements from roles and apply recipe-level overrides.

    Computes minimum model tier and reasoning level based on:
    1. Role-level requirements
    2. Guideline count thresholds
    3. Recipe-level overrides

    Args:
        all_roles: List of all roles being composed (compose + mixin)
        composed: The composed role dictionary
        recipe: Recipe dictionary (may contain model_recommendation override)

    Returns:
        Dict with keys: min_tier, reasoning, rationale
    """
    # Step 1: Aggregate from roles
    max_tier, max_reasoning, tier_drivers = _aggregate_tier_and_reasoning_from_roles(
        all_roles
    )

    # Step 2: Count-based tier bumps
    guideline_count = len(composed.get("guidelines", []))
    tool_count = len(composed.get("tools", []))
    role_count = len(all_roles)

    max_tier, max_reasoning, tier_drivers = _apply_guideline_count_tier_bumps(
        guideline_count, max_tier, max_reasoning, tier_drivers
    )

    # Step 3: Recipe override
    max_tier, max_reasoning, override_rationale = _apply_recipe_model_override(
        recipe, max_tier, max_reasoning
    )

    # Step 4: Generate rationale
    if override_rationale:
        rationale = override_rationale
    else:
        rationale = _generate_model_requirement_rationale(
            role_count, guideline_count, tool_count, tier_drivers
        )

    return {
        "min_tier": TIER_NAMES[max_tier],
        "reasoning": REASONING_NAMES[max_reasoning],
        "rationale": rationale,
    }

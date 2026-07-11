"""List command - display available roles and recipes with pattern filtering."""

from __future__ import annotations

import argparse
import fnmatch

from generator.cli.commands._helpers import get_base_dir
from generator.loader import list_recipes, list_roles


def _normalize_patterns(patterns: list[str] | None) -> list[str]:
    """Normalize pattern list, converting None/empty to ['*'] and 'all' to '*'.

    Returns:
        List of normalized patterns
    """
    if not patterns:
        return ["*"]
    return ["*" if p == "all" else p for p in patterns]


def _filter_by_patterns(items: list[dict], patterns: list[str]) -> list[dict]:
    """Filter items by matching name against patterns (case-insensitive).

    Args:
        items: List of dicts with 'name' key
        patterns: List of fnmatch patterns

    Returns:
        Filtered list of items
    """
    if patterns == ["*"]:
        return items

    filtered = []
    for item in items:
        item_name_lower = item["name"].lower()
        for pattern in patterns:
            pattern_lower = pattern.lower()
            if fnmatch.fnmatch(item_name_lower, pattern_lower):
                filtered.append(item)
                break  # Don't add the same item multiple times
    return filtered


def _print_roles(roles: list[dict]) -> None:
    """Print roles grouped by type with count.

    Max 15 lines: header (2) + type headers + role lines + footer (2)
    """
    print("ROLES")
    print("=" * 60)
    current_type = None
    for r in roles:
        if r["type"] != current_type:
            current_type = r["type"]
            print(f"\n  [{current_type}]")
        print(f"    {r['name']:35s} {r['path']}")
    print(f"\n  Total: {len(roles)} roles")


def _print_recipes(recipes: list[dict]) -> None:
    """Print recipes with composition and mixins, plus count.

    Max 15 lines: header (2) + recipe lines + footer (2)
    """
    print("RECIPES")
    print("=" * 60)
    for r in recipes:
        compose_str = " + ".join(c.split("/")[-1] for c in r["compose"])
        mixin_str = ""
        if r["mixins"]:
            mixin_str = " [+" + ", ".join(m.split("/")[-1] for m in r["mixins"]) + "]"
        print(f"  {r['name']:40s} {compose_str}{mixin_str}")
    print(f"\n  Total: {len(recipes)} recipes")


def cmd_list(args: argparse.Namespace) -> int:
    """List roles and/or recipes with optional pattern filtering.

    Args:
        args: Parsed command-line arguments with:
            - roles: Whether to show roles
            - recipes: Whether to show recipes
            - patterns: Optional list of fnmatch patterns

    Returns:
        Exit code (always 0)
    """
    base_dir = get_base_dir()
    show_roles = args.roles or not args.recipes
    show_recipes = args.recipes or not args.roles

    # Normalize patterns
    patterns = _normalize_patterns(args.patterns)

    if show_roles:
        roles = list_roles(base_dir)
        roles = _filter_by_patterns(roles, patterns)
        _print_roles(roles)

    if show_roles and show_recipes:
        print()

    if show_recipes:
        recipes = list_recipes(base_dir)
        recipes = _filter_by_patterns(recipes, patterns)
        _print_recipes(recipes)

    return 0

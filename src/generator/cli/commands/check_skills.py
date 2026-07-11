"""Check skills command - identify stale skills needing updates."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from generator.cli.commands._helpers import REPO_ROOT, resolve_install_target
from generator.loader import list_recipes, load_recipe
from generator.paths import get_skill_install_path
from generator.skill_updater import check_stale_skills


def _resolve_formats_to_check(args: argparse.Namespace) -> list[str]:
    """Determine which formats to check based on args.

    Args:
        args: Namespace with optional format attribute

    Returns:
        List of format names to check
    """
    if hasattr(args, "format") and args.format:
        return [args.format]
    return ["copilot", "claude", "cursor", "cline"]


def _load_all_recipes() -> dict[str, Any]:
    """Load all recipes from the repository.

    Returns:
        Dictionary mapping recipe name to recipe data
    """
    all_recipes = {}
    for recipe_info in list_recipes(base_dir=REPO_ROOT):
        recipe_name = recipe_info["name"]
        recipe = load_recipe(recipe_name, base_dir=REPO_ROOT)
        all_recipes[recipe_name] = recipe
    return all_recipes


def _get_skills_base_dir(fmt: str, target: Any) -> Path | None:
    """Get skill base directory for a format."""
    dummy_path = get_skill_install_path(fmt, "dummy", workspace=False, target=target)
    skills_base_dir = dummy_path.parent
    return skills_base_dir if skills_base_dir.exists() else None


def _check_format_stale_skills(
    fmt: str, skills_base_dir: Path, all_recipes: dict[str, Any]
) -> list[dict[str, Any]]:
    """Check for stale skills in one format."""
    stale_skills = check_stale_skills(skills_base_dir, all_recipes)
    for skill in stale_skills:
        skill["format"] = fmt
    return stale_skills


def _collect_stale_skills(
    formats: list[str], target: Any, all_recipes: dict[str, Any]
) -> list[dict[str, Any]]:
    """Check for stale skills across all formats."""
    all_stale = []
    for fmt in formats:
        skills_base_dir = _get_skills_base_dir(fmt, target)
        if skills_base_dir:
            stale_skills = _check_format_stale_skills(fmt, skills_base_dir, all_recipes)
            all_stale.extend(stale_skills)
    return all_stale


def _print_skill_details(skill: dict[str, Any]) -> None:
    """Print details for one stale skill."""
    print(f"  {skill['skill_name']} ({skill['format']})")
    print(f"    Reason: {skill['reason']}")
    print(f"    Source recipes: {', '.join(skill['source_recipes'])}")
    print(f"    Path: {skill['skill_dir']}")
    print()


def _display_stale_results(stale_skills: list[dict[str, Any]]) -> int:
    """Display stale skills results and return exit code."""
    if not stale_skills:
        print("✓ All skills are up to date!")
        return 0

    print(f"Found {len(stale_skills)} stale skill(s):\n")
    for skill in stale_skills:
        _print_skill_details(skill)

    print("To update: personetta update-skill <name> -f <format>")
    print("To update all: personetta update-skill --all")
    return 1


def cmd_check_skills(args: argparse.Namespace) -> int:
    """Check for stale skills (Phase 7e)."""
    target = resolve_install_target(args.target if hasattr(args, "target") else None)
    formats_to_check = _resolve_formats_to_check(args)
    all_recipes = _load_all_recipes()
    all_stale = _collect_stale_skills(formats_to_check, target, all_recipes)
    return _display_stale_results(all_stale)

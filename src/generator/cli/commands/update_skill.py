"""Update skill command - update skill(s) from latest recipes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from generator.cli.commands._helpers import (
    REPO_ROOT,
    resolve_install_target,
)
from generator.loader import (
    list_recipes,
    load_recipe,
)
from generator.paths import get_skill_install_path
from generator.skill_catalog import update_catalog_entry
from generator.skill_updater import (
    check_stale_skills,
    update_all_stale_skills,
    update_skill,
)


def _validate_update_args(args: argparse.Namespace) -> int | None:
    """Validate update command arguments.

    Args:
        args: Parsed arguments

    Returns:
        Exit code if validation fails, None if valid
    """
    if not args.all and not args.name:
        print("Error: Must provide skill name or use --all", file=sys.stderr)
        return 1

    if args.name and not args.format:
        print("Error: --format required when updating specific skill", file=sys.stderr)
        return 1

    return None


def _load_all_current_recipes() -> dict[str, dict]:
    """Load all current recipes from repository.

    Returns:
        Dictionary mapping recipe names to recipe dicts
    """
    all_recipes = {}
    for recipe_info in list_recipes(base_dir=REPO_ROOT):
        recipe_name = recipe_info["name"]
        recipe = load_recipe(recipe_name, base_dir=REPO_ROOT)
        all_recipes[recipe_name] = recipe
    return all_recipes


def _check_and_confirm_stale_updates(
    stale_skills: list[dict],
    fmt: str,
    force: bool,
    whatif: bool,
) -> bool:
    """Check stale skills and confirm updates.

    Args:
        stale_skills: List of stale skill dicts
        fmt: Format name (copilot, claude, etc.)
        force: Skip confirmation if True
        whatif: Dry-run mode if True

    Returns:
        True if should proceed with update, False otherwise
    """
    if whatif:
        print(f"\n[{fmt.upper()}] Would update {len(stale_skills)} skill(s):")
        for skill in stale_skills:
            print(f"  - {skill['skill_name']}: {skill['reason']}")
        return False

    if not force:
        print(f"\n[{fmt.upper()}] Found {len(stale_skills)} stale skill(s):")
        for skill in stale_skills:
            print(f"  - {skill['skill_name']}: {skill['reason']}")

        response = input(f"\nUpdate {len(stale_skills)} skill(s)? [y/N]: ")
        if response.lower() not in ["y", "yes"]:
            print("Cancelled.")
            return False

    return True


def _update_all_formats(
    formats: list[str],
    target: Path,
    all_recipes: dict[str, dict],
    whatif: bool,
    force: bool,
) -> int:
    """Update all stale skills across formats.

    Args:
        formats: List of format names to update
        target: Install target directory
        all_recipes: All available recipes
        whatif: Dry-run mode
        force: Skip confirmation

    Returns:
        Total number of skills updated
    """
    total_updated = 0

    for fmt in formats:
        # Determine skill base directory
        dummy_path = get_skill_install_path(fmt, "dummy", workspace=False, target=target)
        skills_base_dir = dummy_path.parent

        if not skills_base_dir.exists():
            continue

        # Check for stale skills
        stale_skills = check_stale_skills(skills_base_dir, all_recipes)

        if not stale_skills:
            continue

        # Confirm or whatif
        should_proceed = _check_and_confirm_stale_updates(
            stale_skills, fmt, force, whatif
        )
        if not should_proceed:
            continue

        # Update all stale skills
        updated = update_all_stale_skills(skills_base_dir, all_recipes)
        total_updated += updated

        print(f"[{fmt.upper()}] Updated {updated} skill(s)")

        # Update catalog entries
        for skill in stale_skills:
            update_catalog_entry(skill["skill_name"], fmt, skill["skill_dir"])

    return total_updated


def _load_skill_metadata(skill_dir: Path) -> tuple[list[str] | None, int]:
    """Load skill metadata from directory.

    Args:
        skill_dir: Skill directory path

    Returns:
        Tuple of (recipe_names list or None, exit_code)
    """
    metadata_file = skill_dir / ".skill-metadata.json"

    if not metadata_file.exists():
        print("Error: Skill metadata not found (old skill format?)", file=sys.stderr)
        return None, 1

    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    recipe_names = [r["name"] for r in metadata.get("source_recipes", [])]

    if not recipe_names:
        print("Error: No source recipes in metadata", file=sys.stderr)
        return None, 1

    return recipe_names, 0


def _load_recipes_from_names(
    recipe_names: list[str],
    all_recipes: dict[str, dict],
) -> tuple[list[dict] | None, int]:
    """Load recipe dicts from names.

    Args:
        recipe_names: List of recipe names
        all_recipes: All available recipes dict

    Returns:
        Tuple of (recipe list or None, exit_code)
    """
    recipes = []
    for recipe_name in recipe_names:
        if recipe_name not in all_recipes:
            print(f"Warning: Recipe '{recipe_name}' not found, skipping", file=sys.stderr)
            continue
        recipes.append(all_recipes[recipe_name])

    if not recipes:
        print("Error: No valid recipes found", file=sys.stderr)
        return None, 1

    return recipes, 0


def _update_single_skill_impl(
    skill_name: str,
    skill_dir: Path,
    fmt: str,
    all_recipes: dict[str, dict],
    whatif: bool,
) -> int:
    """Update a single skill.

    Args:
        skill_name: Skill name
        skill_dir: Skill directory
        fmt: Format name
        all_recipes: All available recipes
        whatif: Dry-run mode

    Returns:
        Exit code (0 = success)
    """
    # Load metadata
    recipe_names, exit_code = _load_skill_metadata(skill_dir)
    if exit_code != 0:
        return exit_code

    # At this point, recipe_names is guaranteed to be a list (not None) because exit_code == 0
    assert recipe_names is not None

    # Load recipes
    recipes, exit_code = _load_recipes_from_names(recipe_names, all_recipes)
    if exit_code != 0:
        return exit_code

    # At this point, recipes is guaranteed to be a list (not None) because exit_code == 0
    assert recipes is not None

    # Handle whatif
    if whatif:
        print(
            f"[WHATIF] Would update skill '{skill_name}' from recipes: {', '.join(recipe_names)}"
        )
        return 0

    # Update skill
    print(f"Updating skill '{skill_name}'...")
    success = update_skill(skill_dir, recipes, fmt)

    if not success:
        print("Error: Failed to update skill", file=sys.stderr)
        return 1

    # Update catalog
    update_catalog_entry(skill_name, fmt, skill_dir)

    print(f"✓ Updated skill: {skill_name}")
    print(f"  Path: {skill_dir}")

    return 0


def cmd_update_skill(args: argparse.Namespace) -> int:
    """Update skill(s) from latest recipes (Phase 7e).

    Args:
        args: Namespace with name (optional), format, all (bool), force (bool), whatif (bool)

    Returns:
        Exit code (0 = success)
    """
    # Resolve target
    target = resolve_install_target(args.target if hasattr(args, "target") else None)

    # Validate arguments
    exit_code = _validate_update_args(args)
    if exit_code is not None:
        return exit_code

    # Load all current recipes
    all_recipes = _load_all_current_recipes()

    # Handle --all flag
    if args.all:
        formats_to_update = (
            [args.format] if args.format else ["copilot", "claude", "cursor", "cline"]
        )

        total_updated = _update_all_formats(
            formats_to_update,
            target,
            all_recipes,
            args.whatif,
            args.force,
        )

        if args.whatif:
            print(f"\n[WHATIF] Would update {total_updated} total skill(s)")
        else:
            print(f"\n✓ Updated {total_updated} total skill(s)")

        return 0

    # Update specific skill
    skill_dir = get_skill_install_path(
        args.format, args.name, workspace=False, target=target
    )

    if not skill_dir.exists():
        print(f"Error: Skill '{args.name}' not found at {skill_dir}", file=sys.stderr)
        return 1

    return _update_single_skill_impl(
        args.name,
        skill_dir,
        args.format,
        all_recipes,
        args.whatif,
    )

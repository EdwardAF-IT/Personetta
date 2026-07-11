"""Skill command - generate executable skill from recipe(s)."""

from __future__ import annotations

import argparse
import fnmatch
import shutil
import sys
from pathlib import Path

from generator.cli.commands._helpers import (
    get_base_dir,
    normalize_skill_name,
    resolve_install_target,
    validate_skill_name,
)
from generator.loader import (
    load_merge_config,
    load_recipe,
    load_recipe_roles,
    list_recipes,
)
from generator.merger import compose_recipe
from generator.paths import get_skill_install_path
from generator.skills import SkillGenerator


def _match_recipes_for_skill(patterns: list[str], all_recipes: list[dict]) -> list[dict]:
    """Match recipes by patterns (case-insensitive).

    Args:
        patterns: Recipe name patterns (glob-style)
        all_recipes: List of all available recipes

    Returns:
        List of matched recipe dicts
    """
    matched = []
    for recipe in all_recipes:
        recipe_name_lower = recipe["name"].lower()
        for pattern in patterns:
            pattern_lower = pattern.lower()
            if fnmatch.fnmatch(recipe_name_lower, pattern_lower):
                matched.append(recipe)
                break  # Don't add the same recipe multiple times
    return matched


def _validate_and_normalize_skill_name(original_name: str) -> tuple[str | None, int]:
    """Normalize and validate skill name.

    Args:
        original_name: User-provided skill name

    Returns:
        Tuple of (normalized_name or None, exit_code)
    """
    normalized_name = normalize_skill_name(original_name)

    if normalized_name != original_name:
        print(f"[INFO] Skill name normalized: '{original_name}' -> '{normalized_name}'")

    if not validate_skill_name(normalized_name):
        print(
            f"[ERROR] Invalid skill name '{original_name}' (normalized: '{normalized_name}')",
            file=sys.stderr,
        )
        print(
            "Skill names must be lowercase alphanumeric with hyphens, "
            "1-64 characters, and start/end with alphanumeric.",
            file=sys.stderr,
        )
        return None, 1

    return normalized_name, 0


def _print_whatif_skill(
    skill_name: str,
    matched_recipes: list[dict],
    skill_dir: Path,
    format_name: str,
) -> None:
    """Print whatif output for skill generation.

    Args:
        skill_name: Normalized skill name
        matched_recipes: List of matched recipe dicts
        skill_dir: Target skill directory
        format_name: Output format (copilot, claude, etc.)
    """
    recipe_names = [r["name"] for r in matched_recipes]

    if len(matched_recipes) > 1:
        print(
            f"[WHATIF] Would generate skill '{skill_name}' from {len(matched_recipes)} recipes:"
        )
        for recipe_name in recipe_names:
            print(f"  - {recipe_name}")
    else:
        print(
            f"[WHATIF] Would generate skill '{skill_name}' from recipe '{recipe_names[0]}'"
        )

    print(f"  Format: {format_name}")
    print(f"  Location: {skill_dir}")
    print("  Files that would be created:")
    print(f"    {skill_dir / 'SKILL.md'}")
    print(f"    {skill_dir / 'README.md'}")

    if len(matched_recipes) > 1:
        for recipe_name in recipe_names:
            print(
                f"    {skill_dir / 'references' / f'{recipe_name}-criteria.md'} (if guidelines)"
            )
    else:
        print(
            f"    {skill_dir / 'references' / 'criteria.md'} (if recipe has guidelines)"
        )

    print(
        f"    {skill_dir / 'references' / 'checklist.md'} (if recipe(s) have verification)"
    )
    print("\nNo files created (dry-run mode).")


def _check_and_confirm_overwrite(skill_dir: Path, skill_name: str, force: bool) -> int:
    """Check if skill exists and confirm overwrite.

    Args:
        skill_dir: Target skill directory
        skill_name: Skill name
        force: Whether to force overwrite without confirmation

    Returns:
        Exit code (0 = continue, 1 = cancel)
    """
    if not skill_dir.exists():
        return 0

    if not force:
        print(f"WARNING: Skill '{skill_name}' already exists at:")
        print(f"  {skill_dir}")
        print()
        try:
            response = input("Overwrite existing skill? [y/N]: ").strip().lower()
            if response not in ("y", "yes"):
                print("Cancelled.")
                return 1
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            return 1

    print("Removing existing skill directory...")
    shutil.rmtree(skill_dir)
    return 0


def _load_and_compose_recipes(matched_recipes: list[dict], base_dir: Path) -> list[dict]:
    """Load and compose all matched recipes.

    Args:
        matched_recipes: List of matched recipe dicts
        base_dir: Base directory for recipes

    Returns:
        List of composed recipe dicts
    """
    composed_recipes = []
    merge_config = load_merge_config(base_dir)

    for recipe_data in matched_recipes:
        recipe_name = recipe_data["name"]
        print(f"Loading recipe '{recipe_name}'...")

        recipe_dict = load_recipe(recipe_name, base_dir)
        compose_roles, mixin_roles = load_recipe_roles(recipe_dict, base_dir)
        composed_recipe, warnings = compose_recipe(
            recipe_dict, compose_roles, mixin_roles, merge_config
        )

        # Print any merge warnings
        for warning in warnings:
            if warning.is_error:
                print(f"[ERROR] {warning.message}", file=sys.stderr)
            elif warning.is_warning:
                print(f"[WARNING] {warning.message}", file=sys.stderr)

        composed_recipes.append(composed_recipe)

    return composed_recipes


def _generate_skill_output(
    composed_recipes: list[dict],
    format_name: str,
    skill_name: str,
    skill_dir: Path,
    base_dir: Path,
) -> int:
    """Generate skill using SkillGenerator.

    Args:
        composed_recipes: List of composed recipe dicts
        format_name: Output format
        skill_name: Skill name
        skill_dir: Target skill directory
        base_dir: Base directory for metadata

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    print(f"Generating skill '{skill_name}'...")
    generator = SkillGenerator()

    try:
        # Pass single recipe or list based on count
        if len(composed_recipes) == 1:
            generator.generate(
                composed_recipes[0], format_name, skill_name, skill_dir, base_dir
            )
        else:
            generator.generate(
                composed_recipes, format_name, skill_name, skill_dir, base_dir
            )
    except Exception as exc:
        print(f"[ERROR] Failed to generate skill: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    return 0


def _print_skill_success(skill_name: str, skill_dir: Path) -> None:
    """Print success message and list generated files.

    Args:
        skill_name: Skill name
        skill_dir: Target skill directory
    """
    print(f"\nSkill '{skill_name}' generated successfully!")
    print(f"Location: {skill_dir}")
    print("\nGenerated files:")

    for file_path in sorted(skill_dir.rglob("*")):
        if file_path.is_file():
            relative = file_path.relative_to(skill_dir)
            print(f"  {relative}")

    print(f"\nSkill is ready to use as: /{skill_name}")


def cmd_skill(args: argparse.Namespace) -> int:
    """Generate executable skill from recipe(s).

    Phase 6: Supports multi-recipe composition.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    base_dir = get_base_dir()
    target = resolve_install_target(args.target)

    # Get all recipes
    all_recipes = list_recipes(base_dir)

    # Match recipes by patterns
    matched_recipes = _match_recipes_for_skill(args.patterns, all_recipes)

    if not matched_recipes:
        print(f"No recipes matched patterns: {', '.join(args.patterns)}", file=sys.stderr)
        print("\nUse 'personetta list' to see available recipes.", file=sys.stderr)
        return 1

    # Print info for multiple recipes
    recipe_names = [r["name"] for r in matched_recipes]
    if len(matched_recipes) > 1:
        print(
            f"[INFO] Combining {len(matched_recipes)} recipes: {', '.join(recipe_names)}"
        )

    # Normalize and validate skill name
    skill_name, exit_code = _validate_and_normalize_skill_name(args.name)
    if exit_code != 0:
        return exit_code

    # At this point, skill_name is guaranteed to be str (not None) because exit_code == 0
    assert skill_name is not None

    # Determine workspace install
    workspace_flag = getattr(args, "workspace", False)
    is_workspace = workspace_flag or (target != Path.home())

    # Determine install path
    skill_dir = get_skill_install_path(args.format, skill_name, is_workspace, target)

    # Handle --whatif mode
    if getattr(args, "whatif", False):
        _print_whatif_skill(skill_name, matched_recipes, skill_dir, args.format)
        return 0

    # Check if skill already exists and confirm overwrite
    exit_code = _check_and_confirm_overwrite(skill_dir, skill_name, args.force)
    if exit_code != 0:
        return exit_code

    # Load and compose all recipes
    composed_recipes = _load_and_compose_recipes(matched_recipes, base_dir)

    # Generate skill
    exit_code = _generate_skill_output(
        composed_recipes, args.format, skill_name, skill_dir, base_dir
    )
    if exit_code != 0:
        return exit_code

    # Print success
    _print_skill_success(skill_name, skill_dir)

    return 0

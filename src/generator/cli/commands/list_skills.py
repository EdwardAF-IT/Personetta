"""List skills command - show installed skills by format."""

from __future__ import annotations

import argparse
from pathlib import Path


def _refresh_catalog_if_requested(args: argparse.Namespace) -> None:
    """Refresh skill catalog if --refresh flag is set."""
    from generator.skill_catalog import refresh_catalog, refresh_all_catalogs

    if not args.refresh:
        return

    print("Refreshing catalog...")
    if args.format:
        refresh_catalog(args.format)
        print(f"Catalog refreshed for {args.format}.")
    else:
        refresh_all_catalogs()
        print("Catalog refreshed for all formats.")
    print()


def _get_formats_to_show(args: argparse.Namespace) -> list[str]:
    """Determine which formats to display based on args."""
    if args.format:
        return [args.format]
    return ["copilot", "claude", "cursor", "cline"]


def _count_total_skills(catalog: dict, formats: list[str]) -> int:
    """Count total skills across specified formats."""
    total = 0
    for fmt in formats:
        if fmt in catalog.get("skills", {}):
            total += len(catalog["skills"][fmt])
    return total


def _print_skill_header(total_skills: int, catalog_path: Path, catalog: dict) -> None:
    """Print header with skill count and catalog info."""
    print(f"Installed Skills ({total_skills} total):")
    print(f"Catalog: {catalog_path}")
    print(f"Last updated: {catalog.get('last_updated', 'unknown')}")
    print()


def _format_description(desc: str, max_length: int = 80) -> str:
    """Truncate description if too long."""
    if len(desc) > max_length:
        return desc[: max_length - 3] + "..."
    return desc


def _print_skill_details(skill_info: dict) -> None:
    """Print skill details (recipes, scripts, path)."""
    # Source recipes
    recipes = skill_info.get("source_recipes", [])
    if recipes:
        print(f"    Recipes: {', '.join(recipes)}")

    # Scripts
    if skill_info.get("has_scripts"):
        count = skill_info.get("script_count", 0)
        print(f"    Scripts: {count} bundled")

    # Path
    print(f"    Path: {skill_info.get('path', 'unknown')}")


def _print_skill_info(skill_name: str, skill_info: dict) -> None:
    """Print formatted information for a single skill."""
    print(f"  {skill_name}")
    desc = skill_info.get("description", "No description")
    print(f"    {_format_description(desc)}")
    _print_skill_details(skill_info)
    print()


def _print_skills_for_format(fmt: str, skills: dict) -> None:
    """Print all skills for a specific format."""
    print(f"== {fmt.upper()} ==")
    print()

    for skill_name, skill_info in sorted(skills.items()):
        _print_skill_info(skill_name, skill_info)


def cmd_list_skills(args: argparse.Namespace) -> int:
    """List installed skills from catalog (Phase 7d).

    Args:
        args: Namespace with format (optional) and refresh (bool)

    Returns:
        Exit code (0 = success)
    """
    from generator.skill_catalog import load_catalog, get_catalog_path

    # Refresh catalog if requested
    _refresh_catalog_if_requested(args)

    # Load catalog
    catalog_path = get_catalog_path()
    catalog = load_catalog(catalog_path)

    # Filter by format if specified
    formats_to_show = _get_formats_to_show(args)

    # Count total skills
    total_skills = _count_total_skills(catalog, formats_to_show)

    if total_skills == 0:
        print("No skills found.")
        if not args.refresh:
            print("Tip: Use --refresh to scan skill directories")
        return 0

    # Display skills
    _print_skill_header(total_skills, catalog_path, catalog)

    for fmt in formats_to_show:
        if fmt not in catalog.get("skills", {}) or not catalog["skills"][fmt]:
            continue
        _print_skills_for_format(fmt, catalog["skills"][fmt])

    return 0

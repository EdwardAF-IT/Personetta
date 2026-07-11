"""Remove skill command - delete installed skill from system."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def _get_skill_directory(skill_name: str, format_name: str, base_dir: Path) -> Path:
    """Get skill directory path."""
    from generator.paths import get_skill_install_path

    return get_skill_install_path(
        format_name,
        skill_name,
        workspace=False,
        target=base_dir,
    )


def _is_skill_in_catalog(skill_name: str, format_name: str, base_dir: Path) -> bool:
    """Check if skill exists in catalog."""
    from generator.skill_catalog import load_catalog, get_catalog_path

    catalog_path = get_catalog_path(base_dir)
    catalog = load_catalog(catalog_path)
    return (
        format_name in catalog.get("skills", {})
        and skill_name in catalog["skills"][format_name]
    )


def _check_skill_exists(
    skill_name: str, format_name: str, base_dir: Path
) -> tuple[bool, bool, Path]:
    """Check if skill exists in directory and/or catalog.

    Returns:
        Tuple of (dir_exists, catalog_exists, skill_dir)
    """
    skill_dir = _get_skill_directory(skill_name, format_name, base_dir)
    dir_exists = skill_dir.exists()
    catalog_exists = _is_skill_in_catalog(skill_name, format_name, base_dir)
    return dir_exists, catalog_exists, skill_dir


def _show_removal_plan(
    skill_name: str,
    format_name: str,
    dir_exists: bool,
    catalog_exists: bool,
    skill_dir: Path,
) -> None:
    """Print what will be removed."""
    print(f"Skill to remove: {skill_name} ({format_name})")
    if dir_exists:
        print(f"  Directory: {skill_dir}")
    if catalog_exists:
        print(f"  Catalog entry: {skill_name}")


def _confirm_removal(force: bool) -> bool:
    """Get user confirmation unless force flag is set.

    Returns:
        True if removal should proceed, False otherwise
    """
    if force:
        return True

    response = input("\nRemove this skill? [y/N]: ")
    if response.lower() not in ("y", "yes"):
        print("Removal cancelled.")
        return False

    return True


def _remove_skill_directory(skill_dir: Path) -> bool:
    """Remove skill directory from filesystem.

    Returns:
        True if successful, False otherwise
    """
    try:
        shutil.rmtree(skill_dir)
        print(f"✓ Removed directory: {skill_dir}")
        return True
    except OSError as e:
        print(f"Error: Failed to remove directory: {e}", file=sys.stderr)
        return False


def _remove_skill_catalog_entry(
    skill_name: str, format_name: str, base_dir: Path
) -> bool:
    """Remove skill from catalog.

    Returns:
        True if successful, False otherwise
    """
    from generator.skill_catalog import remove_skill_from_catalog

    if remove_skill_from_catalog(skill_name, format_name, base_dir):
        print(f"✓ Removed catalog entry: {skill_name}")
        return True
    else:
        print(
            f"Warning: Failed to remove catalog entry for '{skill_name}'",
            file=sys.stderr,
        )
        return False


def cmd_remove_skill(args: argparse.Namespace) -> int:
    """Remove installed skill (Phase 7f).

    Args:
        args: Namespace with skill_name, format, target (optional), and force (bool)

    Returns:
        Exit code (0 = success, 1 = error)
    """
    # Skills are always installed to user home (~/)
    base_dir = Path.home()

    # Check if skill exists (directory or catalog entry)
    dir_exists, catalog_exists, skill_dir = _check_skill_exists(
        args.skill_name, args.format, base_dir
    )

    # If neither exists, error
    if not dir_exists and not catalog_exists:
        print(
            f"Error: Skill '{args.skill_name}' not found for format '{args.format}'",
            file=sys.stderr,
        )
        return 1

    # Show what will be removed
    _show_removal_plan(
        args.skill_name, args.format, dir_exists, catalog_exists, skill_dir
    )

    # Confirm unless --force
    if not _confirm_removal(args.force):
        return 0

    # Remove directory if exists
    if dir_exists:
        if not _remove_skill_directory(skill_dir):
            return 1

    # Remove catalog entry if exists
    if catalog_exists:
        _remove_skill_catalog_entry(args.skill_name, args.format, base_dir)

    print(f"\nSkill '{args.skill_name}' removed successfully.")
    return 0

"""Clean skills command - remove orphaned skills and catalog entries."""

from __future__ import annotations

import argparse
from pathlib import Path


def _get_formats_to_clean(args: argparse.Namespace) -> list[str]:
    """Determine which formats to clean based on args."""
    if args.format:
        return [args.format]
    return ["copilot", "claude", "cursor", "cline"]


def _scan_format_for_orphans(fmt: str, base_dir: Path) -> dict:
    """Scan a single format for orphaned skills."""
    from generator.skill_catalog import scan_for_orphans, _get_skills_dir

    skills_dir = _get_skills_dir(fmt, base_dir)
    return scan_for_orphans(fmt, base_dir, skills_dir)


def _scan_all_formats_for_orphans(
    formats: list[str], base_dir: Path
) -> tuple[dict, int, int]:
    """Scan all formats for orphaned skills.

    Returns:
        Tuple of (all_orphans dict, total_orphaned_dirs, total_orphaned_entries)
    """
    all_orphans = {}
    total_orphaned_dirs = 0
    total_orphaned_entries = 0

    for fmt in formats:
        orphans = _scan_format_for_orphans(fmt, base_dir)
        if orphans["orphaned_directories"] or orphans["orphaned_entries"]:
            all_orphans[fmt] = orphans
            total_orphaned_dirs += len(orphans["orphaned_directories"])
            total_orphaned_entries += len(orphans["orphaned_entries"])

    return all_orphans, total_orphaned_dirs, total_orphaned_entries


def _print_orphaned_directories(fmt: str, orphaned_dirs: list) -> None:
    """Print orphaned directories for a format."""
    print(f"{fmt} - Orphaned directories (not in catalog):")
    for orphaned_dir in orphaned_dirs:
        print(f"  - {orphaned_dir.name}")


def _print_orphaned_entries(fmt: str, orphaned_entries: list) -> None:
    """Print orphaned catalog entries for a format."""
    print(f"{fmt} - Orphaned catalog entries (no directory):")
    for orphaned_entry in orphaned_entries:
        print(f"  - {orphaned_entry}")


def _print_orphans_summary(
    all_orphans: dict, total_dirs: int, total_entries: int
) -> None:
    """Print summary of all orphaned skills found."""
    print("Orphaned skills found:\n")

    for fmt, orphans in all_orphans.items():
        if orphans["orphaned_directories"]:
            _print_orphaned_directories(fmt, orphans["orphaned_directories"])

        if orphans["orphaned_entries"]:
            _print_orphaned_entries(fmt, orphans["orphaned_entries"])

        print()

    print(f"Total: {total_dirs} directories, {total_entries} entries\n")


def _confirm_cleanup(force: bool) -> bool:
    """Get user confirmation unless force flag is set.

    Returns:
        True if cleanup should proceed, False otherwise
    """
    if force:
        return True

    response = input("Clean these orphaned skills? [y/N]: ")
    if response.lower() not in ("y", "yes"):
        print("Cleanup cancelled.")
        return False

    return True


def _clean_format_orphans(fmt: str, base_dir: Path) -> dict:
    """Clean orphaned skills for a single format."""
    from generator.skill_catalog import clean_orphaned_skills, _get_skills_dir

    skills_dir = _get_skills_dir(fmt, base_dir)
    return clean_orphaned_skills(fmt, base_dir, skills_dir)


def _clean_all_orphans(
    formats: list[str], all_orphans: dict, base_dir: Path
) -> tuple[int, int]:
    """Clean orphaned skills for all formats.

    Returns:
        Tuple of (total_dirs_removed, total_entries_removed)
    """
    total_dirs_removed = 0
    total_entries_removed = 0

    for fmt in formats:
        if fmt not in all_orphans:
            continue

        result = _clean_format_orphans(fmt, base_dir)
        total_dirs_removed += result["directories_removed"]
        total_entries_removed += result["entries_removed"]

    return total_dirs_removed, total_entries_removed


def _print_cleanup_results(dirs_removed: int, entries_removed: int) -> None:
    """Print cleanup results summary."""
    print("\nCleaned successfully:")
    print(f"  Directories removed: {dirs_removed}")
    print(f"  Catalog entries removed: {entries_removed}")


def cmd_clean_skills(args: argparse.Namespace) -> int:
    """Clean orphaned skills and catalog entries (Phase 7f).

    Args:
        args: Namespace with format (optional) and force (bool)

    Returns:
        Exit code (0 = success)
    """
    base_dir = Path.home()

    # Determine formats to clean
    formats_to_clean = _get_formats_to_clean(args)

    # Scan for orphans across all formats
    all_orphans, total_orphaned_dirs, total_orphaned_entries = (
        _scan_all_formats_for_orphans(formats_to_clean, base_dir)
    )

    # If nothing to clean
    if not all_orphans:
        print("No orphaned skills found.")
        return 0

    # Show what will be cleaned
    _print_orphans_summary(all_orphans, total_orphaned_dirs, total_orphaned_entries)

    # Confirm unless --force
    if not _confirm_cleanup(args.force):
        return 0

    # Clean orphans for each format
    total_dirs_removed, total_entries_removed = _clean_all_orphans(
        formats_to_clean, all_orphans, base_dir
    )

    # Report results
    _print_cleanup_results(total_dirs_removed, total_entries_removed)

    return 0

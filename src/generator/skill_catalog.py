"""Skill catalog management for personetta (Phase 7d).

Maintains a searchable index of installed skills across all formats.
Supports auto-update on skill generation and manual catalog refresh.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from generator.constants import (
    COPILOT_DIR,
    CLAUDE_DIR,
    CURSOR_DIR,
    CLINE_DIR,
    SKILLS_SUBDIR,
    PERSONETTA_DIR,
)

# ============================================================================
# Catalog Structure and Path Resolution
# ============================================================================


def get_catalog_path(base_dir: Optional[Path] = None) -> Path:
    """Get path to skills catalog file.

    Args:
        base_dir: Base directory (defaults to user home)

    Returns:
        Path to skills-catalog.json
    """
    if base_dir is None:
        base_dir = Path.home()

    catalog_dir = base_dir / PERSONETTA_DIR
    catalog_dir.mkdir(parents=True, exist_ok=True)

    return catalog_dir / "skills-catalog.json"


def create_catalog() -> dict:
    """Create new empty catalog structure.

    Returns:
        Catalog dict with version, timestamp, and empty skills dict
    """
    return {
        "version": "1.0",
        "last_updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "skills": {},
    }


# ============================================================================
# Catalog Persistence
# ============================================================================


def save_catalog(catalog: dict, catalog_path: Path) -> None:
    """Save catalog to disk.

    Args:
        catalog: Catalog dict to save
        catalog_path: Path to catalog file
    """
    # Ensure parent directory exists
    catalog_path.parent.mkdir(parents=True, exist_ok=True)

    # Update timestamp
    catalog["last_updated"] = (
        datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )

    # Write JSON with formatting
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
        f.write("\n")  # Trailing newline


def load_catalog(catalog_path: Path) -> dict:
    """Load catalog from disk, creating new if missing or corrupt.

    Args:
        catalog_path: Path to catalog file

    Returns:
        Catalog dict
    """
    if not catalog_path.exists():
        return create_catalog()

    try:
        with open(catalog_path, encoding="utf-8") as f:
            catalog = json.load(f)

        # Validate structure
        if not isinstance(catalog, dict):
            raise ValueError("Catalog is not a dict")
        if "skills" not in catalog:
            raise ValueError("Catalog missing 'skills' key")

        return catalog

    except (json.JSONDecodeError, ValueError, OSError):
        # Corrupt or invalid file - return new catalog
        return create_catalog()


# ============================================================================
# Skill Directory Scanning
# ============================================================================


def _get_skills_dir(format_name: str, base_dir: Path) -> Path:
    """Get skills directory for a format.

    Args:
        format_name: Format (copilot, claude, cursor, cline)
        base_dir: Base directory

    Returns:
        Path to skills directory
    """
    format_dirs = {
        "copilot": COPILOT_DIR,
        "claude": CLAUDE_DIR,
        "cursor": CURSOR_DIR,
        "cline": CLINE_DIR,
    }

    format_dir = format_dirs.get(format_name, COPILOT_DIR)
    return base_dir / format_dir / SKILLS_SUBDIR


def _extract_skill_info(skill_dir: Path) -> Optional[dict]:
    """Extract skill information from directory.

    Args:
        skill_dir: Path to skill directory

    Returns:
        Skill info dict or None if invalid
    """
    # Must have metadata file
    metadata_file = skill_dir / ".skill-metadata.json"
    if not metadata_file.exists():
        return None

    try:
        with open(metadata_file, encoding="utf-8") as f:
            metadata = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    # Extract description from SKILL.md if present
    description = "No description available"
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        try:
            content = skill_md.read_text(encoding="utf-8")
            # Look for description in frontmatter or first paragraph
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("description:"):
                    description = line.split("description:", 1)[1].strip().strip("'\"")
                    break
                # First non-empty, non-heading line after frontmatter
                if (
                    i > 5
                    and line.strip()
                    and not line.startswith("#")
                    and not line.startswith("---")
                ):
                    description = line.strip()[:200]  # First 200 chars
                    break
        except OSError:
            pass

    # Count scripts
    scripts_dir = skill_dir / "scripts"
    script_count = 0
    has_scripts = False
    if scripts_dir.exists() and scripts_dir.is_dir():
        script_files = list(scripts_dir.glob("*"))
        script_count = len([f for f in script_files if f.is_file()])
        has_scripts = script_count > 0

    # Build entry
    return {
        "name": metadata.get("skill_name", skill_dir.name),
        "description": description,
        "path": str(skill_dir),
        "source_recipes": [r["name"] for r in metadata.get("source_recipes", [])],
        "generated_at": metadata.get("generated_at", "unknown"),
        "has_scripts": has_scripts,
        "script_count": script_count,
    }


def scan_all_skills(format_name: str, base_dir: Optional[Path] = None) -> dict:
    """Scan skills directory and return all skill entries.

    Args:
        format_name: Format to scan (copilot, claude, cursor, cline)
        base_dir: Base directory (defaults to user home)

    Returns:
        Dict of skill_name -> skill_info
    """
    if base_dir is None:
        base_dir = Path.home()

    skills_dir = _get_skills_dir(format_name, base_dir)

    if not skills_dir.exists():
        return {}

    skills = {}

    # Scan all subdirectories
    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue

        skill_info = _extract_skill_info(skill_dir)
        if skill_info:
            skills[skill_dir.name] = skill_info

    return skills


# ============================================================================
# Catalog Entry Management
# ============================================================================


def update_catalog_entry(
    skill_name: str,
    format_name: str,
    skill_dir: Path,
    catalog_path: Optional[Path] = None,
) -> None:
    """Update or add catalog entry for a skill.

    Args:
        skill_name: Name of the skill
        format_name: Format (copilot, claude, cursor, cline)
        skill_dir: Path to skill directory
        catalog_path: Path to catalog file (defaults to user catalog)
    """
    if catalog_path is None:
        catalog_path = get_catalog_path()

    # Load existing catalog
    catalog = load_catalog(catalog_path)

    # Extract skill info
    skill_info = _extract_skill_info(skill_dir)
    if not skill_info:
        # Invalid skill - skip silently
        return

    # Ensure format section exists
    if format_name not in catalog["skills"]:
        catalog["skills"][format_name] = {}

    # Update entry
    catalog["skills"][format_name][skill_name] = skill_info

    # Save catalog
    save_catalog(catalog, catalog_path)


def refresh_catalog(format_name: str, base_dir: Optional[Path] = None) -> None:
    """Refresh catalog by scanning all skills for a format.

    Args:
        format_name: Format to refresh (copilot, claude, cursor, cline)
        base_dir: Base directory (defaults to user home)
    """
    if base_dir is None:
        base_dir = Path.home()

    catalog_path = get_catalog_path(base_dir)
    catalog = load_catalog(catalog_path)

    # Scan all skills
    skills = scan_all_skills(format_name, base_dir)

    # Replace format section in catalog
    catalog["skills"][format_name] = skills

    # Save catalog
    save_catalog(catalog, catalog_path)


def refresh_all_catalogs(base_dir: Optional[Path] = None) -> None:
    """Refresh catalog for all formats.

    Args:
        base_dir: Base directory (defaults to user home)
    """
    for format_name in ["copilot", "claude", "cursor", "cline"]:
        refresh_catalog(format_name, base_dir)


# ============================================================================
# Catalog Entry Removal (Phase 7f)
# ============================================================================


def remove_skill_from_catalog(
    skill_name: str,
    format_name: str,
    base_dir: Optional[Path] = None,
) -> bool:
    """Remove skill entry from catalog.

    Args:
        skill_name: Name of skill to remove
        format_name: Format (copilot, claude, cursor, cline)
        base_dir: Base directory (defaults to user home)

    Returns:
        True if skill was removed, False if not found
    """
    if base_dir is None:
        base_dir = Path.home()

    catalog_path = get_catalog_path(base_dir)
    catalog = load_catalog(catalog_path)

    # Check if format exists
    if format_name not in catalog["skills"]:
        return False

    # Check if skill exists
    if skill_name not in catalog["skills"][format_name]:
        return False

    # Remove skill
    del catalog["skills"][format_name][skill_name]

    # Save catalog
    save_catalog(catalog, catalog_path)

    return True


# ============================================================================
# Orphan Detection and Cleanup (Phase 7f)
# ============================================================================


def scan_for_orphans(
    format_name: str,
    base_dir: Path,
    skills_dir: Path,
) -> dict:
    """Scan for orphaned skills and catalog entries.

    Args:
        format_name: Format to scan
        base_dir: Base directory
        skills_dir: Skills directory to scan

    Returns:
        Dict with orphaned_directories (list of Paths) and
        orphaned_entries (list of skill names)
    """
    orphans: dict[str, list] = {"orphaned_directories": [], "orphaned_entries": []}

    # Load catalog
    catalog_path = get_catalog_path(base_dir)
    catalog = load_catalog(catalog_path)

    # Get catalog entries for this format
    catalog_entries = catalog["skills"].get(format_name, {})
    catalog_skill_names = set(catalog_entries.keys())

    # Scan directory for skill directories
    if skills_dir.exists():
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            # Check if valid skill (has SKILL.md)
            if not (skill_dir / "SKILL.md").exists():
                continue

            skill_name = skill_dir.name

            # Check if in catalog
            if skill_name not in catalog_skill_names:
                orphans["orphaned_directories"].append(skill_dir)

    # Check catalog entries for missing directories
    for skill_name in catalog_skill_names:
        skill_path = Path(catalog_entries[skill_name].get("path", ""))

        if not skill_path.exists():
            orphans["orphaned_entries"].append(skill_name)

    return orphans


def clean_orphaned_skills(
    format_name: str,
    base_dir: Path,
    skills_dir: Path,
) -> dict:
    """Clean orphaned skills and catalog entries.

    Args:
        format_name: Format to clean
        base_dir: Base directory
        skills_dir: Skills directory

    Returns:
        Dict with directories_removed and entries_removed counts
    """
    import shutil

    result = {"directories_removed": 0, "entries_removed": 0}

    # Scan for orphans
    orphans = scan_for_orphans(format_name, base_dir, skills_dir)

    # Remove orphaned directories
    for orphaned_dir in orphans["orphaned_directories"]:
        try:
            shutil.rmtree(orphaned_dir)
            result["directories_removed"] += 1
        except OSError:
            # Skip if can't remove
            pass

    # Remove orphaned catalog entries
    for orphaned_entry in orphans["orphaned_entries"]:
        if remove_skill_from_catalog(orphaned_entry, format_name, base_dir):
            result["entries_removed"] += 1

    return result


# ============================================================================
# Simplified Management Functions (Phase 7f)
# ============================================================================


def remove_catalog_entry(
    skill_name: str,
    format_name: str,
    catalog_path: Path,
) -> None:
    """Remove skill entry from catalog (simplified interface).

    Args:
        skill_name: Name of skill to remove
        format_name: Format (copilot, claude, cursor, cline)
        catalog_path: Path to catalog file
    """
    catalog = load_catalog(catalog_path)

    # Check if format and skill exist
    if format_name in catalog["skills"]:
        if skill_name in catalog["skills"][format_name]:
            del catalog["skills"][format_name][skill_name]

    # Update timestamp and save
    catalog["last_updated"] = datetime.now(timezone.utc).isoformat()
    save_catalog(catalog, catalog_path)


def clean_orphaned_entries(
    format_name: str,
    catalog_path: Path,
) -> list[str]:
    """Clean orphaned catalog entries (simplified interface).

    Removes entries where skill directory doesn't exist.

    Args:
        format_name: Format to clean
        catalog_path: Path to catalog file

    Returns:
        List of removed skill names
    """
    catalog = load_catalog(catalog_path)
    removed: list[str] = []

    # Check if format exists
    if format_name not in catalog["skills"]:
        return removed

    # Find orphaned entries
    skills = catalog["skills"][format_name]
    for skill_name, skill_info in list(skills.items()):
        skill_path = Path(skill_info.get("path", ""))

        if not skill_path.exists():
            del catalog["skills"][format_name][skill_name]
            removed.append(skill_name)

    # Update timestamp and save if changes made
    if removed:
        catalog["last_updated"] = datetime.now(timezone.utc).isoformat()
        save_catalog(catalog, catalog_path)

    return removed

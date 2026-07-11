"""Skill metadata management for personetta.

Handles recipe versioning, hashing, and metadata generation for skills.
Phase 7a functionality extracted from skill_generator.py
"""

from __future__ import annotations

import hashlib
import json
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from generator.project_layout import get_project_root_from_file


def compute_recipe_hash(recipe: dict) -> str:
    """Compute SHA-256 hash of recipe content.

    Args:
        recipe: Recipe dictionary to hash

    Returns:
        Hash string in format "sha256:hexdigest"
    """
    recipe_json = _serialize_recipe(recipe)
    recipe_bytes = recipe_json.encode("utf-8")
    hash_obj = hashlib.sha256(recipe_bytes)
    return f"sha256:{hash_obj.hexdigest()}"


def _serialize_recipe(recipe: dict) -> str:
    """Serialize recipe to deterministic JSON.

    Args:
        recipe: Recipe dictionary

    Returns:
        JSON string with sorted keys
    """
    return json.dumps(recipe, sort_keys=True, ensure_ascii=False)


def get_personetta_version() -> str:
    """Get personetta version from pyproject.toml.

    Returns:
        Version string (e.g., "1.1.0")

    Raises:
        FileNotFoundError: If pyproject.toml not found
        KeyError: If version field missing
    """
    pyproject_path = _find_pyproject_toml()
    version = _read_version_from_toml(pyproject_path)
    return version


def _find_pyproject_toml() -> Path:
    """Find pyproject.toml using project layout.

    Returns:
        Path to pyproject.toml

    Raises:
        FileNotFoundError: If pyproject.toml not found
    """
    project_root = get_project_root_from_file(__file__)
    pyproject_path = project_root / "pyproject.toml"

    if not pyproject_path.exists():
        raise FileNotFoundError(f"pyproject.toml not found at {pyproject_path}")

    return pyproject_path


def _read_version_from_toml(pyproject_path: Path) -> str:
    """Read version from pyproject.toml.

    Args:
        pyproject_path: Path to pyproject.toml

    Returns:
        Version string

    Raises:
        KeyError: If version field missing
    """
    with open(pyproject_path, "rb") as f:
        pyproject_data = tomllib.load(f)

    try:
        return pyproject_data["project"]["version"]
    except KeyError:
        raise KeyError("Version not found in pyproject.toml [project] section")


def create_metadata(
    skill_name: str,
    recipes: list[dict],
    format: str,
    base_dir: Optional[Path] = None,
) -> dict:
    """Create skill metadata dictionary.

    Args:
        skill_name: Name of the skill
        recipes: List of recipe dictionaries
        format: Target format (copilot, claude, cursor, cline)
        base_dir: Base directory for recipe files

    Returns:
        Metadata dictionary
    """
    timestamp = _get_current_timestamp()
    version = _get_version_safely()
    source_recipes = _build_source_recipes(recipes, base_dir, timestamp)

    return {
        "skill_name": skill_name,
        "generated_at": timestamp,
        "personetta_version": version,
        "format": format,
        "source_recipes": source_recipes,
    }


def _get_current_timestamp() -> str:
    """Get current UTC timestamp in ISO 8601 format.

    Returns:
        Timestamp string
    """
    now = datetime.now(timezone.utc)
    return now.isoformat().replace("+00:00", "Z")


def _get_version_safely() -> str:
    """Get personetta version with fallback.

    Returns:
        Version string or "unknown"
    """
    try:
        return get_personetta_version()
    except (FileNotFoundError, KeyError):
        return "unknown"


def _build_source_recipes(
    recipes: list[dict],
    base_dir: Optional[Path],
    timestamp: str,
) -> list[dict]:
    """Build source recipe references.

    Args:
        recipes: List of recipe dictionaries
        base_dir: Base directory for recipe files
        timestamp: Fallback timestamp

    Returns:
        List of source recipe dictionaries
    """
    source_recipes = []
    for recipe in recipes:
        recipe_ref = _create_recipe_reference(recipe, base_dir, timestamp)
        source_recipes.append(recipe_ref)

    return source_recipes


def _create_recipe_reference(
    recipe: dict,
    base_dir: Optional[Path],
    timestamp: str,
) -> dict:
    """Create reference dict for a single recipe.

    Args:
        recipe: Recipe dictionary
        base_dir: Base directory for recipe files
        timestamp: Fallback timestamp

    Returns:
        Recipe reference dictionary
    """
    recipe_name = recipe.get("name", "unknown")
    content_hash = compute_recipe_hash(recipe)
    file_path, file_mtime = _resolve_file_info(recipe_name, base_dir, timestamp)

    return {
        "name": recipe_name,
        "file_path": file_path,
        "content_hash": content_hash,
        "file_mtime": file_mtime,
    }


def _resolve_file_info(
    recipe_name: str,
    base_dir: Optional[Path],
    fallback_timestamp: str,
) -> tuple[str, str]:
    """Resolve file path and mtime for recipe.

    Args:
        recipe_name: Name of the recipe
        base_dir: Base directory for recipe files
        fallback_timestamp: Timestamp to use if file not found

    Returns:
        Tuple of (file_path, file_mtime)
    """
    if base_dir:
        return _get_actual_file_info(recipe_name, base_dir, fallback_timestamp)
    else:
        return _get_placeholder_file_info(recipe_name, fallback_timestamp)


def _get_actual_file_info(
    recipe_name: str,
    base_dir: Path,
    fallback_timestamp: str,
) -> tuple[str, str]:
    """Get actual file info if file exists.

    Args:
        recipe_name: Name of the recipe
        base_dir: Base directory
        fallback_timestamp: Fallback if file missing

    Returns:
        Tuple of (file_path, file_mtime)
    """
    recipe_file = base_dir / f"{recipe_name}.yaml"

    if recipe_file.exists():
        mtime_timestamp = recipe_file.stat().st_mtime
        mtime_dt = datetime.fromtimestamp(mtime_timestamp, tz=timezone.utc)
        file_mtime = mtime_dt.isoformat().replace("+00:00", "Z")
        return str(recipe_file), file_mtime
    else:
        return _get_placeholder_file_info(recipe_name, fallback_timestamp)


def _get_placeholder_file_info(
    recipe_name: str,
    fallback_timestamp: str,
) -> tuple[str, str]:
    """Get placeholder file info.

    Args:
        recipe_name: Name of the recipe
        fallback_timestamp: Timestamp to use

    Returns:
        Tuple of (file_path, file_mtime)
    """
    file_path = f"recipes/{recipe_name}.yaml"
    return file_path, fallback_timestamp

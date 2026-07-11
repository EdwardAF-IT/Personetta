"""Shared helper functions for CLI commands."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from generator.cursor_personal_context_sync import maybe_sync_personal_context
from generator.installer import resolve_target
from generator.project_layout import get_project_root_from_file

# Repository root for roles/recipes
# Used by commands to find recipe files
REPO_ROOT = get_project_root_from_file(__file__)


def normalize_skill_name(name: str) -> str:
    """
    Normalize skill name to valid format.

    Transformations:
    - Convert to lowercase
    - Replace spaces with hyphens
    - Replace underscores with hyphens
    - Collapse multiple hyphens to single
    - Strip leading/trailing hyphens

    Args:
        name: Raw skill name from user input

    Returns:
        Normalized skill name

    Examples:
        >>> normalize_skill_name("Python Testing")
        'python-testing'
        >>> normalize_skill_name("code_review_python")
        'code-review-python'
        >>> normalize_skill_name("--Python--Testing--")
        'python-testing'
    """
    # Convert to lowercase
    normalized = name.lower()

    # Replace spaces and underscores with hyphens
    normalized = normalized.replace(" ", "-").replace("_", "-")

    # Collapse multiple hyphens to single hyphen
    normalized = re.sub(r"-+", "-", normalized)

    # Strip leading/trailing hyphens
    normalized = normalized.strip("-")

    return normalized


def validate_skill_name(name: str) -> bool:
    """
    Validate skill name after normalization.

    Valid skill names:
    - Lowercase alphanumeric + hyphens only
    - Must start and end with alphanumeric
    - Length: 1-64 characters
    - Pattern: ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$

    Args:
        name: Normalized skill name

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_skill_name("python-testing")
        True
        >>> validate_skill_name("test123")
        True
        >>> validate_skill_name("python@testing")
        False
        >>> validate_skill_name("-python")
        False
    """
    # Check length
    if not name or len(name) > 64:
        return False

    # Check pattern: lowercase alphanumeric + hyphens, must start/end with alphanumeric
    pattern = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$"
    return bool(re.match(pattern, name))


def emit_cursor_user_sync(target: Path) -> None:
    """Emit sync message for Cursor personal context."""
    ok, msg = maybe_sync_personal_context(target)
    if not msg:
        return
    if ok:
        print(msg)
    else:
        print(f"[WARNING] {msg}", file=sys.stderr)


def install_path_summary() -> str:
    """Return summary of install paths for all formats."""
    return (
        "~/.cursor/rules, ~/.personetta/cursor-recipes; "
        "~/.copilot/instructions, ~/.personetta/copilot-recipes; "
        "~/.claude/rules, ~/.personetta/claude-recipes; "
        "~/Documents/Cline/Rules, ~/.personetta/cline-recipes"
    )


def get_base_dir() -> Path:
    """
    Repository root for roles/recipes.

    Resolution order:
    1. PERSONETTA_BASE environment variable (for tests or alternate trees)
    2. Default: Use _REPO_ROOT (works for both dev and installed modes)
       - Dev mode: _REPO_ROOT points to repository root
       - Installed mode: _REPO_ROOT points to site-packages (recipes bundled there)
    """
    # Environment override
    override = os.environ.get("PERSONETTA_BASE")
    if override:
        return Path(override).resolve()

    # Use _REPO_ROOT - works in both dev and installed modes when recipes are bundled
    return REPO_ROOT


def resolve_install_target(target_args: list[str] | None) -> Path:
    """Root directory for --install / install (any format). Omitting --target means user-wide (global) install."""
    if target_args is None:
        return resolve_target(["global"])
    return resolve_target(target_args)

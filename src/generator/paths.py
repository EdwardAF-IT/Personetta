"""
Path resolution registry for format-specific directory paths.

Centralizes all path logic for Cursor, Copilot, Claude, and Cline installations,
eliminating duplication across layout files and installer.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from generator.constants import (
    CURSOR_DIR,
    COPILOT_DIR,
    CLAUDE_DIR,
    CURSOR_RULES_SUBDIR,
    COPILOT_INSTRUCTIONS_SUBDIR,
    CLAUDE_RULES_SUBDIR,
    CURSOR_RECIPES_SUBDIR,
    COPILOT_RECIPES_SUBDIR,
    CLAUDE_RECIPES_SUBDIR,
    CLINE_RECIPES_SUBDIR,
    PERSONETTA_DIR,
    FORMAT_CURSOR,
    FORMAT_COPILOT,
    FORMAT_CLAUDE,
    FORMAT_CLINE,
    SKILLS_SUBDIR,
    COPILOT_WORKSPACE_SKILLS_DIR,
)


@dataclass(frozen=True, slots=True)
class PathResolver:
    """Resolves format-specific paths for installation targets."""

    format_name: str

    def cache_dir(self, target: Path) -> Path:
        """Get recipe cache directory under .personetta/."""
        return target / PERSONETTA_DIR / self._cache_subdir()

    def rules_dir(self, target: Path) -> Path:
        """Get installation directory for rules/instructions."""
        if self.format_name == FORMAT_CURSOR:
            return target / CURSOR_DIR / CURSOR_RULES_SUBDIR
        elif self.format_name == FORMAT_COPILOT:
            return target / COPILOT_DIR / COPILOT_INSTRUCTIONS_SUBDIR
        elif self.format_name == FORMAT_CLAUDE:
            return target / CLAUDE_DIR / CLAUDE_RULES_SUBDIR
        elif self.format_name == FORMAT_CLINE:
            # Global: ~/Documents/Cline/Rules
            # Project: .clinerules
            return target / "Documents" / "Cline" / "Rules"
        else:
            raise ValueError(f"Unknown format: {self.format_name}")

    def state_file(self, target: Path) -> Path:
        """Get path to active recipe state JSON file."""
        return target / PERSONETTA_DIR / f"{self.format_name}-active.json"

    def _cache_subdir(self) -> str:
        """Get cache subdirectory name under .personetta/."""
        return {
            FORMAT_CURSOR: CURSOR_RECIPES_SUBDIR,
            FORMAT_COPILOT: COPILOT_RECIPES_SUBDIR,
            FORMAT_CLAUDE: CLAUDE_RECIPES_SUBDIR,
            FORMAT_CLINE: CLINE_RECIPES_SUBDIR,
        }[self.format_name]


# ━━━ Registry ━━━

_RESOLVERS: dict[str, PathResolver] = {
    FORMAT_CURSOR: PathResolver(FORMAT_CURSOR),
    FORMAT_COPILOT: PathResolver(FORMAT_COPILOT),
    FORMAT_CLAUDE: PathResolver(FORMAT_CLAUDE),
    FORMAT_CLINE: PathResolver(FORMAT_CLINE),
}


def provisions_user_path(target: Path) -> Path:
    """Path to the user's provisions override file under the install root.

    Provisions are tool-agnostic, so this file is shared across formats (it lives
    beside the recipe caches under ``.personetta/``), not per-format.

    Args:
        target: Install root (user home for global, repo root for project).

    Returns:
        Path to ``<target>/.personetta/provisions.yaml``.
    """
    return target / PERSONETTA_DIR / "provisions.yaml"


def get_path_resolver(format_name: str) -> PathResolver:
    """Get path resolver for the specified format."""
    try:
        return _RESOLVERS[format_name]
    except KeyError:
        available = ", ".join(sorted(_RESOLVERS.keys()))
        raise ValueError(
            f"Unknown format '{format_name}'. Available: {available}"
        ) from None


def get_skill_install_path(
    format_name: str,
    skill_name: str,
    workspace: bool,
    target: Path,
) -> Path:
    """
    Get installation path for a skill based on format and workspace flag.

    Args:
        format_name: Target format (copilot, claude, cursor, cline)
        skill_name: Name of the skill (e.g., "python-testing")
        workspace: If True, install to workspace directory; if False, install to user directory
        target: Base path (home directory for user-level, project directory for workspace)

    Returns:
        Path object representing the full skill installation directory

    Raises:
        ValueError: If format_name is not recognized

    Examples:
        >>> # Copilot user-level
        >>> get_skill_install_path("copilot", "python-testing", False, Path.home())
        Path("~/.copilot/skills/python-testing")

        >>> # Copilot workspace
        >>> get_skill_install_path("copilot", "code-review", True, Path.cwd())
        Path(".github/skills/code-review")

        >>> # Claude user-level
        >>> get_skill_install_path("claude", "python-testing", False, Path.home())
        Path("~/.claude/skills/python-testing")
    """
    # Validate format
    if format_name not in _RESOLVERS:
        available = ", ".join(sorted(_RESOLVERS.keys()))
        raise ValueError(f"Unknown format '{format_name}'. Available: {available}")

    # Determine base directory based on format and workspace flag
    if format_name == FORMAT_COPILOT:
        if workspace:
            # Copilot workspace uses .github/skills/
            base_dir = target / COPILOT_WORKSPACE_SKILLS_DIR / SKILLS_SUBDIR
        else:
            # Copilot user-level uses ~/.copilot/skills/
            base_dir = target / COPILOT_DIR / SKILLS_SUBDIR
    elif format_name == FORMAT_CLAUDE:
        # Claude uses .claude/skills/ for both user and workspace
        base_dir = target / CLAUDE_DIR / SKILLS_SUBDIR
    elif format_name == FORMAT_CURSOR:
        # Cursor uses .cursor/skills/ for both user and workspace
        base_dir = target / CURSOR_DIR / SKILLS_SUBDIR
    elif format_name == FORMAT_CLINE:
        # Cline uses .cline/skills/ for both user and workspace
        base_dir = target / ".cline" / SKILLS_SUBDIR
    else:
        # This should never be reached due to validation above
        raise ValueError(f"Unknown format: {format_name}")

    # Append skill name to create final path
    return base_dir / skill_name

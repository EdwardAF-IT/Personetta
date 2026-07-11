"""
Project directory layout constants.

Centralizes all project structure paths to make reorganizations painless.
All paths relative to project root unless otherwise specified.
"""

from __future__ import annotations

from pathlib import Path

# ━━━ PROJECT STRUCTURE ━━━

# Source code directories (will be under src/)
SRC_DIR = "src"
GENERATOR_DIR = "generator"  # Relative to SRC_DIR
TOOLING_DIR = "tooling"  # Relative to SRC_DIR

# Data directories (under data/ at root)
DATA_DIR = "data"
BASE_DIR = "base"  # Relative to DATA_DIR
LANGUAGE_SPECIFIC_DIR = "language_specific"  # Relative to DATA_DIR
RECIPES_DIR = "recipes"  # Relative to DATA_DIR
SCHEMAS_DIR = "schemas"  # Relative to DATA_DIR
CONFIG_DIR = "config"  # Relative to DATA_DIR
TEMPLATES_DIR = "templates"  # Relative to DATA_DIR
BUNDLED_SKILLS_DIR = "bundled-skills"  # Relative to DATA_DIR

# Other top-level directories (stay at root)
TESTS_DIR = "tests"
DOCS_DIR = "docs"
SCRIPTS_DIR = "scripts"
PIPELINES_DIR = "pipelines"


# ━━━ CURRENT LAYOUT (PRE-REORG) ━━━
# These point to the current structure - will be updated during reorg


def get_project_root_from_file(file_path: str | Path) -> Path:
    """
    Get project root from any file in the project.

    In development mode: Looks for pyproject.toml as the marker of project root.
    In installed mode: Falls back to finding the package root containing data/.
    """
    current = Path(file_path).resolve()

    # Try to find pyproject.toml (dev mode)
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists():
            return parent

    # Installed mode: find the directory containing our package structure
    # When installed via pip, we're in site-packages/generator/...
    # We want to return site-packages (which should have data/ alongside generator/)
    for parent in [current] + list(current.parents):
        # Look for data directory as the marker (more reliable than generator+base)
        # In installed mode: data/ is at root
        # In dev mode with pyproject.toml missing: data/ is still at root
        if (parent / "data").exists() and (parent / "data").is_dir():
            return parent

    # Last resort: return current directory's parent
    # This handles edge cases where the structure is unexpected
    return current.parent


class BaseProjectLayout:
    """
    Base project layout for Python projects.

    Provides generic project structure paths common to most Python projects.
    Subclass this to add project-specific directories.
    """

    def __init__(self, project_root: Path | None = None):
        """
        Initialize with explicit project root or auto-detect.

        Args:
            project_root: Explicit project root path, or None to auto-detect
        """
        if project_root is None:
            # Auto-detect from this file's location
            project_root = get_project_root_from_file(__file__)
        self.root = project_root.resolve()

        # Detect if we're in installed mode (site-packages) or dev mode (repo)
        # Dev mode: has src/ directory with our package structure
        # Installed mode: package files are at root level
        has_src_dir = (self.root / "src").exists() and (self.root / "src").is_dir()
        self._is_installed = not has_src_dir

    @classmethod
    def from_file(cls, file: Path | str) -> "BaseProjectLayout":
        """
        Construct a layout rooted at the project containing `file`.

        Args:
            file: Any file path within the project

        Returns:
            Layout instance rooted at the detected project root
        """
        return cls(get_project_root_from_file(file))

    # ━━━ Generic directories present in most Python projects ━━━

    @property
    def src(self) -> Path:
        """Source code directory."""
        return self.root / SRC_DIR

    @property
    def tests(self) -> Path:
        """Tests directory (stays at root)."""
        return self.root / TESTS_DIR

    @property
    def docs(self) -> Path:
        """Documentation directory (stays at root)."""
        return self.root / DOCS_DIR

    @property
    def scripts(self) -> Path:
        """Scripts directory (stays at root)."""
        return self.root / SCRIPTS_DIR


class ProjectLayout(BaseProjectLayout):
    """Resolves project directory paths relative to project root."""

    # ━━━ Source directories ━━━

    @property
    def generator(self) -> Path:
        """Generator module directory."""
        if self._is_installed:
            return self.root / GENERATOR_DIR
        return self.root / SRC_DIR / GENERATOR_DIR

    @property
    def base(self) -> Path:
        """Base roles directory."""
        if self._is_installed:
            return self.root / DATA_DIR / BASE_DIR
        return self.root / DATA_DIR / BASE_DIR

    @property
    def language_specific(self) -> Path:
        """Language-specific roles directory."""
        if self._is_installed:
            return self.root / DATA_DIR / LANGUAGE_SPECIFIC_DIR
        return self.root / DATA_DIR / LANGUAGE_SPECIFIC_DIR

    @property
    def tooling(self) -> Path:
        """Tooling utilities directory."""
        if self._is_installed:
            return self.root / TOOLING_DIR
        return self.root / SRC_DIR / TOOLING_DIR

    # ━━━ Data directories ━━━

    @property
    def recipes(self) -> Path:
        """Recipes directory."""
        if self._is_installed:
            return self.root / DATA_DIR / RECIPES_DIR
        return self.root / DATA_DIR / RECIPES_DIR

    @property
    def schemas(self) -> Path:
        """JSON schemas directory."""
        if self._is_installed:
            return self.root / DATA_DIR / SCHEMAS_DIR
        return self.root / DATA_DIR / SCHEMAS_DIR

    @property
    def config(self) -> Path:
        """Config files directory."""
        if self._is_installed:
            return self.root / DATA_DIR / CONFIG_DIR
        return self.root / DATA_DIR / CONFIG_DIR

    @property
    def templates(self) -> Path:
        """Templates directory."""
        if self._is_installed:
            return self.root / DATA_DIR / TEMPLATES_DIR
        return self.root / DATA_DIR / TEMPLATES_DIR

    @property
    def bundled_skills(self) -> Path:
        """Bundled skills directory."""
        if self._is_installed:
            return self.root / "data" / BUNDLED_SKILLS_DIR
        return self.root / "data" / BUNDLED_SKILLS_DIR


# Global instance for convenience
_default_layout: ProjectLayout | None = None


def get_default_layout() -> ProjectLayout:
    """Get or create the default project layout instance."""
    global _default_layout
    if _default_layout is None:
        _default_layout = ProjectLayout()
    return _default_layout

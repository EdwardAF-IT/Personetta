"""
Base layout strategy for tool-specific installation patterns.

Provides common implementation for installing recipes across all supported tools
(Cursor, Copilot, Claude, Cline), with format-specific behavior delegated to subclasses.

This eliminates ~600 lines of duplication across the four layout files.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

from generator.constants import PERSONETTA_DIR, MARKDOWN_GLOB
from generator.loader import (
    load_merge_config,
    load_recipe,
    load_recipe_roles,
    list_recipes,
)
from generator.merger import compose_recipe
from generator.output_formats import format_role


class LayoutStrategy(ABC):
    """Abstract base class for format-specific installation layouts."""

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Format identifier (e.g., 'cursor', 'copilot', 'claude', 'cline')."""
        pass

    @property
    @abstractmethod
    def recipes_subdir(self) -> str:
        """Subdirectory name under .personetta/ for cached recipes."""
        pass

    @abstractmethod
    def rules_dir(self, target: Path) -> Path:
        """Installation directory for active rules/instructions."""
        pass

    @abstractmethod
    def wrap_output(self, content: str, recipe: dict) -> str:
        """
        Format-specific wrapping of composed output.

        Args:
            content: The formatted recipe content (markdown)
            recipe: The recipe dict (may contain metadata for frontmatter)

        Returns:
            Wrapped content ready to write to cache
        """
        pass

    @abstractmethod
    def write_baseline_router_active(
        self,
        target_root: Path,
        successful_recipes: list[str],
        base_dir: Path,
    ) -> None:
        """
        Write format-specific baseline, router, and active files.

        Args:
            target_root: Target installation directory
            successful_recipes: List of recipe names that composed successfully
            base_dir: Base directory containing roles and recipes
        """
        pass

    @abstractmethod
    def cleanup_on_zero_successes(self, target_root: Path) -> None:
        """
        Remove all format-specific files when no recipes composed successfully.

        Prevents stale personas from lingering after failed installs.
        """
        pass

    # ━━━ Common implementation (shared by all formats) ━━━

    def personetta_root(self, target: Path) -> Path:
        """Get .personetta directory path."""
        return target / PERSONETTA_DIR

    def recipe_cache_dir(self, target: Path) -> Path:
        """Get cache directory for this format's recipes."""
        return self.personetta_root(target) / self.recipes_subdir

    def state_path(self, target: Path) -> Path:
        """Get path to active recipe state JSON file."""
        return self.personetta_root(target) / f"{self.format_name}-active.json"

    def write_state(self, target: Path, active_recipe: str) -> None:
        """Write active recipe state to JSON file."""
        path = self.state_path(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"active_recipe": active_recipe, "format": self.format_name}
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def read_state(self, target: Path) -> dict | None:
        """Read active recipe state from JSON file."""
        path = self.state_path(target)
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def get_default_active_recipe(self, successful_recipes: list[str]) -> str:
        """Get default active recipe (first alphabetically)."""
        return sorted(successful_recipes)[0]

    def load_cached_recipe_content(self, target_root: Path, recipe_name: str) -> str:
        """Load content from cached recipe file."""
        cache_dir = self.recipe_cache_dir(target_root)
        return (cache_dir / (recipe_name + ".md")).read_text(encoding="utf-8")

    def list_cached_recipes(self, target_root: Path) -> list[str]:
        """List recipe names in cache directory (without .md extension)."""
        cache_dir = self.recipe_cache_dir(target_root)
        if not cache_dir.is_dir():
            return []
        return sorted(p.stem for p in cache_dir.glob(MARKDOWN_GLOB))

    def install_all(
        self,
        base_dir: Path,
        target_root: Path,
        *,
        recipe_filter: str | None = None,
        recipe_list: list[str] | None = None,
    ) -> tuple[list[str], list[str]]:
        """
        Install all recipes to target directory.

        This is the main entry point for installation. It:
        1. Loads and filters recipes
        2. Composes each recipe (merges roles + mixins)
        3. Formats output for this tool
        4. Writes to cache
        5. Prunes stale cache files
        6. Writes baseline/router/active files

        Args:
            base_dir: Base directory containing roles/ and recipes/
            target_root: Target installation directory (user home or project)
            recipe_filter: Optional substring filter for recipe names (legacy)
            recipe_list: Optional explicit list of recipe names to install (takes precedence over recipe_filter)

        Returns:
            (successful_recipe_names, failed_recipe_names)
        """
        merge_config = load_merge_config(base_dir)
        recipes = list_recipes(base_dir)

        if recipe_list is not None:
            # Use explicit list of recipe names
            recipe_names_set = set(recipe_list)
            recipes = [r for r in recipes if r["name"] in recipe_names_set]
        elif recipe_filter:
            # Legacy substring filter
            recipes = [r for r in recipes if recipe_filter in r["name"]]

        if not recipes:
            return [], []

        cache_dir = self.recipe_cache_dir(target_root)
        cache_dir.mkdir(parents=True, exist_ok=True)

        ok: list[str] = []
        failed: list[str] = []

        for recipe_info in recipes:
            recipe = load_recipe(recipe_info["name"], base_dir)
            compose_roles, mixin_roles = load_recipe_roles(recipe, base_dir)
            composed, warnings = compose_recipe(
                recipe, compose_roles, mixin_roles, merge_config
            )

            errors = [w for w in warnings if w.severity == "error"]
            if errors:
                failed.append(recipe_info["name"])
                continue

            # Format and wrap output for this tool (cache files use alwaysApply: false for Cursor)
            output = format_role(composed, self.format_name, cursor_always_apply=False)
            wrapped = self.wrap_output(output, recipe)
            (cache_dir / (recipe["name"] + ".md")).write_text(wrapped, encoding="utf-8")
            ok.append(recipe["name"])

        if not ok:
            self.cleanup_on_zero_successes(target_root)
            return ok, failed

        # Prune stale cache files
        ok_set = set(ok)
        for p in cache_dir.glob(MARKDOWN_GLOB):
            if p.stem not in ok_set:
                p.unlink()

        # Write format-specific baseline, router, and active files
        self.write_baseline_router_active(target_root, ok, base_dir)

        return ok, failed

    def install_single_recipe_to_cache(
        self,
        recipe_name: str,
        base_dir: Path,
        target_root: Path,
    ) -> dict:
        """
        Install a single recipe to cache (used by set-active).

        Args:
            recipe_name: Name of recipe to install
            base_dir: Base directory containing roles/ and recipes/
            target_root: Target installation directory

        Returns:
            Composed recipe dict

        Raises:
            ValueError: If recipe composition fails
        """
        merge_config = load_merge_config(base_dir)
        recipe = load_recipe(recipe_name, base_dir)
        compose_roles, mixin_roles = load_recipe_roles(recipe, base_dir)
        composed, warnings = compose_recipe(
            recipe, compose_roles, mixin_roles, merge_config
        )

        errors = [w for w in warnings if w.severity == "error"]
        if errors:
            raise ValueError("; ".join(w.message for w in errors))

        output = format_role(composed, self.format_name)
        wrapped = self.wrap_output(output, recipe)

        cache_dir = self.recipe_cache_dir(target_root)
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / (recipe_name + ".md")
        cache_path.write_text(wrapped, encoding="utf-8")

        return composed

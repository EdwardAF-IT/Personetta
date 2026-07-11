"""
Cursor install layout: one always-on baseline, one active persona in .cursor/rules,
full recipe bodies in .personetta/cursor-recipes/ (not loaded by Cursor as rules).

See docs/requirements.md for product rationale.
"""

from __future__ import annotations

from pathlib import Path

from generator.layout_base import LayoutStrategy
from generator.loader import load_recipe, load_system_role
from generator.project_layout import get_project_root_from_file

import yaml

from generator.constants import (
    FORMAT_CURSOR,
    CURSOR_RECIPES_SUBDIR,
    CURSOR_BASELINE_FILENAME,
    CURSOR_ROUTER_FILENAME,
    CURSOR_ACTIVE_FILENAME,
)
from generator.formatter import (
    replace_cursor_frontmatter,
)
from generator.formatters.system import (
    format_baseline_for_cursor,
    format_router_for_cursor,
)


class CursorLayout(LayoutStrategy):
    """Cursor-specific layout implementation."""

    @property
    def format_name(self) -> str:
        return FORMAT_CURSOR

    @property
    def recipes_subdir(self) -> str:
        return CURSOR_RECIPES_SUBDIR

    def rules_dir(self, target: Path) -> Path:
        return target / ".cursor" / "rules"

    def wrap_output(self, content: str, recipe: dict) -> str:
        """Wrap with Cursor frontmatter (alwaysApply: false for cache)."""
        # Content is already formatted as cursor markdown by format_cursor
        # We just need to ensure it has frontmatter with alwaysApply: false
        return content

    def write_baseline_router_active(
        self,
        target_root: Path,
        successful_recipes: list[str],
        base_dir: Path,
    ) -> None:
        """Write Cursor-specific baseline, router, and active files."""
        # Install baseline
        self._install_baseline(target_root)

        # Install router
        self._install_router(target_root, successful_recipes, base_dir)

        # Install default active (first recipe alphabetically)
        default_name = sorted(successful_recipes)[0]
        self._write_active_from_cache(target_root, default_name, base_dir)
        self.write_state(target_root, default_name)

    def cleanup_on_zero_successes(self, target_root: Path) -> None:
        """Remove all Cursor files when no recipes succeed."""
        rules = self.rules_dir(target_root)
        for name in (
            CURSOR_BASELINE_FILENAME,
            CURSOR_ROUTER_FILENAME,
            CURSOR_ACTIVE_FILENAME,
        ):
            p = rules / name
            if p.is_file():
                p.unlink()

        cache_dir = self.recipe_cache_dir(target_root)
        if cache_dir.is_dir():
            for p in cache_dir.glob("*.md"):
                p.unlink()

        state_path = self.state_path(target_root)
        if state_path.is_file():
            state_path.unlink()

    # ━━━ Cursor-specific helper methods ━━━

    def _install_baseline(self, target: Path) -> Path:
        """Install personetta-baseline.md from YAML."""
        project_root = get_project_root_from_file(__file__)
        baseline = load_system_role("baseline", project_root)
        body = format_baseline_for_cursor(baseline)
        dest = self.rules_dir(target) / CURSOR_BASELINE_FILENAME
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body, encoding="utf-8")
        return dest

    def _install_router(
        self, target_root: Path, recipe_names: list[str], base_dir: Path
    ) -> Path:
        """Write personetta-router.md from YAML and installed recipe ids."""
        router = load_system_role("router", base_dir)

        rows: list[dict] = []
        for name in sorted(recipe_names):
            r = load_recipe(name, base_dir)
            desc = (r.get("description") or "").strip()
            first_line = desc.split("\n")[0] if desc else ""
            rows.append(
                {
                    "name": name,
                    "description": first_line,
                    "activation_phrases": r.get("activation_phrases") or [],
                }
            )

        text = format_router_for_cursor(router, rows)
        dest = self.rules_dir(target_root) / CURSOR_ROUTER_FILENAME
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        return dest

    def _write_active_from_cache(
        self,
        target_root: Path,
        recipe_name: str,
        base_dir: Path,
    ) -> Path:
        """Write personetta-active.md from cached recipe."""
        cache_path = self.recipe_cache_dir(target_root) / f"{recipe_name}.md"
        cache_text = cache_path.read_text(encoding="utf-8")

        # Get description from cached file or recipe
        desc = self._description_from_cached_file(cache_text)
        if not desc:
            recipe = load_recipe(recipe_name, base_dir)
            desc = recipe.get("description", "")

        # Create active file with alwaysApply: true
        short = desc.strip().replace("\n", " ")
        if len(short) > 200:
            short = short[:197] + "..."
        escaped = short.replace('"', '"')
        frontmatter_desc = f"Personetta active persona ({recipe_name}): {escaped}"

        text = replace_cursor_frontmatter(cache_text, frontmatter_desc, always_apply=True)
        dest = self.rules_dir(target_root) / CURSOR_ACTIVE_FILENAME
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        return dest

    def _description_from_cached_file(self, text: str) -> str:
        """Extract description from cached file's YAML frontmatter."""
        if not text.startswith("---"):
            return ""
        end = text.find("---", 3)
        if end == -1:
            return ""
        try:
            meta = yaml.safe_load(text[3:end])
            if isinstance(meta, dict) and meta.get("description"):
                return str(meta["description"])
        except yaml.YAMLError:
            pass
        return ""


# ━━━ Module-level singleton and public API ━━━

_cursor_layout = CursorLayout()


def install_all_cursor(
    base_dir: Path,
    target_root: Path,
    *,
    recipe_filter: str | None = None,
    recipe_list: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    """
    Install baseline + recipe cache + default active persona.
    Returns (successful_recipe_names, failed_recipe_names).
    """
    return _cursor_layout.install_all(
        base_dir, target_root, recipe_filter=recipe_filter, recipe_list=recipe_list
    )


def set_active_cursor(
    target_root: Path, recipe_name: str, base_dir: Path | None = None
) -> Path:
    """Point personetta-active.md at a cached recipe. Raises FileNotFoundError if cache missing."""
    if base_dir is None:
        import os

        override = os.environ.get("PERSONETTA_BASE")
        if override:
            base_dir = Path(override).resolve()
        else:
            # Use project root from project layout
            base_dir = get_project_root_from_file(__file__)

    cache_path = _cursor_layout.recipe_cache_dir(target_root) / f"{recipe_name}.md"
    if not cache_path.is_file():
        raise FileNotFoundError(
            f"No cached Cursor recipe '{recipe_name}' at {cache_path}. "
            "Run: personetta install '*' --format cursor"
        )

    dest = _cursor_layout._write_active_from_cache(target_root, recipe_name, base_dir)
    _cursor_layout.write_state(target_root, recipe_name)
    return dest


def install_single_cursor_recipe_to_cache(
    base_dir: Path,
    target_root: Path,
    recipe_name: str,
) -> Path:
    """Compose one recipe and write cache. Refresh active file if it is the active recipe."""
    # Ensure baseline exists
    if not (_cursor_layout.rules_dir(target_root) / CURSOR_BASELINE_FILENAME).is_file():
        _cursor_layout._install_baseline(target_root)

    # Use base class method to compose and cache
    _ = _cursor_layout.install_single_recipe_to_cache(recipe_name, base_dir, target_root)

    # If this is the active recipe, refresh active file
    state = _cursor_layout.read_state(target_root)
    active = state.get("active_recipe") if state else None
    if active == recipe_name:
        _cursor_layout._write_active_from_cache(target_root, recipe_name, base_dir)

    # Refresh router
    refresh_cursor_router_from_cache(base_dir, target_root)

    cache_path = _cursor_layout.recipe_cache_dir(target_root) / f"{recipe_name}.md"
    return cache_path


def refresh_cursor_router_from_cache(base_dir: Path, target_root: Path) -> Path | None:
    """Rebuild router from whatever is in cursor-recipes (after single-recipe update)."""
    names = _cursor_layout.list_cached_recipes(target_root)
    if not names:
        return None
    return _cursor_layout._install_router(target_root, names, base_dir)


# ─────────────────────────────────────────────────────────────────────────────
# Re-exports for backward compatibility
# ─────────────────────────────────────────────────────────────────────────────
ACTIVE_FILENAME = CURSOR_ACTIVE_FILENAME
BASELINE_FILENAME = CURSOR_BASELINE_FILENAME
ROUTER_FILENAME = CURSOR_ROUTER_FILENAME


def _rules_dir(target_root: Path) -> Path:
    """Legacy helper for backward compatibility."""
    return _cursor_layout.rules_dir(target_root)


def list_cached_cursor_recipes(target_root: Path) -> list[str]:
    """List recipe names in cache directory (without .md extension)."""
    return _cursor_layout.list_cached_recipes(target_root)


def cursor_recipe_cache_dir(target: Path) -> Path:
    """Get cache directory path."""
    return _cursor_layout.recipe_cache_dir(target)


def read_cursor_state(target: Path) -> dict | None:
    """Read state file."""
    return _cursor_layout.read_state(target)

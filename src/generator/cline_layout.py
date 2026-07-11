"""
Cline global rules under ~/Documents/Cline/Rules (see Cline global rules support).

Workspace rules still use .clinerules; link can junction that folder to the global dir.
"""

from __future__ import annotations

from pathlib import Path

from generator.constants import (
    FORMAT_CLINE,
    CLINE_RECIPES_SUBDIR,
    CLINE_STATE_FILE,
    CLINE_BASELINE_FILENAME,
    CLINE_ROUTER_FILENAME,
    CLINE_ACTIVE_FILENAME,
)
from generator.layout_common import (
    collect_recipe_router_rows,
)
from generator.formatters.system import (
    format_baseline_for_plain,
    format_router_for_plain,
)
from generator.layout_base import LayoutStrategy
from generator.loader import load_system_role


class ClineLayout(LayoutStrategy):
    @property
    def format_name(self) -> str:
        return FORMAT_CLINE

    @property
    def recipes_subdir(self) -> str:
        return CLINE_RECIPES_SUBDIR

    def rules_dir(self, target_root: Path) -> Path:
        """Cline loads personal rules from Documents/Cline/Rules (all platforms, home-relative)."""
        return target_root / "Documents" / "Cline" / "Rules"

    @property
    def state_file(self) -> str:
        return CLINE_STATE_FILE

    def wrap_output(self, content: str, recipe: dict) -> str:
        """Cline uses plain markdown - no wrapping needed."""
        return content

    def write_baseline_router_active(
        self,
        target_root: Path,
        successful_recipes: list[str],
        base_dir: Path,
    ) -> None:
        rules_dir = self.rules_dir(target_root)
        rules_dir.mkdir(parents=True, exist_ok=True)

        # Write router
        self._install_router(target_root, successful_recipes, base_dir)

        # Write baseline from YAML
        baseline = load_system_role("baseline", base_dir)
        baseline_body = format_baseline_for_plain(
            baseline,
            format_key="cline",
            host_product="Cline (VS Code extension)",
            cache_glob="~/.personetta/cline-recipes/",
            active_filename=CLINE_ACTIVE_FILENAME,
            router_filename=CLINE_ROUTER_FILENAME,
        )
        (rules_dir / CLINE_BASELINE_FILENAME).write_text(baseline_body, encoding="utf-8")

        # Write active file (first recipe alphabetically)
        default_name = sorted(successful_recipes)[0]
        cache_dir = self.recipe_cache_dir(target_root)
        active_body = (cache_dir / (default_name + ".md")).read_text(encoding="utf-8")
        (rules_dir / CLINE_ACTIVE_FILENAME).write_text(active_body, encoding="utf-8")
        self.write_state(target_root, default_name)

    def cleanup_on_zero_successes(self, target_root: Path) -> None:
        gdir = self.rules_dir(target_root)
        for name in (
            CLINE_BASELINE_FILENAME,
            CLINE_ROUTER_FILENAME,
            CLINE_ACTIVE_FILENAME,
        ):
            p = gdir / name
            if p.is_file():
                p.unlink()
        cache_dir = self.recipe_cache_dir(target_root)
        if cache_dir.is_dir():
            for p in cache_dir.glob("*.md"):
                p.unlink()
        state_path = self.state_path(target_root)
        if state_path.is_file():
            state_path.unlink()

    def _install_router(
        self, target_root: Path, recipe_names: list[str], base_dir: Path
    ) -> Path:
        """Write Cline-specific router file from YAML."""
        router = load_system_role("router", base_dir)
        rows = collect_recipe_router_rows(base_dir, recipe_names)
        body = format_router_for_plain(
            router,
            format_key="cline",
            recipe_rows=rows,
            cache_glob="~/.personetta/cline-recipes/",
            active_filename=CLINE_ACTIVE_FILENAME,
        )
        dest = self.rules_dir(target_root) / CLINE_ROUTER_FILENAME
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body, encoding="utf-8")
        return dest

    def _write_active_from_cache(
        self, target_root: Path, recipe_name: str, base_dir: Path
    ) -> Path:
        """Write active persona file from cached recipe."""
        cache_path = self.recipe_cache_dir(target_root) / (recipe_name + ".md")
        body = cache_path.read_text(encoding="utf-8")
        dest = self.rules_dir(target_root) / CLINE_ACTIVE_FILENAME
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body, encoding="utf-8")
        return dest


# Module-level singleton
_cline_layout = ClineLayout()


# ─────────────────────────────────────────────────────────────────────────────
# Public API (backward compatible)
# ─────────────────────────────────────────────────────────────────────────────


def cline_global_rules_dir(profile: Path) -> Path:
    """Cline loads personal rules from Documents/Cline/Rules (all platforms, home-relative)."""
    return _cline_layout.rules_dir(profile)


def personetta_root(target: Path) -> Path:
    return target / ".personetta"


def cline_recipe_cache_dir(target: Path) -> Path:
    return _cline_layout.recipe_cache_dir(target)


def cline_state_path(target: Path) -> Path:
    return _cline_layout.state_path(target)


def write_cline_state(target: Path, active_recipe: str) -> None:
    _cline_layout.write_state(target, active_recipe)


def read_cline_state(target: Path) -> dict | None:
    return _cline_layout.read_state(target)


def _cleanup_cline_on_zero_successes(target_root: Path) -> None:
    _cline_layout.cleanup_on_zero_successes(target_root)


def install_all_cline(
    base_dir: Path,
    target_root: Path,
    *,
    recipe_filter: str | None = None,
    recipe_list: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    return _cline_layout.install_all(
        base_dir, target_root, recipe_filter=recipe_filter, recipe_list=recipe_list
    )


def set_active_cline(base_dir: Path, target_root: Path, recipe_name: str) -> Path:
    """Point active persona at a cached recipe. Raises FileNotFoundError if cache missing."""
    cache_path = cline_recipe_cache_dir(target_root) / (recipe_name + ".md")
    if not cache_path.is_file():
        msg = (
            "No cached Cline recipe '{0}' at {1}. "
            "Run: personetta install '*' --format cline"
        ).format(recipe_name, cache_path)
        raise FileNotFoundError(msg)

    dest = _cline_layout._write_active_from_cache(target_root, recipe_name, base_dir)
    _cline_layout.write_state(target_root, recipe_name)
    return dest


def install_cline_router(
    target_root: Path, recipe_names: list[str], base_dir: Path
) -> Path:
    return _cline_layout._install_router(target_root, recipe_names, base_dir)


def install_single_cline_recipe_to_cache(
    base_dir: Path,
    target_root: Path,
    recipe_name: str,
) -> Path:
    """Compose one recipe and write cache. Refresh active file if it is the active recipe."""
    # Use base class method to compose and cache
    _ = _cline_layout.install_single_recipe_to_cache(recipe_name, base_dir, target_root)

    # If this is the active recipe, refresh active file
    state = _cline_layout.read_state(target_root)
    active = state.get("active_recipe") if state else None
    if active == recipe_name:
        _cline_layout._write_active_from_cache(target_root, recipe_name, base_dir)

    # Refresh router if cache has recipes
    names = _cline_layout.list_cached_recipes(target_root)
    if names:
        _cline_layout._install_router(target_root, names, base_dir)

    cache_path = _cline_layout.recipe_cache_dir(target_root) / (recipe_name + ".md")
    return cache_path


def list_cached_cline_recipes(target_root: Path) -> list[str]:
    """List cached recipe names."""
    return _cline_layout.list_cached_recipes(target_root)


# Constants for backward compatibility (actively used by commands.py)
BASELINE_NAME = CLINE_BASELINE_FILENAME
ROUTER_NAME = CLINE_ROUTER_FILENAME
ACTIVE_NAME = CLINE_ACTIVE_FILENAME

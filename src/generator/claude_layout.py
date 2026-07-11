"""
Claude Code install layout: user rules under ~/.claude/rules/ (markdown).

See Claude Code memory docs: personal rules in ~/.claude/rules/.
"""

from __future__ import annotations

from pathlib import Path

from generator.constants import (
    FORMAT_CLAUDE,
    CLAUDE_RECIPES_SUBDIR,
    CLAUDE_STATE_FILE,
    CLAUDE_BASELINE_FILENAME,
    CLAUDE_ROUTER_FILENAME,
    CLAUDE_ACTIVE_FILENAME,
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


class ClaudeLayout(LayoutStrategy):
    @property
    def format_name(self) -> str:
        return FORMAT_CLAUDE

    @property
    def recipes_subdir(self) -> str:
        return CLAUDE_RECIPES_SUBDIR

    def rules_dir(self, target_root: Path) -> Path:
        return target_root / ".claude" / "rules"

    @property
    def state_file(self) -> str:
        return CLAUDE_STATE_FILE

    def wrap_output(self, content: str, recipe: dict) -> str:
        """Claude uses plain markdown - no wrapping needed."""
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
            format_key="claude",
            host_product="Claude Code (terminal / IDE)",
            cache_glob="~/.personetta/claude-recipes/",
            active_filename=CLAUDE_ACTIVE_FILENAME,
            router_filename=CLAUDE_ROUTER_FILENAME,
        )
        (rules_dir / CLAUDE_BASELINE_FILENAME).write_text(baseline_body, encoding="utf-8")

        # Write active file (first recipe alphabetically)
        default_name = sorted(successful_recipes)[0]
        cache_dir = self.recipe_cache_dir(target_root)
        active_body = (cache_dir / (default_name + ".md")).read_text(encoding="utf-8")
        (rules_dir / CLAUDE_ACTIVE_FILENAME).write_text(active_body, encoding="utf-8")
        self.write_state(target_root, default_name)

    def cleanup_on_zero_successes(self, target_root: Path) -> None:
        rules = self.rules_dir(target_root)
        for name in (
            CLAUDE_BASELINE_FILENAME,
            CLAUDE_ROUTER_FILENAME,
            CLAUDE_ACTIVE_FILENAME,
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

    def _install_router(
        self, target_root: Path, recipe_names: list[str], base_dir: Path
    ) -> Path:
        """Write Claude-specific router file from YAML."""
        router = load_system_role("router", base_dir)
        rows = collect_recipe_router_rows(base_dir, recipe_names)
        body = format_router_for_plain(
            router,
            format_key="claude",
            recipe_rows=rows,
            cache_glob="~/.personetta/claude-recipes/",
            active_filename=CLAUDE_ACTIVE_FILENAME,
        )
        dest = self.rules_dir(target_root) / CLAUDE_ROUTER_FILENAME
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body, encoding="utf-8")
        return dest

    def _write_active_from_cache(
        self, target_root: Path, recipe_name: str, base_dir: Path
    ) -> Path:
        """Write active persona file from cached recipe."""
        cache_path = self.recipe_cache_dir(target_root) / (recipe_name + ".md")
        body = cache_path.read_text(encoding="utf-8")
        dest = self.rules_dir(target_root) / CLAUDE_ACTIVE_FILENAME
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body, encoding="utf-8")
        return dest


# Module-level singleton
_claude_layout = ClaudeLayout()


# ─────────────────────────────────────────────────────────────────────────────
# Public API (backward compatible)
# ─────────────────────────────────────────────────────────────────────────────


def personetta_root(target: Path) -> Path:
    return target / ".personetta"


def claude_recipe_cache_dir(target: Path) -> Path:
    return _claude_layout.recipe_cache_dir(target)


def claude_state_path(target: Path) -> Path:
    return _claude_layout.state_path(target)


def claude_rules_dir(target: Path) -> Path:
    return _claude_layout.rules_dir(target)


def write_claude_state(target: Path, active_recipe: str) -> None:
    _claude_layout.write_state(target, active_recipe)


def read_claude_state(target: Path) -> dict | None:
    return _claude_layout.read_state(target)


def install_claude_router(
    target_root: Path, recipe_names: list[str], base_dir: Path
) -> Path:
    return _claude_layout._install_router(target_root, recipe_names, base_dir)


def _cleanup_claude_on_zero_successes(target_root: Path) -> None:
    _claude_layout.cleanup_on_zero_successes(target_root)


def install_all_claude(
    base_dir: Path,
    target_root: Path,
    *,
    recipe_filter: str | None = None,
    recipe_list: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    return _claude_layout.install_all(
        base_dir, target_root, recipe_filter=recipe_filter, recipe_list=recipe_list
    )


def set_active_claude(base_dir: Path, target_root: Path, recipe_name: str) -> Path:
    """Point active persona at a cached recipe. Raises FileNotFoundError if cache missing."""
    cache_path = claude_recipe_cache_dir(target_root) / (recipe_name + ".md")
    if not cache_path.is_file():
        msg = (
            "No cached Claude recipe '{0}' at {1}. "
            "Run: personetta install '*' --format claude"
        ).format(recipe_name, cache_path)
        raise FileNotFoundError(msg)

    dest = _claude_layout._write_active_from_cache(target_root, recipe_name, base_dir)
    _claude_layout.write_state(target_root, recipe_name)
    return dest


def install_single_claude_recipe_to_cache(
    base_dir: Path,
    target_root: Path,
    recipe_name: str,
) -> Path:
    """Compose one recipe and write cache. Refresh active file if it is the active recipe."""
    # Use base class method to compose and cache
    _ = _claude_layout.install_single_recipe_to_cache(recipe_name, base_dir, target_root)

    # If this is the active recipe, refresh active file
    state = _claude_layout.read_state(target_root)
    active = state.get("active_recipe") if state else None
    if active == recipe_name:
        _claude_layout._write_active_from_cache(target_root, recipe_name, base_dir)

    # Refresh router if cache has recipes
    names = _claude_layout.list_cached_recipes(target_root)
    if names:
        _claude_layout._install_router(target_root, names, base_dir)

    cache_path = _claude_layout.recipe_cache_dir(target_root) / (recipe_name + ".md")
    return cache_path


def list_cached_claude_recipes(target_root: Path) -> list[str]:
    """List cached recipe names."""
    return _claude_layout.list_cached_recipes(target_root)


# Constants for backward compatibility (actively used by commands.py)
BASELINE_NAME = CLAUDE_BASELINE_FILENAME
ROUTER_NAME = CLAUDE_ROUTER_FILENAME
ACTIVE_NAME = CLAUDE_ACTIVE_FILENAME

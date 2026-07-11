"""
GitHub Copilot (VS Code) install layout: user profile ~/.copilot/instructions/*.instructions.md
"""

from __future__ import annotations

from pathlib import Path

from generator.constants import (
    FORMAT_COPILOT,
    COPILOT_RECIPES_SUBDIR,
    COPILOT_STATE_FILE,
    COPILOT_BASELINE_STEM,
    COPILOT_ROUTER_STEM,
    COPILOT_ACTIVE_STEM,
    COPILOT_INSTRUCTIONS_SUFFIX,
)
from generator.layout_common import (
    collect_recipe_router_rows,
    build_plain_router_markdown,
    build_plain_baseline_markdown,
)
from generator.formatters.system import (
    format_baseline_for_plain,
    format_router_for_plain,
)
from generator.layout_base import LayoutStrategy
from generator.loader import load_recipe, list_recipes, load_system_role


class CopilotLayout(LayoutStrategy):
    @property
    def format_name(self) -> str:
        return FORMAT_COPILOT

    @property
    def recipes_subdir(self) -> str:
        return COPILOT_RECIPES_SUBDIR

    def rules_dir(self, target_root: Path) -> Path:
        return target_root / ".copilot" / "instructions"

    @property
    def state_file(self) -> str:
        return COPILOT_STATE_FILE

    def wrap_output(self, content: str, recipe: dict) -> str:
        """Wrap content with Copilot instruction frontmatter."""
        name = recipe.get("name", "Personetta recipe")
        description = recipe.get("description", "Personetta composed recipe")
        desc_escaped = description.replace("'", "''")
        header = "---\nname: '{0}'\ndescription: '{1}'\napplyTo: '{2}'\n---\n\n".format(
            name, desc_escaped, "**"
        )
        return header + content.lstrip("\n")

    def write_baseline_router_active(
        self,
        target_root: Path,
        successful_recipes: list[str],
        base_dir: Path,
    ) -> None:
        inst_dir = self.rules_dir(target_root)
        inst_dir.mkdir(parents=True, exist_ok=True)

        # Load system roles from YAML
        baseline = load_system_role("baseline", base_dir)
        router = load_system_role("router", base_dir)

        # Collect recipe data for router
        rows = collect_recipe_router_rows(base_dir, successful_recipes)

        # Format system roles for Copilot
        router_body = format_router_for_plain(
            router,
            format_key="copilot",
            recipe_rows=rows,
            cache_glob="~/.personetta/copilot-recipes/",
            active_filename=COPILOT_ACTIVE_STEM + COPILOT_INSTRUCTIONS_SUFFIX,
        )
        baseline_body = format_baseline_for_plain(
            baseline,
            format_key="copilot",
            host_product="GitHub Copilot in VS Code",
            cache_glob="~/.personetta/copilot-recipes/",
            active_filename=COPILOT_ACTIVE_STEM + COPILOT_INSTRUCTIONS_SUFFIX,
            router_filename=COPILOT_ROUTER_STEM + COPILOT_INSTRUCTIONS_SUFFIX,
        )

        (inst_dir / (COPILOT_ROUTER_STEM + COPILOT_INSTRUCTIONS_SUFFIX)).write_text(
            self.wrap_output(
                router_body,
                {
                    "name": "Personetta - recipe router",
                    "description": "Recipe index and set-active commands (Personetta).",
                },
            ),
            encoding="utf-8",
        )

        (inst_dir / (COPILOT_BASELINE_STEM + COPILOT_INSTRUCTIONS_SUFFIX)).write_text(
            self.wrap_output(
                baseline_body,
                {
                    "name": "Personetta - baseline",
                    "description": "Cross-cutting Personetta rules for Copilot chat (always on).",
                },
            ),
            encoding="utf-8",
        )

        # Write active file (first recipe alphabetically)
        default_recipe_name = sorted(successful_recipes)[0]
        recipes = list_recipes(base_dir)
        default_info = next(r for r in recipes if r["name"] == default_recipe_name)
        cache_dir = self.recipe_cache_dir(target_root)
        active_body = (cache_dir / (default_recipe_name + ".md")).read_text(
            encoding="utf-8"
        )
        desc_short = (default_info.get("description") or "Personetta composed recipe")[
            :200
        ]
        (inst_dir / (COPILOT_ACTIVE_STEM + COPILOT_INSTRUCTIONS_SUFFIX)).write_text(
            self.wrap_output(
                active_body,
                {
                    "name": "Personetta - active persona ({0})".format(
                        default_recipe_name
                    ),
                    "description": desc_short,
                },
            ),
            encoding="utf-8",
        )
        self.write_state(target_root, default_recipe_name)

    def cleanup_on_zero_successes(self, target_root: Path) -> None:
        inst = self.rules_dir(target_root)
        for stem in (COPILOT_BASELINE_STEM, COPILOT_ROUTER_STEM, COPILOT_ACTIVE_STEM):
            p = inst / (stem + COPILOT_INSTRUCTIONS_SUFFIX)
            if p.is_file():
                p.unlink()
        cache_dir = self.recipe_cache_dir(target_root)
        if cache_dir.is_dir():
            for p in cache_dir.glob("*.md"):
                p.unlink()
        state_path = self.state_path(target_root)
        if state_path.is_file():
            state_path.unlink()
        if inst.is_dir() and not any(inst.iterdir()):
            inst.rmdir()

    def _write_active_from_cache(
        self, target_root: Path, recipe_name: str, base_dir: Path
    ) -> Path:
        """Write active persona file from cached recipe."""
        cache_path = self.recipe_cache_dir(target_root) / (recipe_name + ".md")
        body = cache_path.read_text(encoding="utf-8")
        recipe = load_recipe(recipe_name, base_dir)
        desc = (recipe.get("description") or "Personetta composed recipe")[:200]

        inst_dir = self.rules_dir(target_root)
        inst_dir.mkdir(parents=True, exist_ok=True)
        dest = inst_dir / (COPILOT_ACTIVE_STEM + COPILOT_INSTRUCTIONS_SUFFIX)
        dest.write_text(
            self.wrap_output(
                body,
                {
                    "name": "Personetta - active persona ({0})".format(recipe_name),
                    "description": desc,
                },
            ),
            encoding="utf-8",
        )
        return dest


# Module-level singleton
_copilot_layout = CopilotLayout()


# ─────────────────────────────────────────────────────────────────────────────
# Public API (backward compatible)
# ─────────────────────────────────────────────────────────────────────────────


def personetta_root(target: Path) -> Path:
    return target / ".personetta"


def copilot_recipe_cache_dir(target: Path) -> Path:
    return _copilot_layout.recipe_cache_dir(target)


def copilot_state_path(target: Path) -> Path:
    return _copilot_layout.state_path(target)


def copilot_instructions_dir(target: Path) -> Path:
    return _copilot_layout.rules_dir(target)


def wrap_copilot_instructions(
    name: str, description: str, body: str, *, apply_to: str = "**"
) -> str:
    """Legacy wrapper - converts to dict format for new API."""
    recipe_dict = {"name": name, "description": description}
    return _copilot_layout.wrap_output(body, recipe_dict)


def write_copilot_state(target: Path, active_recipe: str) -> None:
    _copilot_layout.write_state(target, active_recipe)


def read_copilot_state(target: Path) -> dict | None:
    return _copilot_layout.read_state(target)


def _cleanup_copilot_on_zero_successes(target_root: Path) -> None:
    _copilot_layout.cleanup_on_zero_successes(target_root)


def install_all_copilot(
    base_dir: Path,
    target_root: Path,
    *,
    recipe_filter: str | None = None,
    recipe_list: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    return _copilot_layout.install_all(
        base_dir, target_root, recipe_filter=recipe_filter, recipe_list=recipe_list
    )


def set_active_copilot(base_dir: Path, target_root: Path, recipe_name: str) -> Path:
    """Point active persona at a cached recipe. Raises FileNotFoundError if cache missing."""
    cache_path = copilot_recipe_cache_dir(target_root) / (recipe_name + ".md")
    if not cache_path.is_file():
        msg = (
            "No cached Copilot recipe '{0}' at {1}. "
            "Run: personetta install '*' --format copilot"
        ).format(recipe_name, cache_path)
        raise FileNotFoundError(msg)

    dest = _copilot_layout._write_active_from_cache(target_root, recipe_name, base_dir)
    _copilot_layout.write_state(target_root, recipe_name)
    return dest


def ensure_copilot_baseline_router(base_dir: Path, target_root: Path) -> None:
    """Ensure baseline and router files exist if cache is non-empty."""
    inst_dir = copilot_instructions_dir(target_root)
    if (inst_dir / (COPILOT_BASELINE_STEM + COPILOT_INSTRUCTIONS_SUFFIX)).is_file():
        return
    names = list_cached_copilot_recipes(target_root)
    if not names:
        return
    inst_dir.mkdir(parents=True, exist_ok=True)
    rows = collect_recipe_router_rows(base_dir, names)
    router_body = build_plain_router_markdown(
        "copilot",
        rows,
        cache_glob="~/.personetta/copilot-recipes/",
        active_filename=COPILOT_ACTIVE_STEM + COPILOT_INSTRUCTIONS_SUFFIX,
    )
    baseline_body = build_plain_baseline_markdown(
        "copilot",
        host_product="GitHub Copilot in VS Code",
        cache_glob="~/.personetta/copilot-recipes/",
        active_filename=COPILOT_ACTIVE_STEM + COPILOT_INSTRUCTIONS_SUFFIX,
        router_filename=COPILOT_ROUTER_STEM + COPILOT_INSTRUCTIONS_SUFFIX,
    )
    (inst_dir / (COPILOT_ROUTER_STEM + COPILOT_INSTRUCTIONS_SUFFIX)).write_text(
        wrap_copilot_instructions(
            "Personetta - recipe router",
            "Recipe index and set-active commands (Personetta).",
            router_body,
        ),
        encoding="utf-8",
    )
    (inst_dir / (COPILOT_BASELINE_STEM + COPILOT_INSTRUCTIONS_SUFFIX)).write_text(
        wrap_copilot_instructions(
            "Personetta - baseline",
            "Cross-cutting Personetta rules for Copilot chat (always on).",
            baseline_body,
        ),
        encoding="utf-8",
    )


def install_single_copilot_recipe_to_cache(
    base_dir: Path,
    target_root: Path,
    recipe_name: str,
) -> Path:
    """Compose one recipe and write cache. Refresh active file if it is the active recipe."""
    # Ensure baseline exists
    ensure_copilot_baseline_router(base_dir, target_root)

    # Use base class method to compose and cache
    _ = _copilot_layout.install_single_recipe_to_cache(recipe_name, base_dir, target_root)

    # If this is the active recipe, refresh active file
    state = _copilot_layout.read_state(target_root)
    active = state.get("active_recipe") if state else None
    if active == recipe_name:
        _copilot_layout._write_active_from_cache(target_root, recipe_name, base_dir)

    cache_path = _copilot_layout.recipe_cache_dir(target_root) / (recipe_name + ".md")
    return cache_path


def list_cached_copilot_recipes(target_root: Path) -> list[str]:
    """List cached recipe names."""
    return _copilot_layout.list_cached_recipes(target_root)


# Constants for backward compatibility (actively used by commands.py)
ACTIVE_STEM = COPILOT_ACTIVE_STEM
BASELINE_STEM = COPILOT_BASELINE_STEM
ROUTER_STEM = COPILOT_ROUTER_STEM
INSTRUCTIONS_SUFFIX = COPILOT_INSTRUCTIONS_SUFFIX

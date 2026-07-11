"""Remove command - delete installed recipes from cache."""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from pathlib import Path

from generator.cli.commands._helpers import get_base_dir, resolve_install_target
from generator.claude_layout import (
    claude_recipe_cache_dir,
    install_all_claude,
    list_cached_claude_recipes,
    read_claude_state,
    set_active_claude,
)
from generator.cline_layout import (
    cline_recipe_cache_dir,
    install_all_cline,
    list_cached_cline_recipes,
    read_cline_state,
    set_active_cline,
)
from generator.copilot_layout import (
    copilot_recipe_cache_dir,
    install_all_copilot,
    list_cached_copilot_recipes,
    read_copilot_state,
    set_active_copilot,
)
from generator.cursor_layout import (
    cursor_recipe_cache_dir,
    list_cached_cursor_recipes,
    read_cursor_state,
    refresh_cursor_router_from_cache,
    set_active_cursor,
)


def _get_cursor_cache_and_state(target: Path) -> tuple[list[str], Path, str | None]:
    """Get Cursor cached recipes and state."""
    cached = list_cached_cursor_recipes(target)
    cache_dir = cursor_recipe_cache_dir(target)
    state = read_cursor_state(target)
    active = state.get("active_recipe") if state else None
    return cached, cache_dir, active


def _get_copilot_cache_and_state(target: Path) -> tuple[list[str], Path, str | None]:
    """Get Copilot cached recipes and state."""
    cached = list_cached_copilot_recipes(target)
    cache_dir = copilot_recipe_cache_dir(target)
    state = read_copilot_state(target)
    active = state.get("active_recipe") if state else None
    return cached, cache_dir, active


def _get_claude_cache_and_state(target: Path) -> tuple[list[str], Path, str | None]:
    """Get Claude cached recipes and state."""
    cached = list_cached_claude_recipes(target)
    cache_dir = claude_recipe_cache_dir(target)
    state = read_claude_state(target)
    active = state.get("active_recipe") if state else None
    return cached, cache_dir, active


def _get_cline_cache_and_state(target: Path) -> tuple[list[str], Path, str | None]:
    """Get Cline cached recipes and state."""
    cached = list_cached_cline_recipes(target)
    cache_dir = cline_recipe_cache_dir(target)
    state = read_cline_state(target)
    active = state.get("active_recipe") if state else None
    return cached, cache_dir, active


def _get_cached_recipes_and_state(
    fmt: str, target: Path
) -> tuple[list[str], Path, str | None]:
    """Get cached recipes, cache directory, and active recipe for format."""
    if fmt == "cursor":
        return _get_cursor_cache_and_state(target)
    elif fmt == "copilot":
        return _get_copilot_cache_and_state(target)
    elif fmt == "claude":
        return _get_claude_cache_and_state(target)
    elif fmt == "cline":
        return _get_cline_cache_and_state(target)
    else:
        raise ValueError(f"Unknown format: {fmt}")


def _match_recipes_by_patterns(
    cached_recipes: list[str], patterns: list[str]
) -> list[str]:
    """Filter cached recipes by glob patterns (case-insensitive)."""
    matched_recipes = []
    for recipe_name in cached_recipes:
        recipe_name_lower = recipe_name.lower()
        for pattern in patterns:
            pattern_lower = pattern.lower()
            if fnmatch.fnmatch(recipe_name_lower, pattern_lower):
                matched_recipes.append(recipe_name)
                break
    return matched_recipes


def _display_removal_candidates(
    fmt: str, matched_recipes: list[str], active_recipe: str | None
) -> None:
    """Display recipes that will be removed."""
    print(f"The following {len(matched_recipes)} recipe(s) will be removed:")
    for name in sorted(matched_recipes):
        marker = " (active)" if name == active_recipe else ""
        print(f"  {name}{marker}")
    print()


def _prompt_user_confirmation() -> bool:
    """Prompt user for confirmation."""
    try:
        response = input("Proceed with removal? [y/N]: ").strip().lower()
        if response not in ("y", "yes"):
            print("Cancelled.")
            return False
        return True
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        return False


def _confirm_removal(args: argparse.Namespace, cache_dir: Path, count: int) -> bool:
    """Confirm removal with user (unless --yes or --whatif)."""
    if getattr(args, "whatif", False):
        print(f"[WHATIF] Would remove {count} recipe(s) from {cache_dir}")
        print("No changes made (dry-run mode).")
        return False

    if args.yes:
        return True
    return _prompt_user_confirmation()


def _try_remove_file(recipe_file: Path) -> tuple[bool, str | None]:
    """Try to remove a single recipe file."""
    try:
        if recipe_file.exists():
            recipe_file.unlink()
            return True, None
        return False, "Recipe file not found"
    except Exception as exc:
        return False, str(exc)


def _handle_remove_success(recipe_name: str, removed: list[str]) -> None:
    """Handle successful file removal."""
    removed.append(recipe_name)
    print(f"Removed: {recipe_name}")


def _handle_remove_not_found(recipe_file: Path) -> None:
    """Handle file not found case."""
    print(f"[WARNING] Recipe file not found: {recipe_file}", file=sys.stderr)


def _handle_remove_failure(recipe_name: str, error: str, failed: list[str]) -> None:
    """Handle file removal failure."""
    failed.append(recipe_name)
    print(f"[ERROR] Failed to remove {recipe_name}: {error}", file=sys.stderr)


def _process_recipe_removal(
    recipe_name: str, cache_dir: Path, removed: list[str], failed: list[str]
) -> None:
    """Process removal of a single recipe file."""
    recipe_file = cache_dir / f"{recipe_name}.md"
    success, error = _try_remove_file(recipe_file)

    if success:
        _handle_remove_success(recipe_name, removed)
    elif error == "Recipe file not found":
        _handle_remove_not_found(recipe_file)
    else:
        # At this point, error is guaranteed to be str (not None)
        assert error is not None
        _handle_remove_failure(recipe_name, error, failed)


def _remove_recipe_files(
    matched_recipes: list[str], cache_dir: Path
) -> tuple[list[str], list[str]]:
    """Remove recipe files from cache directory."""
    removed: list[str] = []
    failed: list[str] = []
    for recipe_name in matched_recipes:
        _process_recipe_removal(recipe_name, cache_dir, removed, failed)
    return removed, failed


def _set_new_active(fmt: str, target: Path, new_active: str, base_dir: Path) -> None:
    """Set new active recipe for a format."""
    if fmt == "cursor":
        set_active_cursor(target, new_active, base_dir)
    elif fmt == "copilot":
        set_active_copilot(base_dir, target, new_active)
    elif fmt == "claude":
        set_active_claude(base_dir, target, new_active)
    elif fmt == "cline":
        set_active_cline(base_dir, target, new_active)


def _handle_active_removed_with_remaining(
    fmt: str,
    active_recipe: str,
    remaining_recipes: list[str],
    target: Path,
    base_dir: Path,
) -> None:
    """Handle active recipe removal when recipes remain."""
    new_active = sorted(remaining_recipes)[0]
    try:
        _set_new_active(fmt, target, new_active, base_dir)
        print(f"\nActive persona changed: {active_recipe} -> {new_active}")
    except Exception as exc:
        print(f"[WARNING] Failed to update active recipe: {exc}", file=sys.stderr)


def _get_state_filename(fmt: str) -> str:
    """Get state filename for a format."""
    state_file_map = {
        "cursor": "cursor-active.json",
        "copilot": "copilot-active.json",
        "claude": "claude-active.json",
        "cline": "cline-active.json",
    }
    return state_file_map[fmt]


def _clear_state_file(fmt: str, target: Path) -> None:
    """Clear the state file for a format."""
    state_file = target / ".personetta" / _get_state_filename(fmt)
    if not state_file.exists():
        return

    try:
        state_file.write_text(
            json.dumps({"active_recipe": ""}, indent=2), encoding="utf-8"
        )
    except Exception as exc:
        print(f"[WARNING] Failed to clear state file: {exc}", file=sys.stderr)


def _print_active_cleared_message() -> None:
    """Print message when active persona is cleared."""
    print("\nActive persona cleared (no recipes remain)")


def _handle_active_recipe_removal(
    fmt: str,
    active_recipe: str | None,
    removed: list[str],
    remaining_recipes: list[str],
    target: Path,
    base_dir: Path,
) -> None:
    """Handle active recipe if it was removed."""
    if active_recipe not in removed:
        return

    if remaining_recipes:
        _handle_active_removed_with_remaining(
            fmt, active_recipe, remaining_recipes, target, base_dir
        )
    else:
        _print_active_cleared_message()
        _clear_state_file(fmt, target)


def _regenerate_router_cursor(base_dir: Path, target: Path) -> None:
    """Regenerate Cursor router."""
    refresh_cursor_router_from_cache(base_dir, target)


def _regenerate_router_copilot(
    base_dir: Path, target: Path, remaining_recipes: list[str]
) -> None:
    """Regenerate Copilot router."""
    install_all_copilot(base_dir, target, recipe_list=remaining_recipes)


def _regenerate_router_claude(
    base_dir: Path, target: Path, remaining_recipes: list[str]
) -> None:
    """Regenerate Claude router."""
    install_all_claude(base_dir, target, recipe_list=remaining_recipes)


def _regenerate_router_cline(
    base_dir: Path, target: Path, remaining_recipes: list[str]
) -> None:
    """Regenerate Cline router."""
    install_all_cline(base_dir, target, recipe_list=remaining_recipes)


def _call_router_regenerator(
    fmt: str, base_dir: Path, target: Path, remaining_recipes: list[str]
) -> None:
    """Call the appropriate router regenerator for format."""
    if fmt == "cursor":
        _regenerate_router_cursor(base_dir, target)
    elif fmt == "copilot":
        _regenerate_router_copilot(base_dir, target, remaining_recipes)
    elif fmt == "claude":
        _regenerate_router_claude(base_dir, target, remaining_recipes)
    elif fmt == "cline":
        _regenerate_router_cline(base_dir, target, remaining_recipes)


def _regenerate_router_after_removal(
    fmt: str, remaining_recipes: list[str], base_dir: Path, target: Path
) -> None:
    """Regenerate router with remaining recipes."""
    if not remaining_recipes:
        return

    try:
        _call_router_regenerator(fmt, base_dir, target, remaining_recipes)
        print(f"Router regenerated with {len(remaining_recipes)} recipe(s)")
    except Exception as exc:
        print(f"[WARNING] Failed to regenerate router: {exc}", file=sys.stderr)


def _print_removal_error(removed: list[str]) -> int:
    """Print error when no recipes were removed."""
    print("No recipes were removed.", file=sys.stderr)
    return 1


def _print_removal_success(removed: list[str], cache_dir: Path) -> None:
    """Print successful removal summary."""
    print(f"\nRemoved {len(removed)} recipe(s) from {cache_dir}")


def _print_removal_failures(failed: list[str]) -> int:
    """Print removal failure summary."""
    print(
        f"Failed to remove {len(failed)} recipe(s): {', '.join(failed)}",
        file=sys.stderr,
    )
    return 1


def _display_removal_summary(
    removed: list[str], failed: list[str], cache_dir: Path
) -> int:
    """Display removal summary and return exit code."""
    if not removed:
        return _print_removal_error(removed)

    _print_removal_success(removed, cache_dir)

    if failed:
        return _print_removal_failures(failed)
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    """Remove installed recipes matching one or more glob patterns."""
    base_dir = get_base_dir()
    target = resolve_install_target(args.target)
    fmt = args.format

    try:
        cached_recipes, cache_dir, active_recipe = _get_cached_recipes_and_state(
            fmt, target
        )
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    if not cached_recipes:
        print(f"No {fmt} recipes installed at {target}", file=sys.stderr)
        return 1

    matched_recipes = _match_recipes_by_patterns(cached_recipes, args.patterns)

    if not matched_recipes:
        print(
            f"No installed {fmt} recipes matched patterns: {', '.join(args.patterns)}",
            file=sys.stderr,
        )
        print(f"\nInstalled {fmt} recipes:", file=sys.stderr)
        for name in sorted(cached_recipes):
            print(f"  {name}", file=sys.stderr)
        return 1

    _display_removal_candidates(fmt, matched_recipes, active_recipe)

    if not _confirm_removal(args, cache_dir, len(matched_recipes)):
        return 0

    removed, failed = _remove_recipe_files(matched_recipes, cache_dir)
    remaining_recipes = [r for r in cached_recipes if r not in removed]

    _handle_active_recipe_removal(
        fmt, active_recipe, removed, remaining_recipes, target, base_dir
    )
    _regenerate_router_after_removal(fmt, remaining_recipes, base_dir, target)

    return _display_removal_summary(removed, failed, cache_dir)

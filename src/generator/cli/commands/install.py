"""Install command - install recipes to format-specific caches."""

from __future__ import annotations

import argparse
import fnmatch
import sys
from pathlib import Path

from generator.cli.commands._helpers import (
    emit_cursor_user_sync,
    get_base_dir,
    resolve_install_target,
)
from generator.loader import list_recipes
from generator.cursor_layout import (
    ACTIVE_FILENAME,
    BASELINE_FILENAME,
    ROUTER_FILENAME,
    cursor_recipe_cache_dir,
    install_all_cursor,
)
from generator.claude_layout import (
    ACTIVE_NAME as CLAUDE_ACTIVE_NAME,
    BASELINE_NAME as CLAUDE_BASELINE_NAME,
    ROUTER_NAME as CLAUDE_ROUTER_NAME,
    claude_recipe_cache_dir,
    install_all_claude,
)
from generator.claude_skills_install import publish_claude_skills
from generator.copilot_layout import (
    ACTIVE_STEM as COPILOT_ACTIVE_STEM,
    BASELINE_STEM as COPILOT_BASELINE_STEM,
    INSTRUCTIONS_SUFFIX,
    ROUTER_STEM as COPILOT_ROUTER_STEM,
    copilot_instructions_dir,
    copilot_recipe_cache_dir,
    install_all_copilot,
)
from generator.copilot_skills_install import publish_copilot_skills
from generator.cline_layout import (
    ACTIVE_NAME as CLINE_ACTIVE_NAME,
    BASELINE_NAME as CLINE_BASELINE_NAME,
    ROUTER_NAME as CLINE_ROUTER_NAME,
    cline_global_rules_dir,
    cline_recipe_cache_dir,
    install_all_cline,
)
from generator.cursor_skills_install import publish_cursor_skills
from generator.provisions import apply_provision, load_provisions


def _apply_enabled_provisions(base_dir: Path, target: Path, fmt: str) -> None:
    """Apply enabled provisions that target ``fmt`` after a successful install.

    Deploy-dark: nothing is enabled by default, so this is a no-op until the user
    opts in via ``personetta provision enable``. Output is printed only when a
    provision actually targets this tool, to avoid noise on normal installs.
    """
    config = load_provisions(base_dir, target)
    selected = [p for p in config.enabled_provisions() if fmt in p.targets]
    if not selected:
        return
    print("\nApplying enabled provisions for {0}:".format(fmt))
    for provision in selected:
        for res in apply_provision(provision, target, dry_run=False):
            print("  {0:24s} {1:18s} {2}".format(res.provision, res.status, res.detail))


def _match_recipes_for_install(
    patterns: list[str], all_recipes: list[dict]
) -> list[dict]:
    """Match recipes by patterns (case-insensitive).

    Args:
        patterns: Recipe name patterns (glob-style)
        all_recipes: List of all available recipes

    Returns:
        List of matched recipe dicts
    """
    matched = []
    for recipe in all_recipes:
        recipe_name_lower = recipe["name"].lower()
        for pattern in patterns:
            pattern_lower = pattern.lower()
            if fnmatch.fnmatch(recipe_name_lower, pattern_lower):
                matched.append(recipe)
                break  # Don't add the same recipe multiple times
    return matched


def _print_whatif_cursor(recipe_names: list[str], target: Path) -> None:
    """Print whatif output for Cursor install."""
    cache_root = cursor_recipe_cache_dir(target)
    rules_dir = target / ".cursor" / "rules"
    print("\nWould install to:")
    print(f"  Cache: {cache_root}")
    print(f"  Rules: {rules_dir}")


def _print_whatif_copilot(recipe_names: list[str], target: Path) -> None:
    """Print whatif output for Copilot install."""
    cache_root = copilot_recipe_cache_dir(target)
    inst_dir = copilot_instructions_dir(target)
    print("\nWould install to:")
    print(f"  Cache: {cache_root}")
    print(f"  Instructions: {inst_dir}")


def _print_whatif_claude(recipe_names: list[str], target: Path) -> None:
    """Print whatif output for Claude install."""
    cache_root = claude_recipe_cache_dir(target)
    print(f"\nWould install to: {cache_root}")


def _print_whatif_cline(recipe_names: list[str], target: Path) -> None:
    """Print whatif output for Cline install."""
    cache_root = cline_recipe_cache_dir(target)
    print(f"\nWould install to: {cache_root}")


def _print_whatif_install(recipe_names: list[str], fmt: str, target: Path) -> None:
    """Print whatif output for install command.

    Args:
        recipe_names: List of recipe names
        fmt: Format name
        target: Install target directory
    """
    print(f"[WHATIF] Would install {len(recipe_names)} recipe(s) for {fmt}:")
    for name in sorted(recipe_names):
        print(f"  {name}")

    if fmt == "cursor":
        _print_whatif_cursor(recipe_names, target)
    elif fmt == "copilot":
        _print_whatif_copilot(recipe_names, target)
    elif fmt == "claude":
        _print_whatif_claude(recipe_names, target)
    elif fmt == "cline":
        _print_whatif_cline(recipe_names, target)


def _print_installed_recipes(ok: list[str], cache_root: Path) -> None:
    """Print list of installed recipes."""
    for name in sorted(ok):
        print(f"  {name:40s} -> {cache_root / (name + '.md')}")


def _publish_cursor_skills_if_needed(base_dir: Path) -> None:
    """Publish Cursor skills globally."""
    published = publish_cursor_skills(base_dir)
    if published:
        skills_root = Path.home() / ".cursor" / "skills"
        print(f"\nInstalled Cursor skills globally -> {skills_root}")
        for name in sorted(published):
            print(f"  {name}")


def _publish_copilot_skills_if_needed(base_dir: Path) -> None:
    """Publish Copilot skills to extension."""
    published = publish_copilot_skills(base_dir)
    if published:
        vscode_ext_dir = Path.home() / ".vscode" / "extensions"
        copilot_exts = sorted(vscode_ext_dir.glob("github.copilot-chat-*"))
        if copilot_exts:
            skills_root = copilot_exts[-1] / "assets" / "prompts" / "skills"
            print(f"\nInstalled Copilot skills -> {skills_root}")
            for name in sorted(published):
                print(f"  {name}")


def _publish_claude_skills_if_needed(base_dir: Path) -> None:
    """Publish Claude skills globally."""
    published = publish_claude_skills(base_dir)
    if published:
        skills_root = Path.home() / ".claude" / "skills"
        print(f"\nInstalled Claude skills globally -> {skills_root}")
        for name in sorted(published):
            print(f"  {name}")


def _install_cursor_format(base_dir: Path, target: Path, recipe_names: list[str]) -> int:
    """Install for Cursor format.

    Returns:
        Exit code (0 = success, 1 = error)
    """
    ok, bad = install_all_cursor(base_dir, target, recipe_list=recipe_names)
    cache_root = cursor_recipe_cache_dir(target)
    rules_dir = target / ".cursor" / "rules"

    _print_installed_recipes(ok, cache_root)

    if ok:
        print(f"  {BASELINE_FILENAME:40s} -> {rules_dir / BASELINE_FILENAME}")
        print(f"  {ROUTER_FILENAME:40s} -> {rules_dir / ROUTER_FILENAME}")
        print(
            f"  {ACTIVE_FILENAME:40s} -> {rules_dir / ACTIVE_FILENAME} "
            f"(default persona: {sorted(ok)[0]})"
        )

    for name in bad:
        print(f"[ERROR] Skipped (conflicts): {name}", file=sys.stderr)

    print(
        f"\nInstalled Cursor: baseline + router + active persona + "
        f"{len(ok)} cached recipe(s) under {target}"
    )

    if not ok:
        return 1
    if bad:
        print(f"Skipped {len(bad)} recipe(s) due to conflicts.", file=sys.stderr)
        return 1

    emit_cursor_user_sync(target)
    _publish_cursor_skills_if_needed(base_dir)
    return 0


def _install_copilot_format(base_dir: Path, target: Path, recipe_names: list[str]) -> int:
    """Install for Copilot format.

    Returns:
        Exit code (0 = success, 1 = error)
    """
    ok, bad = install_all_copilot(base_dir, target, recipe_list=recipe_names)
    cache_root = copilot_recipe_cache_dir(target)
    inst_dir = copilot_instructions_dir(target)

    for name in sorted(ok):
        print(f"  {name:40s} -> {cache_root / (name + '.md')}")

    if ok:
        print(
            f"  {COPILOT_BASELINE_STEM + INSTRUCTIONS_SUFFIX:40s} -> "
            f"{inst_dir / (COPILOT_BASELINE_STEM + INSTRUCTIONS_SUFFIX)}"
        )
        print(
            f"  {COPILOT_ROUTER_STEM + INSTRUCTIONS_SUFFIX:40s} -> "
            f"{inst_dir / (COPILOT_ROUTER_STEM + INSTRUCTIONS_SUFFIX)}"
        )
        print(
            f"  {COPILOT_ACTIVE_STEM + INSTRUCTIONS_SUFFIX:40s} -> "
            f"{inst_dir / (COPILOT_ACTIVE_STEM + INSTRUCTIONS_SUFFIX)} "
            f"(default persona: {sorted(ok)[0]})"
        )

    for name in bad:
        print(f"[ERROR] Skipped (conflicts): {name}", file=sys.stderr)

    print(
        f"\nInstalled Copilot: baseline + router + active + "
        f"{len(ok)} cached recipe(s) under {target}"
    )

    if not ok:
        return 1
    if bad:
        print(f"Skipped {len(bad)} recipe(s) due to conflicts.", file=sys.stderr)
        return 1

    _publish_copilot_skills_if_needed(base_dir)
    return 0


def _install_claude_format(base_dir: Path, target: Path, recipe_names: list[str]) -> int:
    """Install for Claude format.

    Returns:
        Exit code (0 = success, 1 = error)
    """
    ok, bad = install_all_claude(base_dir, target, recipe_list=recipe_names)
    cache_root = claude_recipe_cache_dir(target)
    rules_dir = target / ".claude" / "rules"

    for name in sorted(ok):
        print(f"  {name:40s} -> {cache_root / (name + '.md')}")

    if ok:
        print(f"  {CLAUDE_BASELINE_NAME:40s} -> {rules_dir / CLAUDE_BASELINE_NAME}")
        print(f"  {CLAUDE_ROUTER_NAME:40s} -> {rules_dir / CLAUDE_ROUTER_NAME}")
        print(
            f"  {CLAUDE_ACTIVE_NAME:40s} -> {rules_dir / CLAUDE_ACTIVE_NAME} "
            f"(default persona: {sorted(ok)[0]})"
        )

    for name in bad:
        print(f"[ERROR] Skipped (conflicts): {name}", file=sys.stderr)

    print(
        f"\nInstalled Claude Code rules: baseline + router + active + "
        f"{len(ok)} cached recipe(s) under {target}"
    )

    if not ok:
        return 1
    if bad:
        print(f"Skipped {len(bad)} recipe(s) due to conflicts.", file=sys.stderr)
        return 1

    _publish_claude_skills_if_needed(base_dir)
    return 0


def _install_cline_format(base_dir: Path, target: Path, recipe_names: list[str]) -> int:
    """Install for Cline format.

    Returns:
        Exit code (0 = success, 1 = error)
    """
    ok, bad = install_all_cline(base_dir, target, recipe_list=recipe_names)
    cache_root = cline_recipe_cache_dir(target)
    rules_dir = cline_global_rules_dir(target)

    for name in sorted(ok):
        print(f"  {name:40s} -> {cache_root / (name + '.md')}")

    if ok:
        print(f"  {CLINE_BASELINE_NAME:40s} -> {rules_dir / CLINE_BASELINE_NAME}")
        print(f"  {CLINE_ROUTER_NAME:40s} -> {rules_dir / CLINE_ROUTER_NAME}")
        print(
            f"  {CLINE_ACTIVE_NAME:40s} -> {rules_dir / CLINE_ACTIVE_NAME} "
            f"(default persona: {sorted(ok)[0]})"
        )

    for name in bad:
        print(f"[ERROR] Skipped (conflicts): {name}", file=sys.stderr)

    print(
        f"\nInstalled Cline global rules: baseline + router + active + "
        f"{len(ok)} cached recipe(s) under {target}"
    )

    if not ok:
        return 1
    if bad:
        print(f"Skipped {len(bad)} recipe(s) due to conflicts.", file=sys.stderr)
        return 1

    return 0


def cmd_install(args: argparse.Namespace) -> int:
    """Install recipes matching one or more glob patterns.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    base_dir = get_base_dir()
    target = resolve_install_target(args.target)

    # Get all recipes
    all_recipes = list_recipes(base_dir)

    # Match recipes by patterns
    matched_recipes = _match_recipes_for_install(args.patterns, all_recipes)

    if not matched_recipes:
        print(f"No recipes matched patterns: {', '.join(args.patterns)}", file=sys.stderr)
        print("\nUse 'personetta list' to see available recipes.", file=sys.stderr)
        return 1

    # Extract recipe names for install
    recipe_names = [r["name"] for r in matched_recipes]

    # Handle --whatif mode
    if getattr(args, "whatif", False):
        _print_whatif_install(recipe_names, args.format, target)
        return 0

    # Install using format-specific handlers
    handlers = {
        "cursor": _install_cursor_format,
        "copilot": _install_copilot_format,
        "claude": _install_claude_format,
        "cline": _install_cline_format,
    }
    handler = handlers.get(args.format)
    if handler is None:
        raise RuntimeError(f"Unhandled install format: {args.format}")

    rc = handler(base_dir, target, recipe_names)
    if rc == 0:
        _apply_enabled_provisions(base_dir, target, args.format)
    return rc

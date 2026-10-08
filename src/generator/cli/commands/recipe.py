"""Recipe command - generate and optionally install a formatted recipe."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from generator.cli.commands._helpers import (
    emit_cursor_user_sync,
    get_base_dir,
    resolve_install_target,
)
from generator.loader import load_merge_config, load_recipe, load_recipe_roles
from generator.merger import compose_recipe
from generator.output_formats import format_role
from generator.recipe_export import export_recipe, render_export
from generator.cursor_layout import install_single_cursor_recipe_to_cache
from generator.copilot_layout import install_single_copilot_recipe_to_cache
from generator.claude_layout import install_single_claude_recipe_to_cache
from generator.cline_layout import install_single_cline_recipe_to_cache
from generator.installer import install_output


def _load_and_compose_recipe(recipe_name: str, base_dir: Path) -> tuple[dict, list]:
    """Load recipe, compose it, and return composed recipe with warnings.

    Returns:
        Tuple of (composed_recipe_dict, warnings_list)
    """
    recipe = load_recipe(recipe_name, base_dir)
    compose_roles, mixin_roles = load_recipe_roles(recipe, base_dir)
    merge_config = load_merge_config(base_dir)

    composed, warnings = compose_recipe(recipe, compose_roles, mixin_roles, merge_config)
    return composed, warnings


def _print_warnings(warnings: list) -> int:
    """Print warnings and return error count.

    Returns:
        Number of errors found (0 if none)
    """
    for w in warnings:
        label = (
            "ERROR"
            if w.severity == "error"
            else "WARNING" if w.severity == "warning" else "INFO"
        )
        print(f"[{label}] {w.message}", file=sys.stderr)

    errors = [w for w in warnings if w.severity == "error"]
    return len(errors)


def _install_to_cache(fmt: str, base_dir: Path, target: Path, recipe_name: str) -> Path:
    """Install recipe to format-specific cache and return destination path.

    Args:
        fmt: Output format (cursor, copilot, claude, cline)
        base_dir: Base directory for recipes
        target: Installation target directory
        recipe_name: Name of recipe to install

    Returns:
        Destination path as Path object

    Raises:
        ValueError: If format-specific installation fails
    """
    if fmt == "cursor":
        dest = install_single_cursor_recipe_to_cache(base_dir, target, recipe_name)
        emit_cursor_user_sync(target)
        return dest
    elif fmt == "copilot":
        return install_single_copilot_recipe_to_cache(base_dir, target, recipe_name)
    elif fmt == "claude":
        return install_single_claude_recipe_to_cache(base_dir, target, recipe_name)
    elif fmt == "cline":
        return install_single_cline_recipe_to_cache(base_dir, target, recipe_name)
    else:
        return install_output(format_role({}, fmt), fmt, recipe_name, target)


def _cmd_recipe_json(args: argparse.Namespace, base_dir: Path) -> int:
    """Write the self-contained JSON export (stdout, or -o file)."""
    if args.install:
        print("[ERROR] --install does not support --format json", file=sys.stderr)
        return 1
    document, warnings = export_recipe(args.name, base_dir)
    if _print_warnings(warnings) > 0:
        print("Conflict(s) detected. Fix before exporting this recipe.", file=sys.stderr)
        return 1
    text = render_export(document)
    if not args.output:
        # UTF-8 regardless of the console code page (the export contains non-ASCII)
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.write(text)
        return 0
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8", newline="\n")
    print(f"Written to {out_path}")
    return 0


def cmd_recipe(args: argparse.Namespace) -> int:
    """Generate recipe output in specified format.

    Args:
        args: Parsed command-line arguments with:
            - name: Recipe name
            - format: Output format
            - install: Whether to install to cache
            - output: Output file path (optional)
            - target: Installation target (optional)

    Returns:
        Exit code (0 for success, 1 for error)
    """
    base_dir = get_base_dir()

    if args.format == "json":
        return _cmd_recipe_json(args, base_dir)

    # Load and compose recipe
    composed, warnings = _load_and_compose_recipe(args.name, base_dir)

    # Handle warnings and errors
    error_count = _print_warnings(warnings)
    if error_count > 0:
        print(
            f"\n{error_count} conflict(s) detected. Fix before using this recipe.",
            file=sys.stderr,
        )
        return 1

    # Format output
    output = format_role(composed, args.format)

    # Handle installation
    if args.install:
        target = resolve_install_target(args.target)
        try:
            # Use args.name instead of composed["name"] since composed uses "_recipe_name"
            dest = _install_to_cache(args.format, base_dir, target, args.name)
            cache_type = (
                "cache"
                if args.format in ("cursor", "copilot", "claude", "cline")
                else "location"
            )
            print(f"Updated {args.format.capitalize()} {cache_type}: {dest}")
        except ValueError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 1
    elif args.output:
        # Write to file
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"Written to {out_path}")
    else:
        # Print to stdout
        print(output)

    return 0

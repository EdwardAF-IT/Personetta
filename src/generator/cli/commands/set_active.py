"""Set-active command - switch the active persona for a format."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from generator.cli.commands._helpers import (
    emit_cursor_user_sync,
    get_base_dir,
    resolve_install_target,
)
from generator.format_resolver import (
    UNDETERMINED_FORMAT_ERROR,
    resolve_format,
    resolution_note,
)
from generator.cursor_layout import ACTIVE_FILENAME, set_active_cursor
from generator.copilot_layout import (
    ACTIVE_STEM as COPILOT_ACTIVE_STEM,
    INSTRUCTIONS_SUFFIX,
    copilot_instructions_dir,
    set_active_copilot,
)
from generator.claude_layout import (
    ACTIVE_NAME as CLAUDE_ACTIVE_NAME,
    set_active_claude,
)
from generator.cline_layout import set_active_cline


def _get_active_file_path(fmt: str, target: Path) -> Path:
    """Get the active file path for a given format.

    Args:
        fmt: Output format (cursor, copilot, claude, cline)
        target: Installation target directory

    Returns:
        Path to active file

    Raises:
        RuntimeError: If format is unknown
    """
    if fmt == "cursor":
        return target / ".cursor" / "rules" / ACTIVE_FILENAME
    elif fmt == "copilot":
        return copilot_instructions_dir(target) / (
            COPILOT_ACTIVE_STEM + INSTRUCTIONS_SUFFIX
        )
    elif fmt == "claude":
        return target / ".claude" / "rules" / CLAUDE_ACTIVE_NAME
    elif fmt == "cline":
        return target / ".cline" / "rules" / "personetta-active.md"
    else:
        raise RuntimeError(f"Unknown format: {fmt}")


def _set_active_for_format(
    fmt: str, target: Path, recipe_name: str, base_dir: Path
) -> Path:
    """Set active persona for specific format and return destination path.

    Args:
        fmt: Output format (cursor, copilot, claude, cline)
        target: Installation target directory
        recipe_name: Recipe name to activate
        base_dir: Base directory for recipes

    Returns:
        Destination path where active file was written

    Raises:
        RuntimeError: If format is unknown
        FileNotFoundError: If recipe cache file not found
    """
    if fmt == "cursor":
        dest = set_active_cursor(target, recipe_name, base_dir)
        emit_cursor_user_sync(target)
        return dest
    elif fmt == "copilot":
        return set_active_copilot(base_dir, target, recipe_name)
    elif fmt == "claude":
        return set_active_claude(base_dir, target, recipe_name)
    elif fmt == "cline":
        return set_active_cline(base_dir, target, recipe_name)
    else:
        raise RuntimeError(f"Unhandled set-active format: {fmt}")


def cmd_set_active(args: argparse.Namespace) -> int:
    """Set the active persona for a given format.

    When ``--format`` is omitted the target is resolved from the host agent
    (inside a chat), then ``FAB_DEFAULT_FORMAT``, then the sole installed format;
    if still ambiguous the command requires an explicit ``--format``.

    Args:
        args: Parsed command-line arguments with:
            - name: Recipe name to activate
            - format: Output format (optional; resolved when omitted)
            - target: Installation target (optional)
            - whatif: Dry-run mode (optional)

    Returns:
        Exit code (0 for success, 1 for error)
    """
    target = resolve_install_target(args.target)
    resolution = resolve_format(getattr(args, "format", None), target)
    if resolution.format is None:
        print(f"[ERROR] {UNDETERMINED_FORMAT_ERROR}", file=sys.stderr)
        return 1
    fmt = resolution.format
    note = resolution_note(resolution)
    if note:
        print(note)
    base_dir = get_base_dir()

    # Handle --whatif mode
    if getattr(args, "whatif", False):
        print(f"[WHATIF] Would set active {fmt} persona to: {args.name}")
        try:
            dest = _get_active_file_path(fmt, target)
            print(f"Would update: {dest}")
            return 0
        except RuntimeError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 1

    # Set active persona
    try:
        dest = _set_active_for_format(fmt, target, args.name, base_dir)
        print(f"Active {fmt.capitalize()} persona -> {dest} (recipe: {args.name})")
        return 0
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

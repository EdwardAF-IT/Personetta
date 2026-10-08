"""Set-active command - switch the active persona for a format."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from generator.worktree import git_context
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
        # A project/worktree target reuses the user-wide recipe cache.
        return set_active_claude(base_dir, target, recipe_name, user_cache_fallback=True)
    elif fmt == "cline":
        return set_active_cline(base_dir, target, recipe_name)
    else:
        raise RuntimeError(f"Unhandled set-active format: {fmt}")


EXIT_REFUSED = 2


def _targets_global(raw_target: list[str] | None, target: Path) -> bool:
    """True when the resolved install root is the user-wide home directory."""
    if raw_target is not None and raw_target[0] != "global":
        return False
    return target.resolve() == Path.home().resolve()


def _worktree_project_root(raw_target: list[str] | None, target: Path) -> Path:
    """Bare ``--target project`` means the checkout root, not the current subdirectory."""
    if raw_target != ["project"]:
        return target
    context = git_context(target)
    return context.root if context else target


def _refuse_global_in_worktree(args: argparse.Namespace, target: Path) -> bool:
    """Print the refusal and return True when a global write would leak across worktrees."""
    if getattr(args, "use_global", False):
        return False
    if not _targets_global(args.target, target):
        return False
    context = git_context(Path.cwd())
    if context is None or not context.is_linked_worktree:
        return False
    print(
        "[ERROR] Refusing to write the machine-global active persona from inside "
        f"the git worktree {context.root}: every worktree would share it. "
        "Use '--target project' for this worktree's own .claude/rules, "
        "or pass '--global' to write the global file anyway.",
        file=sys.stderr,
    )
    return True


def cmd_set_active(args: argparse.Namespace) -> int:
    """Set the active persona for a given format.

    When ``--format`` is omitted the target is resolved from the host agent
    (inside a chat), then ``FAB_DEFAULT_FORMAT``, then the sole installed format;
    if still ambiguous the command requires an explicit ``--format``.

    Args:
        args: Parsed command-line arguments with:
            - name: Recipe name to activate
            - format: Output format (optional; resolved when omitted)
            - target: Installation target (optional); ``project`` = this checkout
            - use_global: Allow the global file from inside a linked git worktree
            - whatif: Dry-run mode (optional)

    Returns:
        Exit code (0 success, 1 error, 2 refused: global write from a worktree)
    """
    target = _worktree_project_root(args.target, resolve_install_target(args.target))
    if _refuse_global_in_worktree(args, target):
        return EXIT_REFUSED
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

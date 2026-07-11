"""Current command - report the active Personetta recipe for an agent.

Reads the per-format state file under ``~/.personetta/<format>-active.json``,
so it works without a Personetta repository. When ``--format`` is omitted the
host agent is auto-detected (Cursor, Claude Code, or Copilot).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from generator.cli.commands._helpers import resolve_install_target
from generator.format_resolver import (
    UNDETERMINED_FORMAT_ERROR,
    resolve_format,
    resolution_note,
)


def _state_file(target: Path, fmt: str) -> Path:
    """Return the path to the active-recipe state file for a format."""
    return target / ".personetta" / "{0}-active.json".format(fmt)


def _read_active_recipe(state_file: Path) -> Optional[str]:
    """Return the active recipe id from a state file, or None if unavailable."""
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    recipe = data.get("active_recipe")
    return recipe if isinstance(recipe, str) and recipe else None


def cmd_current(args: argparse.Namespace) -> int:
    """Print the active recipe id for the resolved format.

    Args:
        args: Parsed arguments with optional ``format`` and ``target``.

    Returns:
        Exit code (0 when an active recipe is reported, 1 otherwise).
    """
    target = resolve_install_target(getattr(args, "target", None))
    resolution = resolve_format(getattr(args, "format", None), target)
    if resolution.format is None:
        print(f"[ERROR] {UNDETERMINED_FORMAT_ERROR}", file=sys.stderr)
        return 1
    fmt = resolution.format
    note = resolution_note(resolution)
    if note:
        print(note)

    state_file = _state_file(target, fmt)
    recipe = _read_active_recipe(state_file)
    if recipe is None:
        print(
            "No active {0} recipe. Run: personetta install '*' --format {0}".format(fmt)
        )
        return 1

    print("Active {0} recipe: {1}".format(fmt, recipe))
    return 0

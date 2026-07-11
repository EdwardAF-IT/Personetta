"""Detect which AI coding agent is hosting the current process.

A Personetta skill invoked inside an agent chat should target that agent by
default: running ``set-active`` from a Cursor chat should mean ``--format
cursor``, from Claude Code ``--format claude``, and from GitHub Copilot
``--format copilot``. Each harness exports an environment marker on the
subprocesses it spawns, which lets the CLI infer the host and default
``--format`` instead of forcing the user (or skill) to pass it.

Markers (most- to least-specific):

* ``CLAUDECODE`` / ``CLAUDE_CODE_CHILD_SESSION`` -> Claude Code.
* ``COPILOT_AGENT`` (or cross-vendor ``AI_AGENT=...copilot...``) -> GitHub Copilot.
* ``CURSOR_AGENT`` -> Cursor.

Claude/Copilot markers are only set when that harness itself spawns the process,
so they take precedence over the editor-level ``CURSOR_AGENT`` marker (Claude or
Copilot can run inside a Cursor-integrated terminal).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Optional

# Values that mean "marker is off"; anything else non-empty counts as set.
_FALSEY = frozenset({"", "0", "false", "no", "off"})


def _is_set(value: Optional[str]) -> bool:
    """Return True when an environment marker is present and not falsey."""
    if value is None:
        return False
    return value.strip().lower() not in _FALSEY


def detect_host_format(env: Optional[Mapping[str, str]] = None) -> Optional[str]:
    """Infer the hosting agent's Personetta format from environment markers.

    Args:
        env: Environment mapping to inspect (defaults to ``os.environ``).

    Returns:
        One of ``"claude"``, ``"copilot"``, ``"cursor"``, or ``None`` when no
        host could be determined.
    """
    environ = os.environ if env is None else env

    if _is_set(environ.get("CLAUDECODE")) or _is_set(
        environ.get("CLAUDE_CODE_CHILD_SESSION")
    ):
        return "claude"

    ai_agent = (environ.get("AI_AGENT") or "").lower()
    if _is_set(environ.get("COPILOT_AGENT")) or "copilot" in ai_agent:
        return "copilot"

    if _is_set(environ.get("CURSOR_AGENT")):
        return "cursor"

    return None

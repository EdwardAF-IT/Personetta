"""Resolve which tool/format a command should target.

Two distinct contexts need a target format:

* **Inside an agent chat** (Cursor, Claude Code, Copilot) the host exports an
  environment marker, so :func:`generator.host_detect.detect_host_format` can
  infer it - the user need not pass ``--format``.
* **At a plain command line** no host marker exists. Rather than always failing,
  fall back to a configured default (``FAB_DEFAULT_FORMAT``) or, when the user
  has installed exactly one tool, that sole format. Only when the target is
  genuinely ambiguous do we require an explicit ``--format``.

Resolution order (first match wins):

1. ``explicit`` - the ``--format`` flag.
2. ``host`` - detected host agent.
3. ``env-default`` - ``FAB_DEFAULT_FORMAT`` (must be a known format).
4. ``sole-install`` - the only format with installed recipes under ``target``.
5. ``none`` - undetermined; the caller should require ``--format``.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from generator.host_detect import detect_host_format
from generator.output_formats import FORMAT_NAMES

DEFAULT_FORMAT_ENV = "FAB_DEFAULT_FORMAT"

# Error shown when no format could be resolved; mentions --format so callers and
# tests have a single, consistent remediation message.
UNDETERMINED_FORMAT_ERROR = (
    "Could not determine the target tool. "
    "Pass --format {cursor|claude|copilot|cline} or set FAB_DEFAULT_FORMAT."
)

_NOTE_TEMPLATES = {
    "host": "Detected host agent -> {fmt} (no --format given)",
    "env-default": "Using FAB_DEFAULT_FORMAT -> {fmt} (no --format given)",
    "sole-install": (
        "No host agent detected; defaulting to the only installed format "
        "-> {fmt}. Override with --format."
    ),
}


@dataclass(frozen=True)
class FormatResolution:
    """Outcome of resolving a target format.

    Attributes:
        format: Resolved format name, or None when undetermined.
        source: How it was resolved (``explicit``, ``host``, ``env-default``,
            ``sole-install``, or ``none``).
    """

    format: Optional[str]
    source: str


def resolution_note(resolution: "FormatResolution") -> Optional[str]:
    """Return a one-line note explaining a non-explicit resolution, else None."""
    template = _NOTE_TEMPLATES.get(resolution.source)
    if template and resolution.format:
        return template.format(fmt=resolution.format)
    return None


def installed_formats(target: Path) -> list[str]:
    """Return formats that have a non-empty recipe cache under ``target``.

    A format is considered "installed" when ``~/.personetta/<fmt>-recipes``
    exists and contains at least one entry, which is the state ``install``
    leaves behind for every tool (including Cursor).
    """
    cache_root = target / ".personetta"
    found: list[str] = []
    for name in FORMAT_NAMES:
        cache_dir = cache_root / "{0}-recipes".format(name)
        if cache_dir.is_dir() and any(cache_dir.iterdir()):
            found.append(name)
    return found


def _configured_default(env: Mapping[str, str]) -> Optional[str]:
    """Return a valid FAB_DEFAULT_FORMAT value, or None when unset/invalid."""
    configured = (env.get(DEFAULT_FORMAT_ENV) or "").strip().lower()
    return configured if configured in FORMAT_NAMES else None


def resolve_format(
    explicit: Optional[str],
    target: Path,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> FormatResolution:
    """Resolve the target format from flag, host, config, then install state.

    Args:
        explicit: The ``--format`` value (None when omitted).
        target: Install root used to inspect installed formats.
        env: Environment mapping (defaults to ``os.environ``).

    Returns:
        A :class:`FormatResolution` describing the format and how it was chosen.
    """
    if explicit:
        return FormatResolution(explicit, "explicit")

    environ = os.environ if env is None else env

    host = detect_host_format(environ)
    if host:
        return FormatResolution(host, "host")

    configured = _configured_default(environ)
    if configured:
        return FormatResolution(configured, "env-default")

    installed = installed_formats(target)
    if len(installed) == 1:
        return FormatResolution(installed[0], "sole-install")

    return FormatResolution(None, "none")

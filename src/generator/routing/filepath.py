"""Map a file path to the recipe for its language (file-routed activation).

Uses the same extension table as ``route --json`` language detection, so the
hook and the CLI agree on what counts as C#, JavaScript/TypeScript, Python,
PowerShell and T-SQL.
"""

from __future__ import annotations

from pathlib import Path

from generator.routing.context import DEFAULT_LIFECYCLE, LIFECYCLES, language_for_name


def language_for_path(path: Path) -> str | None:
    """Canonical language of ``path`` by extension, or ``None`` if unknown."""
    return language_for_name(path.name)


def recipe_for_path(path: Path, lifecycle: str | None = None) -> str | None:
    """Recipe name ``<lifecycle>-<language>`` for ``path``; unknown lifecycle -> default."""
    language = language_for_path(path)
    if language is None:
        return None
    chosen = lifecycle if lifecycle in LIFECYCLES else DEFAULT_LIFECYCLE
    return f"{chosen}-{language}"

"""Git worktree detection: which checkout a path belongs to, and whether it is linked.

A *linked* worktree (``git worktree add``) has a private git dir under
``<main>/.git/worktrees/<name>`` whose common dir is the main checkout's ``.git``.
In the main checkout, and in any plain clone, the two are the same directory.
A directory outside any git repository is not a worktree.

Used so per-worktree activation never shares the machine-global active file.
"""

from __future__ import annotations

import subprocess  # nosec B404 - fixed git CLI, never a shell
from dataclasses import dataclass
from pathlib import Path

GIT_TIMEOUT_SECONDS = 5


@dataclass(frozen=True)
class GitContext:
    """Where a path sits in git: the checkout root and whether it is a linked worktree."""

    root: Path
    is_linked_worktree: bool


def _existing_dir(path: Path) -> Path | None:
    """Nearest existing directory at or above ``path`` (files resolve to their parent)."""
    current = path.resolve()
    while not current.is_dir():
        if current.parent == current:
            return None
        current = current.parent
    return current


def _resolve_against(base: Path, raw: str) -> Path:
    candidate = Path(raw)
    return (candidate if candidate.is_absolute() else base / candidate).resolve()


def git_context(path: Path) -> GitContext | None:
    """Git checkout containing ``path``, or ``None`` outside git (or without git)."""
    start = _existing_dir(path)
    if start is None:
        return None
    args = ["git", "rev-parse", "--show-toplevel", "--git-dir", "--git-common-dir"]
    try:
        proc = subprocess.run(  # nosec B603 B607 - fixed args, no shell
            args,
            cwd=start,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    lines = proc.stdout.splitlines()
    if proc.returncode != 0 or len(lines) < 3:
        return None
    root = _resolve_against(start, lines[0])
    git_dir = _resolve_against(start, lines[1])
    common_dir = _resolve_against(start, lines[2])
    return GitContext(root=root, is_linked_worktree=git_dir != common_dir)

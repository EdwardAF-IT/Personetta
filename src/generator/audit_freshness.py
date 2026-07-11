"""Committed audit stamp for optional staleness notices (cross-machine via git)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

# Relative to repo root; committed so every clone shares the same "last audit" date.
AUDIT_STAMP_FILE = Path(".personetta") / "last-audit"
DEFAULT_MAX_STALE_DAYS = 90


def read_audit_stamp(repo_root: Path) -> str | None:
    path = repo_root / AUDIT_STAMP_FILE
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8").strip()


def audit_freshness_message(
    repo_root: Path,
    *,
    today: date | None = None,
    max_stale_days: int = DEFAULT_MAX_STALE_DAYS,
) -> str | None:
    """
    Return a human-readable warning if the stamp is missing, invalid, or older than max_stale_days.
    Return None if the stamp is fresh enough.
    """
    today = today or date.today()
    raw = read_audit_stamp(repo_root)
    if raw is None:
        return (
            "No .personetta/last-audit in repo. After a tool-corpus audit, run: "
            "python scripts/record_audit_date.py (and commit the updated file)."
        )
    try:
        last = date.fromisoformat(raw)
    except ValueError:
        return (
            f".personetta/last-audit must be a single YYYY-MM-DD line; got {raw!r}. "
            "Fix or run: python scripts/record_audit_date.py"
        )
    age = (today - last).days
    if age > max_stale_days:
        return (
            f"Tool-corpus audit stamp is {age} days old (last: {last.isoformat()}). "
            "Run your audit, then: python scripts/record_audit_date.py (and commit)."
        )
    return None


def write_audit_stamp(repo_root: Path) -> None:
    """Write today's date to the committed stamp (after a successful tooling apply)."""
    path = repo_root / AUDIT_STAMP_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(date.today().isoformat() + "\n", encoding="utf-8")

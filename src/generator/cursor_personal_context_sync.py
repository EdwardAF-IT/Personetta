"""
Sync Personetta Cursor rules into Cursor's global User Rules storage.

Cursor stores Settings → Rules for AI in the ItemTable row keyed
``aicontext.personalContext`` inside:

- Windows: ``%APPDATA%\\Cursor\\User\\globalStorage\\state.vscdb``
- macOS: ``~/Library/Application Support/Cursor/User/globalStorage/state.vscdb``
- Linux: ``~/.config/Cursor/User/globalStorage/state.vscdb`` (typical)

The Agent does not reliably load ``%USERPROFILE%\\.cursor\\rules\\*.md`` on every
Cursor build; updating this row keeps one global instruction block current
whenever ``install`` / ``set-active`` run against the user home target.

Set ``PERSONETTA_SKIP_CURSOR_USER_SYNC=1`` to disable writes to the database.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

from generator.cursor_layout import (
    ACTIVE_FILENAME,
    BASELINE_FILENAME,
    ROUTER_FILENAME,
    _rules_dir,
)

_SYNC_HEADER = (
    "<!-- personetta:synced - do not edit here; run `personetta install '*'` / "
    "`set-active` from your Personetta repo -->\n\n"
)

# Visible in Cursor Settings > Rules (personalContext). The app may also show a
# "personetta" tab under Rules, Skills, Subagents; Personetta does not write there.
_CURSOR_SETTINGS_TAB_WARNING = (
    "> **Cursor Settings:** If you see a **personetta** tab under **Rules, Skills, "
    "Subagents**, Personetta **does not** sync into it. Do **not** add personas or "
    "skills there and expect them to track `install` / `set-active`—use the Role "
    "Forge repo and CLI only. This block (User / global rules) plus "
    "`~/.cursor/rules/` and `~/.cursor/skills/` from the CLI are authoritative.\n\n"
)


def cursor_global_state_vscdb_path() -> Path | None:
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            return None
        return Path(appdata) / "Cursor" / "User" / "globalStorage" / "state.vscdb"
    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library/Application Support/Cursor/User/globalStorage/state.vscdb"
        )
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    p = base / "Cursor/User/globalStorage/state.vscdb"
    return p


def build_merged_personal_context(target_root: Path) -> str | None:
    """Return merged markdown from on-disk Personetta Cursor rules, or None if missing."""
    rules = _rules_dir(target_root)
    parts: list[str] = [
        _SYNC_HEADER,
        _CURSOR_SETTINGS_TAB_WARNING,
        "# Personetta (global)\n",
    ]
    any_rule_file = False
    for label, name in (
        ("Baseline", BASELINE_FILENAME),
        ("Active persona", ACTIVE_FILENAME),
        ("Recipe router", ROUTER_FILENAME),
    ):
        path = rules / name
        if not path.is_file():
            continue
        any_rule_file = True
        body = path.read_text(encoding="utf-8").strip()
        parts.append(f"\n---\n\n## {label} (`{name}`)\n\n{body}\n")
    if not any_rule_file:
        return None
    return "".join(parts).strip() + "\n"


def write_personal_context_to_cursor_db(
    merged: str,
    *,
    db_path: Path | None = None,
) -> tuple[bool, str]:
    """
    Upsert ``aicontext.personalContext`` in Cursor's global state DB.
    Returns (ok, message for stderr or logging).
    """
    resolved = db_path or cursor_global_state_vscdb_path()
    if resolved is None or not resolved.is_file():
        return (
            False,
            f"Cursor global state DB not found at {resolved} (install Cursor / open once).",
        )

    try:
        conn = sqlite3.connect(str(resolved), timeout=15)
    except sqlite3.Error as exc:
        return (
            False,
            f"Could not open Cursor state DB ({exc}). Quit Cursor and retry, or set PERSONETTA_SKIP_CURSOR_USER_SYNC=1.",
        )

    try:
        conn.execute(
            "INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
            ("aicontext.personalContext", merged),
        )
        conn.commit()
    except sqlite3.Error as exc:
        return (
            False,
            f"Could not write User Rules to Cursor DB ({exc}). Quit Cursor and retry.",
        )
    finally:
        conn.close()

    return True, ""


def maybe_sync_personal_context(target_root: Path) -> tuple[bool, str]:
    """
    If ``target_root`` is the user home directory, merge Personetta rules into
    Cursor's ``aicontext.personalContext``. Skipped when env
    ``PERSONETTA_SKIP_CURSOR_USER_SYNC`` is set.

    Returns (attempted_and_ok, diagnostic_message). When skipped, returns (True, "").
    """
    if os.environ.get("PERSONETTA_SKIP_CURSOR_USER_SYNC", "").strip() in (
        "1",
        "true",
        "yes",
    ):
        return True, ""

    if target_root.resolve() != Path.home().resolve():
        return True, ""

    merged = build_merged_personal_context(target_root)
    if merged is None:
        return (
            False,
            "Personetta Cursor rules not found under ~/.cursor/rules; sync skipped.",
        )

    ok, err = write_personal_context_to_cursor_db(merged)
    if ok:
        return True, (
            "Synced Personetta into Cursor Settings > Rules (global). "
            "Reload the window if Cursor was already open."
        )
    return False, err

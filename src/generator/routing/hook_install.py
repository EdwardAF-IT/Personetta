"""Install/uninstall the Claude Code auto-route hook in settings.json.

We add a ``UserPromptSubmit`` hook that runs a generated launcher script. The
launcher resolves a working ``personetta`` even when it is not on PATH (the
common breakage): it tries the console script, then ``python -m generator``,
then a ``PERSONETTA_BASE/src`` fallback — and always exits 0 so a missing
install never blocks the user's prompt.

The settings edit is idempotent (keyed by a stable marker) and preserves any
existing hooks.
"""

from __future__ import annotations

import json
from pathlib import Path

# Stable marker so we can find/replace/remove our own hook without touching others.
HOOK_MARKER = "personetta route-hook"
WRAPPER_NAME = "route-hook.sh"
HOOK_EVENT = "UserPromptSubmit"


def wrapper_path(install_root: Path) -> Path:
    return install_root / ".personetta" / WRAPPER_NAME


def settings_path(install_root: Path) -> Path:
    return install_root / ".claude" / "settings.json"


def render_wrapper(
    install_root: Path, *, fmt: str = "claude", base_dir: Path | None = None
) -> str:
    """Generate the launcher script body (POSIX sh).

    ``base_dir`` (the personetta repo/package root) is baked in as the
    ``PERSONETTA_BASE`` fallback so the source-tree resolution works even in the
    non-interactive hook context where PATH and profile env are absent.
    """
    root = str(install_root)
    base = str(base_dir) if base_dir is not None else ""
    return """#!/usr/bin/env bash
# personetta auto-route hook launcher (generated; safe to re-generate).
# Resolves personetta even when it is not on PATH, and NEVER blocks the prompt.
set +e
PERSONETTA_HOME="{root}"
export PERSONETTA_BASE="${{PERSONETTA_BASE:-{base}}}"
export PERSONETTA_ROUTE_MODE="${{PERSONETTA_ROUTE_MODE:-prompt}}"

# {marker}
if command -v personetta >/dev/null 2>&1; then
    personetta route-hook --format {fmt} --target project "$PERSONETTA_HOME"
elif python3 -c "import generator" >/dev/null 2>&1; then
    python3 -m generator route-hook --format {fmt} --target project "$PERSONETTA_HOME"
elif [ -n "$PERSONETTA_BASE" ] && \\
     PYTHONPATH="$PERSONETTA_BASE/src" python3 -c "import generator" >/dev/null 2>&1; then
    PYTHONPATH="$PERSONETTA_BASE/src" python3 -m generator route-hook \\
        --format {fmt} --target project "$PERSONETTA_HOME"
else
    # personetta unavailable — fail open so the prompt is never blocked.
    exit 0
fi
exit 0
""".format(root=root, base=base, fmt=fmt, marker=HOOK_MARKER)


def _hook_command(install_root: Path) -> str:
    return 'bash "{0}"'.format(wrapper_path(install_root))


def _load_settings(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _write_settings(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _entry_is_ours(entry: dict) -> bool:
    for hook in entry.get("hooks", []):
        if HOOK_MARKER in str(hook.get("command", "")) or WRAPPER_NAME in str(
            hook.get("command", "")
        ):
            return True
    return False


def is_installed(install_root: Path) -> bool:
    data = _load_settings(settings_path(install_root))
    entries = data.get("hooks", {}).get(HOOK_EVENT, [])
    return any(_entry_is_ours(e) for e in entries)


def install_hook(
    install_root: Path,
    *,
    fmt: str = "claude",
    base_dir: Path | None = None,
    timeout: int = 10,
) -> Path:
    """Write the wrapper and register the UserPromptSubmit hook. Idempotent."""
    wrapper = wrapper_path(install_root)
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    wrapper.write_text(
        render_wrapper(install_root, fmt=fmt, base_dir=base_dir), encoding="utf-8"
    )
    wrapper.chmod(0o755)

    path = settings_path(install_root)
    data = _load_settings(path)
    hooks = data.setdefault("hooks", {})
    event = hooks.setdefault(HOOK_EVENT, [])

    # Drop any prior personetta entry, then add a fresh one (idempotent upsert).
    event[:] = [e for e in event if not _entry_is_ours(e)]
    event.append(
        {
            "matcher": "",
            "hooks": [
                {
                    "type": "command",
                    "command": _hook_command(install_root),
                    "timeout": timeout,
                }
            ],
        }
    )
    _write_settings(path, data)
    return path


def uninstall_hook(install_root: Path) -> bool:
    """Remove our hook entry (and wrapper). Returns True if anything was removed."""
    removed = False
    path = settings_path(install_root)
    data = _load_settings(path)
    event = data.get("hooks", {}).get(HOOK_EVENT, [])
    if event:
        kept = [e for e in event if not _entry_is_ours(e)]
        if len(kept) != len(event):
            removed = True
            data["hooks"][HOOK_EVENT] = kept
            if not kept:
                del data["hooks"][HOOK_EVENT]
            if not data["hooks"]:
                del data["hooks"]
            _write_settings(path, data)

    wrapper = wrapper_path(install_root)
    if wrapper.is_file():
        wrapper.unlink()
        removed = True
    return removed

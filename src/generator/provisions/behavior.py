"""``behavior`` provision strategy: install an rf-managed, persona-independent behavior.

For Item 2 (coordinator delegation) this writes three subagent/instruction files
into the tool's agents directory and registers a SessionStart **depth-guard** hook
in the tool's settings file. It is installed at the hook/agent layer, never inside a
recipe's persona text, so the active persona is unaffected ("economy, not persona").
Idempotent (re-runs report ``already-satisfied``) and ``--dry-run`` aware. Supported
only on tools whose capability declares hooks **and** a subagent directory; others
report ``unsupported`` with a reason.
"""

from __future__ import annotations

import json
from pathlib import Path

from generator.constants import PERSONETTA_DIR
from generator.provisions.capabilities import ToolCapability
from generator.provisions.delegation import (
    COORDINATOR_NAME,
    EXECUTOR_NAME,
    IMPLEMENTER_NAME,
    DelegationConfig,
    parse_config,
    render_coordinator,
    render_depth_guard_hook,
    render_executor,
    render_implementer,
)
from generator.provisions.models import (
    KIND_BEHAVIOR,
    STATUS_ALREADY_SATISFIED,
    STATUS_APPLIED,
    STATUS_DRY_RUN,
    Provision,
    ProvisionResult,
)
from generator.provisions.strategies import register_strategy, unsupported_result

GUARD_MARKER = "personetta delegation-guard"
GUARD_SCRIPT = "pn-delegation-guard.sh"
GUARD_RELPATH = Path(PERSONETTA_DIR) / GUARD_SCRIPT
HOOK_EVENT = "SessionStart"


def _unsupported_reason(capability: ToolCapability, fmt: str) -> str:
    """Return why ``fmt`` cannot host this behavior, or '' when it can."""
    if not capability.supports_hooks:
        return "{0} has no hook layer for rf-managed behaviors".format(fmt)
    if capability.agents_relpath is None:
        return "{0} exposes no subagent directory for delegation".format(fmt)
    if capability.settings_relpath is None:
        return "{0} has no settings file to register the guard hook".format(fmt)
    return ""


def _artifacts(
    config: DelegationConfig, agents_dir: Path, root: Path
) -> list[tuple[Path, str]]:
    """Return the (path, content) file artifacts this behavior installs."""
    return [
        (agents_dir / (EXECUTOR_NAME + ".md"), render_executor(config)),
        (agents_dir / (IMPLEMENTER_NAME + ".md"), render_implementer(config)),
        (agents_dir / (COORDINATOR_NAME + ".md"), render_coordinator(config)),
        (root / GUARD_RELPATH, render_depth_guard_hook(config, GUARD_MARKER)),
    ]


def _needs_write(path: Path, content: str) -> bool:
    """Return True when ``path`` is absent or differs from ``content``."""
    if not path.is_file():
        return True
    return path.read_text(encoding="utf-8") != content


def _write_files(pending: list[tuple[Path, str]]) -> None:
    """Write each pending (path, content) artifact, creating parents."""
    for path, content in pending:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _load_settings(path: Path) -> dict:
    """Load a JSON settings object; return ``{}`` when missing/invalid."""
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _entry_is_ours(entry: dict) -> bool:
    """Return True when a settings hook entry is our guard hook."""
    return any(GUARD_SCRIPT in str(h.get("command", "")) for h in entry.get("hooks", []))


def _hook_registered(path: Path) -> bool:
    """Return True when the guard hook is already present in settings."""
    entries = _load_settings(path).get("hooks", {}).get(HOOK_EVENT, [])
    return any(_entry_is_ours(e) for e in entries)


def _register_hook(path: Path, command: str) -> None:
    """Idempotently register the guard hook under SessionStart, preserving others."""
    data = _load_settings(path)
    event = data.setdefault("hooks", {}).setdefault(HOOK_EVENT, [])
    event[:] = [e for e in event if not _entry_is_ours(e)]
    event.append(
        {
            "matcher": "",
            "hooks": [{"type": "command", "command": command, "timeout": 10}],
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _summary(pending: list[tuple[Path, str]], hook_pending: bool) -> str:
    """Summarize what changed (or would change) for the result detail."""
    parts = [path.name for path, _ in pending]
    if hook_pending:
        parts.append(HOOK_EVENT + " hook")
    return ", ".join(parts) if parts else "no changes"


class BehaviorStrategy:
    """Installs an rf-managed behavior as subagent defs plus a guard hook."""

    def apply(
        self,
        provision: Provision,
        target_root: Path,
        fmt: str,
        capability: ToolCapability,
        *,
        dry_run: bool,
    ) -> ProvisionResult:
        """Write the behavior's artifacts and register its guard hook."""
        reason = _unsupported_reason(capability, fmt)
        if reason:
            return unsupported_result(provision, fmt, reason)
        config = parse_config(provision.options)
        assert capability.agents_relpath is not None  # guaranteed by _unsupported_reason
        assert capability.settings_relpath is not None
        agents_dir = target_root / capability.agents_relpath
        settings = target_root / capability.settings_relpath
        files = _artifacts(config, agents_dir, target_root)
        pending = [(p, c) for (p, c) in files if _needs_write(p, c)]
        hook_pending = not _hook_registered(settings)
        return self._finish(
            provision, fmt, target_root, settings, pending, hook_pending, dry_run
        )

    def _finish(
        self,
        provision: Provision,
        fmt: str,
        root: Path,
        settings: Path,
        pending: list[tuple[Path, str]],
        hook_pending: bool,
        dry_run: bool,
    ) -> ProvisionResult:
        """Resolve the application to a single result, honoring dry-run/idempotency."""
        if not pending and not hook_pending:
            return ProvisionResult(
                provision.name, fmt, STATUS_ALREADY_SATISFIED, "no changes"
            )
        detail = _summary(pending, hook_pending)
        if dry_run:
            return ProvisionResult(provision.name, fmt, STATUS_DRY_RUN, detail)
        _write_files(pending)
        if hook_pending:
            _register_hook(settings, 'bash "{0}"'.format(root / GUARD_RELPATH))
        return ProvisionResult(provision.name, fmt, STATUS_APPLIED, detail)


register_strategy(KIND_BEHAVIOR, BehaviorStrategy())

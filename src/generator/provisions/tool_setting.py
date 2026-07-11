"""``tool-setting`` provision strategy: deep-merge keys into a tool's settings JSON.

Reads the target tool's settings file, deep-merges the provision's ``settings``
block (preserving every unrelated key), and writes it back. Re-runnable: when the
file already contains the desired values, nothing is written and the result is
``already-satisfied``. Supports any tool that declares a settings file in the
capability registry; Item 1's status line targets Claude, which does. Tools with
no mergeable settings file (e.g. Copilot) report ``unsupported`` with a reason.
"""

from __future__ import annotations

import json
from pathlib import Path

from generator.provisions.capabilities import ToolCapability
from generator.provisions.dict_merge import deep_merge
from generator.provisions.models import (
    KIND_TOOL_SETTING,
    STATUS_ALREADY_SATISFIED,
    STATUS_APPLIED,
    STATUS_DRY_RUN,
    Provision,
    ProvisionResult,
)
from generator.provisions.strategies import register_strategy, unsupported_result


def _load_json(path: Path) -> dict:
    """Load a JSON object from ``path``; return ``{}`` when missing/invalid."""
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


class ToolSettingStrategy:
    """Deep-merges ``provision.settings`` into the tool's settings JSON file."""

    def apply(
        self,
        provision: Provision,
        target_root: Path,
        fmt: str,
        capability: ToolCapability,
        *,
        dry_run: bool,
    ) -> ProvisionResult:
        """Merge the provision's settings block into the tool's settings file."""
        relpath = capability.settings_relpath
        if relpath is None:
            reason = "{0} has no mergeable settings file".format(fmt)
            return unsupported_result(provision, fmt, reason)
        if not provision.settings:
            return unsupported_result(provision, fmt, "no settings block to apply")
        return self._merge(provision, target_root / relpath, fmt, dry_run)

    def _merge(
        self, provision: Provision, path: Path, fmt: str, dry_run: bool
    ) -> ProvisionResult:
        """Read-merge-write the settings file; idempotent and dry-run aware."""
        current = _load_json(path)
        merged = deep_merge(current, dict(provision.settings))
        if merged == current:
            return ProvisionResult(
                provision.name, fmt, STATUS_ALREADY_SATISFIED, str(path)
            )
        if dry_run:
            return ProvisionResult(provision.name, fmt, STATUS_DRY_RUN, str(path))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
        return ProvisionResult(provision.name, fmt, STATUS_APPLIED, str(path))


register_strategy(KIND_TOOL_SETTING, ToolSettingStrategy())

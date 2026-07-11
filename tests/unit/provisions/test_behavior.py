"""Tests for the behavior provision strategy (Item 2 install/IO)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generator.provisions.behavior import BehaviorStrategy
from generator.provisions.capabilities import get_capability
from generator.provisions.models import (
    STATUS_ALREADY_SATISFIED,
    STATUS_APPLIED,
    STATUS_DRY_RUN,
    STATUS_UNSUPPORTED,
    Provision,
)

pytestmark = [pytest.mark.unit, pytest.mark.readonly]


def _prov(**options) -> Provision:
    return Provision(
        name="coordinator-delegation",
        kind="behavior",
        targets=("claude",),
        options=options
        or {
            "max_delegation_depth": 1,
            "executor_model": "haiku",
            "implementer_model": "sonnet",
        },
    )


def _apply(prov, root, fmt="claude", *, dry_run=False):
    return BehaviorStrategy().apply(prov, root, fmt, get_capability(fmt), dry_run=dry_run)


def _agents(root: Path) -> Path:
    return root / ".claude" / "agents"


def test_apply_writes_agents_and_registers_hook(tmp_path: Path) -> None:
    result = _apply(_prov(), tmp_path)
    assert result.status == STATUS_APPLIED
    agents = _agents(tmp_path)
    for name in ("pn-executor.md", "pn-implementer.md", "pn-coordinator.md"):
        assert (agents / name).is_file()
    assert (tmp_path / ".personetta" / "pn-delegation-guard.sh").is_file()
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
    entries = settings["hooks"]["SessionStart"]
    assert any(
        "pn-delegation-guard.sh" in h["command"] for e in entries for h in e["hooks"]
    )


def test_apply_is_idempotent(tmp_path: Path) -> None:
    _apply(_prov(), tmp_path)
    result = _apply(_prov(), tmp_path)
    assert result.status == STATUS_ALREADY_SATISFIED


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    result = _apply(_prov(), tmp_path, dry_run=True)
    assert result.status == STATUS_DRY_RUN
    assert not _agents(tmp_path).exists()
    assert not (tmp_path / ".claude" / "settings.json").exists()
    assert "pn-executor.md" in result.detail
    assert "SessionStart hook" in result.detail


def test_agent_defs_reflect_configured_models(tmp_path: Path) -> None:
    _apply(_prov(executor_model="mini", implementer_model="big"), tmp_path)
    executor = (_agents(tmp_path) / "pn-executor.md").read_text()
    implementer = (_agents(tmp_path) / "pn-implementer.md").read_text()
    assert "model: mini" in executor
    assert "model: big" in implementer


def test_config_change_triggers_rewrite(tmp_path: Path) -> None:
    _apply(_prov(executor_model="haiku"), tmp_path)
    result = _apply(_prov(executor_model="nano"), tmp_path)
    assert result.status == STATUS_APPLIED
    assert "model: nano" in (_agents(tmp_path) / "pn-executor.md").read_text()


def test_unsupported_when_no_hooks(tmp_path: Path) -> None:
    result = _apply(_prov(), tmp_path, fmt="copilot")
    assert result.status == STATUS_UNSUPPORTED
    assert "hook layer" in result.detail


def test_unsupported_when_no_agents_dir(tmp_path: Path) -> None:
    # Cursor declares hooks but exposes no subagent directory.
    result = _apply(_prov(), tmp_path, fmt="cursor")
    assert result.status == STATUS_UNSUPPORTED
    assert "subagent directory" in result.detail


def test_hook_registration_preserves_other_hooks(tmp_path: Path) -> None:
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {"hooks": {"SessionStart": [{"matcher": "", "hooks": [{"command": "x"}]}]}}
        )
    )
    _apply(_prov(), tmp_path)
    entries = json.loads(settings_path.read_text())["hooks"]["SessionStart"]
    commands = [h.get("command", "") for e in entries for h in e["hooks"]]
    assert "x" in commands
    assert any("pn-delegation-guard.sh" in c for c in commands)

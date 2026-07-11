"""Tests for the tool-setting (status line) provision strategy."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generator.provisions.capabilities import ToolCapability, get_capability
from generator.provisions.models import (
    STATUS_ALREADY_SATISFIED,
    STATUS_APPLIED,
    STATUS_DRY_RUN,
    STATUS_UNSUPPORTED,
    Provision,
)
from generator.provisions.tool_setting import ToolSettingStrategy

pytestmark = [pytest.mark.unit, pytest.mark.modifying]


def _status_line_provision() -> Provision:
    return Provision(
        name="status-line",
        kind="tool-setting",
        enabled=True,
        targets=("claude",),
        settings={"statusLine": {"type": "command", "command": "ccusage"}},
    )


def _settings_path(target: Path) -> Path:
    relpath = get_capability("claude").settings_relpath
    assert relpath is not None
    return target / relpath


def test_apply_writes_setting_and_creates_file(tmp_path: Path) -> None:
    strategy = ToolSettingStrategy()
    result = strategy.apply(
        _status_line_provision(),
        tmp_path,
        "claude",
        get_capability("claude"),
        dry_run=False,
    )
    assert result.status == STATUS_APPLIED
    data = json.loads(_settings_path(tmp_path).read_text(encoding="utf-8"))
    assert data["statusLine"]["command"] == "ccusage"


def test_apply_preserves_unrelated_keys(tmp_path: Path) -> None:
    path = _settings_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"theme": "dark", "model": "opus"}), encoding="utf-8")

    ToolSettingStrategy().apply(
        _status_line_provision(),
        tmp_path,
        "claude",
        get_capability("claude"),
        dry_run=False,
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["theme"] == "dark"
    assert data["model"] == "opus"
    assert data["statusLine"]["command"] == "ccusage"


def test_apply_is_idempotent(tmp_path: Path) -> None:
    strategy = ToolSettingStrategy()
    cap = get_capability("claude")
    first = strategy.apply(
        _status_line_provision(), tmp_path, "claude", cap, dry_run=False
    )
    second = strategy.apply(
        _status_line_provision(), tmp_path, "claude", cap, dry_run=False
    )
    assert first.status == STATUS_APPLIED
    assert second.status == STATUS_ALREADY_SATISFIED


def test_dry_run_does_not_write(tmp_path: Path) -> None:
    result = ToolSettingStrategy().apply(
        _status_line_provision(),
        tmp_path,
        "claude",
        get_capability("claude"),
        dry_run=True,
    )
    assert result.status == STATUS_DRY_RUN
    assert not _settings_path(tmp_path).exists()


def test_unsupported_when_tool_has_no_settings_file(tmp_path: Path) -> None:
    result = ToolSettingStrategy().apply(
        _status_line_provision(),
        tmp_path,
        "copilot",
        get_capability("copilot"),
        dry_run=False,
    )
    assert result.status == STATUS_UNSUPPORTED
    assert "settings file" in result.detail


def test_unsupported_when_no_settings_block(tmp_path: Path) -> None:
    prov = Provision(name="empty", kind="tool-setting", targets=("claude",))
    result = ToolSettingStrategy().apply(
        prov, tmp_path, "claude", get_capability("claude"), dry_run=False
    )
    assert result.status == STATUS_UNSUPPORTED
    assert "settings block" in result.detail


def test_invalid_existing_json_is_overwritten_safely(tmp_path: Path) -> None:
    path = _settings_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ not valid json", encoding="utf-8")

    result = ToolSettingStrategy().apply(
        _status_line_provision(),
        tmp_path,
        "claude",
        get_capability("claude"),
        dry_run=False,
    )
    assert result.status == STATUS_APPLIED
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["statusLine"]["command"] == "ccusage"


def test_custom_capability_without_settings_is_unsupported(tmp_path: Path) -> None:
    cap = ToolCapability(format_name="weird")
    result = ToolSettingStrategy().apply(
        _status_line_provision(), tmp_path, "weird", cap, dry_run=False
    )
    assert result.status == STATUS_UNSUPPORTED

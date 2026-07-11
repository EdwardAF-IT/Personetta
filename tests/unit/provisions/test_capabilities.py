"""Tests for the per-tool capability registry."""

from __future__ import annotations

import pytest

from generator.provisions.capabilities import ToolCapability, get_capability

pytestmark = [pytest.mark.unit, pytest.mark.readonly]


def test_claude_supports_settings_plugins_and_hooks() -> None:
    cap = get_capability("claude")
    assert cap.settings_relpath is not None
    assert cap.settings_relpath.name == "settings.json"
    assert cap.supports_plugins is True
    assert cap.supports_hooks is True


def test_cursor_has_hooks_but_no_settings_file() -> None:
    cap = get_capability("cursor")
    assert cap.settings_relpath is None
    assert cap.supports_hooks is True
    assert cap.supports_plugins is False


def test_copilot_and_cline_are_conservative() -> None:
    for fmt in ("copilot", "cline"):
        cap = get_capability(fmt)
        assert cap.settings_relpath is None
        assert cap.supports_plugins is False


def test_unknown_tool_gets_conservative_default() -> None:
    cap = get_capability("brand-new-tool")
    assert isinstance(cap, ToolCapability)
    assert cap.format_name == "brand-new-tool"
    assert cap.settings_relpath is None
    assert cap.supports_plugins is False
    assert cap.supports_hooks is False

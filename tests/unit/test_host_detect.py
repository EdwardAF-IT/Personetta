"""Tests for host-agent detection.

Bug 1: a Personetta skill invoked inside an agent chat should target that agent
by default. ``detect_host_format`` reads the environment markers each harness
sets on the subprocesses it spawns, so ``set-active`` (and friends) can default
``--format`` to the host agent instead of requiring an explicit flag.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.readonly]

# Every marker the detector inspects; cleared before each scenario so a stray
# variable from the real test host cannot leak into an assertion.
_MARKERS = (
    "CURSOR_AGENT",
    "CLAUDECODE",
    "CLAUDE_CODE_CHILD_SESSION",
    "COPILOT_AGENT",
    "AI_AGENT",
)


def _clear_markers(monkeypatch) -> None:
    """Remove all host markers so each test starts from a known-empty state."""
    for name in _MARKERS:
        monkeypatch.delenv(name, raising=False)


class TestDetectHostFormat:
    """Detection of the hosting agent from environment markers."""

    def test_detects_cursor(self, monkeypatch):
        from generator.host_detect import detect_host_format

        _clear_markers(monkeypatch)
        monkeypatch.setenv("CURSOR_AGENT", "1")
        assert detect_host_format() == "cursor"

    def test_detects_claude(self, monkeypatch):
        from generator.host_detect import detect_host_format

        _clear_markers(monkeypatch)
        monkeypatch.setenv("CLAUDECODE", "1")
        assert detect_host_format() == "claude"

    def test_detects_copilot_via_copilot_agent(self, monkeypatch):
        from generator.host_detect import detect_host_format

        _clear_markers(monkeypatch)
        monkeypatch.setenv("COPILOT_AGENT", "1")
        assert detect_host_format() == "copilot"

    def test_detects_copilot_via_cross_vendor_ai_agent(self, monkeypatch):
        from generator.host_detect import detect_host_format

        _clear_markers(monkeypatch)
        monkeypatch.setenv("AI_AGENT", "github_copilot_vscode_agent")
        assert detect_host_format() == "copilot"

    def test_returns_none_without_any_marker(self, monkeypatch):
        from generator.host_detect import detect_host_format

        _clear_markers(monkeypatch)
        assert detect_host_format() is None

    def test_claude_takes_precedence_over_cursor(self, monkeypatch):
        """Claude Code's marker is set only when Claude spawns the process, so a
        nested Claude session inside a Cursor terminal must resolve to claude."""
        from generator.host_detect import detect_host_format

        _clear_markers(monkeypatch)
        monkeypatch.setenv("CLAUDECODE", "1")
        monkeypatch.setenv("CURSOR_AGENT", "1")
        assert detect_host_format() == "claude"

    def test_accepts_explicit_environment_mapping(self, monkeypatch):
        from generator.host_detect import detect_host_format

        _clear_markers(monkeypatch)
        assert detect_host_format({"CURSOR_AGENT": "1"}) == "cursor"

    def test_ignores_falsey_marker_values(self, monkeypatch):
        from generator.host_detect import detect_host_format

        _clear_markers(monkeypatch)
        assert detect_host_format({"CURSOR_AGENT": "0"}) is None
        assert detect_host_format({"CLAUDECODE": "false"}) is None

    def test_detected_value_is_a_known_format(self, monkeypatch):
        from generator.host_detect import detect_host_format
        from generator.output_formats import FORMAT_NAMES

        _clear_markers(monkeypatch)
        monkeypatch.setenv("CURSOR_AGENT", "1")
        assert detect_host_format() in FORMAT_NAMES

"""Tests for command target-format resolution.

Covers the full ladder: explicit flag -> host agent -> FAB_DEFAULT_FORMAT ->
sole installed format -> undetermined. The host path matters inside an agent
chat; the env/sole-install paths matter at a plain command line.
"""

from __future__ import annotations

import pytest

from generator.format_resolver import (
    DEFAULT_FORMAT_ENV,
    FormatResolution,
    installed_formats,
    resolution_note,
    resolve_format,
)

pytestmark = [pytest.mark.unit, pytest.mark.readonly]


def _bare_env() -> dict:
    return {}


def _install(target, *formats: str) -> None:
    """Create non-empty recipe caches for the given formats under target."""
    for fmt in formats:
        cache = target / ".personetta" / "{0}-recipes".format(fmt)
        cache.mkdir(parents=True, exist_ok=True)
        (cache / "placeholder.md").write_text("x", encoding="utf-8")


class TestResolveFormat:
    def test_explicit_wins(self, tmp_path):
        _install(tmp_path, "cursor", "claude")
        res = resolve_format("copilot", tmp_path, env={"CURSOR_AGENT": "1"})
        assert res == FormatResolution("copilot", "explicit")

    def test_host_used_when_no_explicit(self, tmp_path):
        res = resolve_format(None, tmp_path, env={"CURSOR_AGENT": "1"})
        assert res == FormatResolution("cursor", "host")

    def test_env_default_when_no_host(self, tmp_path):
        res = resolve_format(None, tmp_path, env={DEFAULT_FORMAT_ENV: "claude"})
        assert res == FormatResolution("claude", "env-default")

    def test_invalid_env_default_is_ignored(self, tmp_path):
        _install(tmp_path, "copilot")
        res = resolve_format(None, tmp_path, env={DEFAULT_FORMAT_ENV: "bogus"})
        # Falls through to sole-install.
        assert res == FormatResolution("copilot", "sole-install")

    def test_sole_installed_format_used_at_cli(self, tmp_path):
        _install(tmp_path, "cursor")
        res = resolve_format(None, tmp_path, env=_bare_env())
        assert res == FormatResolution("cursor", "sole-install")

    def test_ambiguous_install_is_undetermined(self, tmp_path):
        _install(tmp_path, "cursor", "claude")
        res = resolve_format(None, tmp_path, env=_bare_env())
        assert res == FormatResolution(None, "none")

    def test_zero_install_is_undetermined(self, tmp_path):
        res = resolve_format(None, tmp_path, env=_bare_env())
        assert res == FormatResolution(None, "none")

    def test_host_takes_precedence_over_env_and_install(self, tmp_path):
        _install(tmp_path, "copilot")
        res = resolve_format(
            None,
            tmp_path,
            env={"CLAUDECODE": "1", DEFAULT_FORMAT_ENV: "cursor"},
        )
        assert res == FormatResolution("claude", "host")


class TestInstalledFormats:
    def test_detects_non_empty_caches_only(self, tmp_path):
        _install(tmp_path, "cursor", "copilot")
        # An empty cache dir should not count as installed.
        (tmp_path / ".personetta" / "claude-recipes").mkdir(parents=True)
        assert installed_formats(tmp_path) == ["cursor", "copilot"] or set(
            installed_formats(tmp_path)
        ) == {"cursor", "copilot"}


class TestResolutionNote:
    def test_note_for_each_inferred_source(self):
        assert "cursor" in resolution_note(FormatResolution("cursor", "host"))
        assert "FAB_DEFAULT_FORMAT" in resolution_note(
            FormatResolution("claude", "env-default")
        )
        assert "--format" in resolution_note(FormatResolution("copilot", "sole-install"))

    def test_no_note_for_explicit_or_none(self):
        assert resolution_note(FormatResolution("cursor", "explicit")) is None
        assert resolution_note(FormatResolution(None, "none")) is None

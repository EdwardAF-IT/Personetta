"""Tests for the auto-route hook installer (settings.json + wrapper)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from generator.routing.hook_install import (
    HOOK_EVENT,
    HOOK_MARKER,
    install_hook,
    is_installed,
    render_wrapper,
    settings_path,
    uninstall_hook,
    wrapper_path,
)


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class TestInstall:
    def test_creates_wrapper_and_settings(self, tmp_path):
        install_hook(tmp_path)
        wrapper = wrapper_path(tmp_path)
        settings = settings_path(tmp_path)
        assert wrapper.is_file()
        assert HOOK_MARKER in wrapper.read_text(encoding="utf-8")
        assert str(tmp_path) in wrapper.read_text(encoding="utf-8")
        data = _read(settings)
        entries = data["hooks"][HOOK_EVENT]
        assert len(entries) == 1
        assert "route-hook" in entries[0]["hooks"][0]["command"]

    def test_is_installed_reports_true(self, tmp_path):
        assert is_installed(tmp_path) is False
        install_hook(tmp_path)
        assert is_installed(tmp_path) is True

    @pytest.mark.skipif(os.name == "nt", reason="POSIX exec bit")
    def test_wrapper_is_executable(self, tmp_path):
        install_hook(tmp_path)
        assert os.access(wrapper_path(tmp_path), os.X_OK)

    def test_idempotent_no_duplicate_entries(self, tmp_path):
        install_hook(tmp_path)
        install_hook(tmp_path)
        entries = _read(settings_path(tmp_path))["hooks"][HOOK_EVENT]
        ours = [e for e in entries if "route-hook" in e["hooks"][0]["command"]]
        assert len(ours) == 1

    def test_preserves_existing_unrelated_hooks(self, tmp_path):
        settings = settings_path(tmp_path)
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(
            json.dumps(
                {
                    "hooks": {
                        HOOK_EVENT: [
                            {
                                "matcher": "",
                                "hooks": [{"type": "command", "command": "echo keep-me"}],
                            }
                        ]
                    },
                    "theme": "dark",
                }
            ),
            encoding="utf-8",
        )
        install_hook(tmp_path)
        data = _read(settings)
        commands = [h["command"] for e in data["hooks"][HOOK_EVENT] for h in e["hooks"]]
        assert "echo keep-me" in commands
        assert any("route-hook" in c for c in commands)
        assert data["theme"] == "dark"  # untouched


class TestUninstall:
    def test_removes_entry_and_wrapper(self, tmp_path):
        install_hook(tmp_path)
        assert uninstall_hook(tmp_path) is True
        assert not wrapper_path(tmp_path).is_file()
        assert is_installed(tmp_path) is False

    def test_uninstall_keeps_other_hooks(self, tmp_path):
        settings = settings_path(tmp_path)
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(
            json.dumps(
                {
                    "hooks": {
                        HOOK_EVENT: [
                            {
                                "matcher": "",
                                "hooks": [{"type": "command", "command": "echo keep-me"}],
                            }
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )
        install_hook(tmp_path)
        uninstall_hook(tmp_path)
        data = _read(settings)
        commands = [h["command"] for e in data["hooks"][HOOK_EVENT] for h in e["hooks"]]
        assert commands == ["echo keep-me"]

    def test_uninstall_when_absent_returns_false(self, tmp_path):
        assert uninstall_hook(tmp_path) is False


def test_wrapper_resolution_order(tmp_path):
    body = render_wrapper(tmp_path)
    # Robust resolution: PATH console script -> python -m generator -> src fallback -> fail open.
    assert "command -v personetta" in body
    assert "python3 -m generator route-hook" in body
    assert "PERSONETTA_BASE" in body
    assert "exit 0" in body  # never blocks the prompt


def test_wrapper_bakes_base_dir_for_source_fallback(tmp_path):
    body = render_wrapper(tmp_path, base_dir=tmp_path / "repo")
    # PERSONETTA_BASE default points at the package root so the source-tree
    # fallback resolves in the non-interactive hook context.
    assert 'export PERSONETTA_BASE="${PERSONETTA_BASE:-' in body
    assert str(tmp_path / "repo") in body

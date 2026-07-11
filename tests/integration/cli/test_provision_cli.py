"""Integration tests for the `provision` CLI surface (end-to-end via main)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.integration, pytest.mark.cli]


def _run(argv: list[str], real_project: Path, monkeypatch) -> int:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(sys, "argv", ["personetta", *argv])
    from generator.cli.main import main

    return main()


def _target(home: Path) -> list[str]:
    return ["--target", "project", str(home)]


def test_enable_apply_roundtrip(real_project, tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()

    assert (
        _run(
            ["provision", "enable", "status-line", *_target(home)],
            real_project,
            monkeypatch,
        )
        == 0
    )
    assert _run(["provision", "apply", *_target(home)], real_project, monkeypatch) == 0

    settings = home / ".claude" / "settings.json"
    data = json.loads(settings.read_text(encoding="utf-8"))
    assert "statusLine" in data


def test_dry_run_then_real_apply(real_project, tmp_path, monkeypatch, capsys) -> None:
    home = tmp_path / "home"
    home.mkdir()
    settings = home / ".claude" / "settings.json"

    rc = _run(
        ["provision", "apply", "status-line", "--dry-run", *_target(home)],
        real_project,
        monkeypatch,
    )
    assert rc == 0
    assert not settings.exists()
    assert "dry-run" in capsys.readouterr().out

    rc = _run(
        ["provision", "apply", "status-line", *_target(home)], real_project, monkeypatch
    )
    assert rc == 0
    assert settings.exists()


def test_apply_preserves_existing_settings(real_project, tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    settings = home / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps({"theme": "dark"}), encoding="utf-8")

    assert (
        _run(
            ["provision", "apply", "status-line", *_target(home)],
            real_project,
            monkeypatch,
        )
        == 0
    )
    data = json.loads(settings.read_text(encoding="utf-8"))
    assert data["theme"] == "dark"
    assert "statusLine" in data


def test_behavior_installs_without_touching_recipe_rules(
    real_project, tmp_path, monkeypatch
) -> None:
    """Enabling the coordinator behavior installs agents + a hook, not persona text."""
    home = tmp_path / "home"
    home.mkdir()

    assert (
        _run(
            ["provision", "enable", "coordinator-delegation", *_target(home)],
            real_project,
            monkeypatch,
        )
        == 0
    )
    assert _run(["provision", "apply", *_target(home)], real_project, monkeypatch) == 0

    agents = home / ".claude" / "agents"
    assert (agents / "pn-executor.md").is_file()
    assert (agents / "pn-implementer.md").is_file()
    assert (home / ".personetta" / "pn-delegation-guard.sh").is_file()

    settings = json.loads((home / ".claude" / "settings.json").read_text("utf-8"))
    assert "SessionStart" in settings["hooks"]
    # The behavior touches no recipe/persona caches.
    assert not (home / ".personetta" / "claude-recipes").exists()
    assert not (home / ".claude" / "CLAUDE.md").exists()


def test_install_applies_enabled_provision(real_project, tmp_path, monkeypatch) -> None:
    """install (claude) runs the deploy-dark provisions pass for enabled items."""
    monkeypatch.setenv("PERSONETTA_SKIP_CLAUDE_SKILLS", "1")
    home = tmp_path / "home"
    user_file = home / ".personetta" / "provisions.yaml"
    user_file.parent.mkdir(parents=True, exist_ok=True)
    user_file.write_text(
        yaml.safe_dump({"provisions": {"status-line": {"enabled": True}}}),
        encoding="utf-8",
    )

    rc = _run(
        ["install", "implement-python", "--format", "claude", *_target(home)],
        real_project,
        monkeypatch,
    )
    assert rc == 0
    settings = home / ".claude" / "settings.json"
    assert settings.exists()
    assert "statusLine" in json.loads(settings.read_text(encoding="utf-8"))

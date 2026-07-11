"""Tests for the provision CLI command."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest
import yaml

from generator.cli.commands.provision import (
    add_provision_parser,
    cmd_provision,
)

pytestmark = [pytest.mark.unit, pytest.mark.cli]


def _args(**kw) -> argparse.Namespace:
    defaults = {
        "action": "list",
        "name": None,
        "bundle": None,
        "dry_run": False,
        "target": None,
    }
    defaults.update(kw)
    return argparse.Namespace(**defaults)


@pytest.fixture
def patched(monkeypatch, tmp_path, real_project):
    """Point base_dir at the real repo and target at an isolated tmp home."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(
        "generator.cli.commands.provision.get_base_dir", lambda: real_project
    )
    monkeypatch.setattr(
        "generator.cli.commands.provision.resolve_install_target", lambda t: home
    )
    return home


def _enable_status_line(home: Path) -> None:
    path = home / ".personetta" / "provisions.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump({"provisions": {"status-line": {"enabled": True}}}),
        encoding="utf-8",
    )


def test_list_shows_provisions_and_bundles(patched, capsys) -> None:
    rc = cmd_provision(_args(action="list"))
    assert rc == 0
    out = capsys.readouterr().out
    assert "status-line" in out
    assert "economy" in out


def test_enable_then_disable_writes_user_file(patched, capsys) -> None:
    assert cmd_provision(_args(action="enable", name="status-line")) == 0
    user_file = patched / ".personetta" / "provisions.yaml"
    doc = yaml.safe_load(user_file.read_text(encoding="utf-8"))
    assert doc["provisions"]["status-line"]["enabled"] is True

    assert cmd_provision(_args(action="disable", name="status-line")) == 0
    doc = yaml.safe_load(user_file.read_text(encoding="utf-8"))
    assert doc["provisions"]["status-line"]["enabled"] is False


def test_enable_unknown_provision_errors(patched, capsys) -> None:
    rc = cmd_provision(_args(action="enable", name="does-not-exist"))
    assert rc == 1
    assert "Unknown provision" in capsys.readouterr().err


def test_enable_without_name_errors(patched, capsys) -> None:
    rc = cmd_provision(_args(action="enable"))
    assert rc == 1
    assert "Specify a provision" in capsys.readouterr().err


def test_apply_enabled_writes_status_line(patched, capsys) -> None:
    _enable_status_line(patched)
    rc = cmd_provision(_args(action="apply"))
    assert rc == 0
    settings = patched / ".claude" / "settings.json"
    data = json.loads(settings.read_text(encoding="utf-8"))
    assert data["statusLine"]["command"].startswith("bun x ccusage")


def test_apply_dry_run_does_not_write(patched, capsys) -> None:
    _enable_status_line(patched)
    rc = cmd_provision(_args(action="apply", dry_run=True))
    assert rc == 0
    assert not (patched / ".claude" / "settings.json").exists()
    assert "dry-run" in capsys.readouterr().out


def test_apply_named_provision(patched, capsys) -> None:
    rc = cmd_provision(_args(action="apply", name="status-line"))
    assert rc == 0
    assert (patched / ".claude" / "settings.json").exists()


def test_apply_unknown_named_provision_errors(patched, capsys) -> None:
    rc = cmd_provision(_args(action="apply", name="ghost"))
    assert rc == 1
    assert "Unknown provision" in capsys.readouterr().err


def test_apply_unknown_bundle_errors(patched, capsys) -> None:
    rc = cmd_provision(_args(action="apply", bundle="ghost"))
    assert rc == 1
    assert "Unknown bundle" in capsys.readouterr().err


def test_apply_with_nothing_enabled_is_noop(patched, capsys) -> None:
    rc = cmd_provision(_args(action="apply"))
    assert rc == 0
    assert "No provisions applied" in capsys.readouterr().out


def test_enable_bundle_writes_user_file(patched, capsys) -> None:
    rc = cmd_provision(_args(action="enable", bundle="economy"))
    assert rc == 0
    user_file = patched / ".personetta" / "provisions.yaml"
    doc = yaml.safe_load(user_file.read_text(encoding="utf-8"))
    assert doc["bundles"]["economy"]["enabled"] is True


class TestProvisionParser:
    """The parser wires the provision subcommand and its options."""

    def _parser(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        add_provision_parser(sub)
        return parser

    def test_list_action_parses(self) -> None:
        args = self._parser().parse_args(["provision", "list"])
        assert args.action == "list"

    def test_apply_with_bundle_and_dry_run(self) -> None:
        args = self._parser().parse_args(
            ["provision", "apply", "--bundle", "economy", "--dry-run"]
        )
        assert args.action == "apply"
        assert args.bundle == "economy"
        assert args.dry_run is True

    def test_invalid_action_rejected(self) -> None:
        with pytest.raises(SystemExit):
            self._parser().parse_args(["provision", "frobnicate"])

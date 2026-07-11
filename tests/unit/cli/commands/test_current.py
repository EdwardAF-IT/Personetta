"""Tests for the ``current`` command.

Bug 1: reporting the active recipe should also default to the host agent when
``--format`` is omitted, and it must work purely from the user's state file
(no repository required - Bug 2).
"""

from __future__ import annotations

import argparse
import json

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.cli, pytest.mark.readonly]


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = {"format": None, "target": None}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _write_state(root, fmt: str, recipe: str) -> None:
    state_dir = root / ".personetta"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "{0}-active.json".format(fmt)).write_text(
        json.dumps({"active_recipe": recipe}), encoding="utf-8"
    )


class TestCurrentCommand:
    """Reading the active recipe id from per-format state files."""

    def test_prints_active_recipe_for_explicit_format(
        self, tmp_path, capsys, monkeypatch
    ):
        from generator.cli.commands.current import cmd_current

        _write_state(tmp_path, "cursor", "implement-python-backend-perf")
        monkeypatch.setattr(
            "generator.cli.commands.current.resolve_install_target",
            lambda t: tmp_path,
        )

        exit_code = cmd_current(_make_args(format="cursor"))

        assert exit_code == 0
        out = capsys.readouterr().out
        assert "implement-python-backend-perf" in out

    def test_defaults_to_detected_host(self, tmp_path, capsys, monkeypatch):
        from generator.cli.commands.current import cmd_current
        from generator.format_resolver import FormatResolution

        _write_state(tmp_path, "claude", "design-game-mechanics")
        monkeypatch.setattr(
            "generator.cli.commands.current.resolve_install_target",
            lambda t: tmp_path,
        )
        monkeypatch.setattr(
            "generator.cli.commands.current.resolve_format",
            lambda explicit, target: FormatResolution("claude", "host"),
        )

        exit_code = cmd_current(_make_args(format=None))

        assert exit_code == 0
        out = capsys.readouterr().out
        assert "design-game-mechanics" in out

    def test_errors_when_format_unresolved(self, tmp_path, capsys, monkeypatch):
        from generator.cli.commands.current import cmd_current
        from generator.format_resolver import FormatResolution

        monkeypatch.setattr(
            "generator.cli.commands.current.resolve_install_target",
            lambda t: tmp_path,
        )
        monkeypatch.setattr(
            "generator.cli.commands.current.resolve_format",
            lambda explicit, target: FormatResolution(None, "none"),
        )

        exit_code = cmd_current(_make_args(format=None))

        assert exit_code == 1
        assert "--format" in capsys.readouterr().err

    def test_reports_missing_state_file(self, tmp_path, capsys, monkeypatch):
        from generator.cli.commands.current import cmd_current

        monkeypatch.setattr(
            "generator.cli.commands.current.resolve_install_target",
            lambda t: tmp_path,
        )

        exit_code = cmd_current(_make_args(format="cursor"))

        assert exit_code == 1
        out = capsys.readouterr().out + capsys.readouterr().err
        assert "no active" in out.lower() or "install" in out.lower()


class TestCurrentParser:
    """The parser must expose ``current`` with an optional --format."""

    def test_current_registered_with_optional_format(self):
        from generator.cli.parser import build_parser

        parser = build_parser()
        args = parser.parse_args(["current"])
        assert args.command == "current"
        assert args.format is None

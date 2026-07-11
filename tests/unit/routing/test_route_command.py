"""Tests for the `route` CLI command wiring."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


from generator.cli.commands import COMMAND_HANDLERS
from generator.cli.commands.route import cmd_route
from generator.cli.parser import build_parser


def _args(**kw) -> argparse.Namespace:
    base = dict(
        prompt="",
        format="claude",
        target=None,
        apply=False,
        mode="off",
        timeout=4.0,
        min_confidence=0.35,
        classifier=None,
        json=False,
        top=3,
    )
    base.update(kw)
    return argparse.Namespace(**base)


def test_registered_in_handlers():
    assert COMMAND_HANDLERS["route"] is cmd_route


def test_parser_accepts_route():
    parser = build_parser()
    ns = parser.parse_args(["route", "review my python", "-f", "claude"])
    assert ns.command == "route"
    assert ns.prompt == "review my python"
    assert ns.mode == "prompt"  # default


def test_dry_run_json_reports_recommendation(tmp_path: Path, capsys):
    args = _args(
        prompt="review my python module for bugs",
        target=["project", str(tmp_path)],
        json=True,
    )
    rc = cmd_route(args)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["recommended"] == "review-python"
    # No cache in a fresh project target -> cannot switch.
    assert payload["switched"] is False
    assert payload["skipped_reason"] in {"not-cached", "low-confidence"}


def test_dry_run_human_output(tmp_path: Path, capsys):
    args = _args(
        prompt="write pytest tests for my python code",
        target=["project", str(tmp_path)],
        json=False,
    )
    rc = cmd_route(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "test-python" in out
    assert "recommended" in out


def test_apply_mode_off_never_switches(tmp_path: Path, capsys):
    args = _args(
        prompt="review my python module",
        target=["project", str(tmp_path)],
        apply=True,
        mode="off",
        json=True,
    )
    rc = cmd_route(args)
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["switched"] is False

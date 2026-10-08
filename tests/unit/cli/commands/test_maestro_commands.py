"""Unit tests for the route (context mode), recipe --format json, set-active and route-hook commands."""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import pytest

from generator.cli.commands import route as route_cmd
from generator.cli.commands import set_active as set_active_cmd
from generator.cli.main import main
from generator.routing import hook_install
from generator.worktree import GitContext

pytestmark = [pytest.mark.unit, pytest.mark.cli]


def _main(monkeypatch, *argv: str) -> int:
    monkeypatch.setattr(sys, "argv", ["personetta", *argv])
    return main()


# -- route ------------------------------------------------------------------


def test_route_context_json_and_human(monkeypatch, capsys, tmp_path):
    (tmp_path / "a.py").write_text("x", encoding="utf-8")
    assert _main(monkeypatch, "route", "--json", "--repo", str(tmp_path)) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["recipe"] == "implement-python" and doc["hash"].startswith("sha256:")

    assert (
        _main(monkeypatch, "route", "--repo", str(tmp_path), "--lifecycle", "review") == 0
    )
    assert capsys.readouterr().out.startswith("review-python")


def test_route_context_nothing_fits_exits_2(monkeypatch, capsys, tmp_path):
    assert _main(monkeypatch, "route", "--json", "--repo", str(tmp_path)) == 2
    doc = json.loads(capsys.readouterr().out)
    assert doc["recipe"] is None and doc["reason"]
    assert _main(monkeypatch, "route", "--repo", str(tmp_path)) == 2
    assert "no supported language" in capsys.readouterr().out


def test_route_context_never_prints_a_traceback(monkeypatch, capsys):
    def boom(**_kw):
        raise RuntimeError("kaput")

    monkeypatch.setattr(route_cmd, "resolve_context", boom)
    assert _main(monkeypatch, "route", "--json", "--language", "python") == 2
    assert "route failed: kaput" in json.loads(capsys.readouterr().out)["reason"]


def test_route_prompt_mode_needs_prompt_and_format(monkeypatch, capsys):
    assert _main(monkeypatch, "route") == 2
    assert "required" in capsys.readouterr().err


def test_route_prompt_mode_human_output(monkeypatch, capsys, tmp_path):
    code = _main(
        monkeypatch,
        "route",
        "review my python code",
        "-f",
        "claude",
        "--target",
        "project",
        str(tmp_path),
    )
    assert code == 0 and "Prompt routed for" in capsys.readouterr().out


# -- recipe --format json ---------------------------------------------------


def test_recipe_json_stdout_and_file(monkeypatch, capsys, tmp_path):
    assert _main(monkeypatch, "recipe", "implement-python", "--format", "json") == 0
    stdout_doc = json.loads(capsys.readouterr().out)
    out = tmp_path / "nested" / "r.json"
    code = _main(
        monkeypatch, "recipe", "implement-python", "--format", "json", "-o", str(out)
    )
    assert code == 0 and "Written to" in capsys.readouterr().out
    assert json.loads(out.read_text(encoding="utf-8")) == stdout_doc
    assert b"\r\n" not in out.read_bytes()


def test_recipe_json_rejects_install(monkeypatch, capsys):
    code = _main(
        monkeypatch, "recipe", "implement-python", "--format", "json", "--install"
    )
    assert code == 1 and "does not support" in capsys.readouterr().err


def test_recipe_json_conflict_exits_1(monkeypatch, capsys):
    from generator.cli.commands import recipe as recipe_cmd
    from generator.merge import MergeWarning

    monkeypatch.setattr(
        recipe_cmd, "export_recipe", lambda *a, **k: ({}, [MergeWarning("error", "bad")])
    )
    code = _main(monkeypatch, "recipe", "implement-python", "--format", "json")
    assert code == 1 and "Conflict" in capsys.readouterr().err


# -- set-active helpers -----------------------------------------------------


def _ns(**kw):
    base = dict(target=None, use_global=False)
    base.update(kw)
    return argparse.Namespace(**base)


def test_targets_global(monkeypatch, tmp_path):
    home = Path.home()
    assert set_active_cmd._targets_global(None, home)
    assert set_active_cmd._targets_global(["global"], home)
    assert not set_active_cmd._targets_global(["project"], home)
    assert not set_active_cmd._targets_global(None, tmp_path)


def test_worktree_project_root(monkeypatch, tmp_path):
    root = tmp_path / "root"
    monkeypatch.setattr(
        set_active_cmd,
        "git_context",
        lambda p: GitContext(root=root, is_linked_worktree=True),
    )
    assert set_active_cmd._worktree_project_root(["project"], tmp_path / "sub") == root
    assert set_active_cmd._worktree_project_root(["project", "x"], tmp_path) == tmp_path
    monkeypatch.setattr(set_active_cmd, "git_context", lambda p: None)
    assert set_active_cmd._worktree_project_root(["project"], tmp_path) == tmp_path


@pytest.mark.parametrize(
    ("context", "use_global", "refused"),
    [
        (GitContext(Path("w"), True), False, True),
        (GitContext(Path("w"), True), True, False),
        (GitContext(Path("w"), False), False, False),
        (None, False, False),
    ],
)
def test_refuse_global_in_worktree(monkeypatch, capsys, context, use_global, refused):
    monkeypatch.setattr(set_active_cmd, "git_context", lambda p: context)
    args = _ns(use_global=use_global)
    assert set_active_cmd._refuse_global_in_worktree(args, Path.home()) is refused
    assert ("Refusing" in capsys.readouterr().err) is refused


def test_project_target_is_never_refused(monkeypatch, tmp_path):
    monkeypatch.setattr(
        set_active_cmd, "git_context", lambda p: GitContext(tmp_path, True)
    )
    args = _ns(target=["project", str(tmp_path)])
    assert not set_active_cmd._refuse_global_in_worktree(args, tmp_path)


def test_cmd_set_active_returns_exit_refused(monkeypatch):
    monkeypatch.setattr(
        set_active_cmd, "git_context", lambda p: GitContext(Path("w"), True)
    )
    args = _ns(name="implement-python", format="claude", whatif=False)
    assert set_active_cmd.cmd_set_active(args) == set_active_cmd.EXIT_REFUSED


# -- route-hook -------------------------------------------------------------


def test_route_hook_install_status_uninstall(monkeypatch, capsys, tmp_path):
    root = ["--format", "claude", "--target", "project", str(tmp_path)]
    assert _main(monkeypatch, "route-hook", "--status", *root) == 0
    assert "not installed" in capsys.readouterr().out
    assert _main(monkeypatch, "route-hook", "--install", *root) == 0
    assert "Installed" in capsys.readouterr().out
    assert _main(monkeypatch, "route-hook", "--status", *root) == 0
    assert "installed" in capsys.readouterr().out.replace("not installed", "")
    assert _main(monkeypatch, "route-hook", "--uninstall", *root) == 0
    assert "Removed" in capsys.readouterr().out
    assert _main(monkeypatch, "route-hook", "--uninstall", *root) == 0
    assert "No auto-route hook" in capsys.readouterr().out


def test_route_hook_runtime_reads_stdin(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
    code = _main(
        monkeypatch,
        "route-hook",
        "--format",
        "claude",
        "--target",
        "project",
        str(tmp_path),
    )
    assert code == 0 and capsys.readouterr().out == ""


def test_hook_install_survives_corrupt_and_foreign_settings(tmp_path):
    settings = hook_install.settings_path(tmp_path)
    settings.parent.mkdir(parents=True)
    settings.write_text("{broken", encoding="utf-8")
    assert not hook_install.is_installed(tmp_path)
    settings.write_text("[1]", encoding="utf-8")
    assert not hook_install.is_installed(tmp_path)
    settings.write_text(
        json.dumps({"hooks": {"PreToolUse": [{"hooks": [{"command": "other"}]}]}}),
        encoding="utf-8",
    )
    hook_install.install_hook(tmp_path, fmt="claude", base_dir=tmp_path)
    assert hook_install.uninstall_hook(tmp_path)
    kept = json.loads(settings.read_text(encoding="utf-8"))
    assert kept["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == "other"


def test_recipe_json_stdout_is_utf8_on_a_narrow_console(monkeypatch):
    raw = io.BytesIO()
    console = io.TextIOWrapper(raw, encoding="cp1252", errors="strict")
    monkeypatch.setattr(sys, "stdout", console)
    assert _main(monkeypatch, "recipe", "test-csharp", "--format", "json") == 0
    console.flush()
    assert json.loads(raw.getvalue().decode("utf-8"))["recipe"] == "test-csharp"

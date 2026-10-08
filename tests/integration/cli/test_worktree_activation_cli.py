"""Per-worktree activation and the file-routed hook, proven through the CLI entry point.

Every test runs against a throw-away HOME (HOME and USERPROFILE overridden); the
autouse guard fails the test if the real ``~/.claude/rules`` files change.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from generator.cli.main import main

pytestmark = [pytest.mark.integration, pytest.mark.cli]

REAL_RULES = Path.home() / ".claude" / "rules"
ACTIVE = Path(".claude") / "rules" / "personetta-active.md"
RECIPES = (
    "implement-csharp",
    "implement-javascript",
    "implement-python",
    "implement-powershell",
    "implement-tsql",
    "review-csharp",
)


def _fingerprint(root: Path) -> dict[str, str]:
    if not root.is_dir():
        return {}
    return {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


@pytest.fixture(autouse=True)
def _real_home_untouched():
    before = _fingerprint(REAL_RULES)
    yield
    assert _fingerprint(REAL_RULES) == before, "test wrote to the real ~/.claude/rules"


@pytest.fixture
def fake_home(tmp_path, monkeypatch) -> Path:
    home = tmp_path / "home"
    cache = home / ".personetta" / "claude-recipes"
    cache.mkdir(parents=True)
    for name in RECIPES:
        (cache / f"{name}.md").write_text(f"# {name}\nbody of {name}\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    assert Path.home() == home
    return home


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def repo(tmp_path, fake_home) -> Path:
    root = tmp_path / "main"
    root.mkdir()
    _git(root, "init", "-q")
    (root / "seed.txt").write_text("x", encoding="utf-8")
    _git(root, "add", "seed.txt")
    _git(root, "commit", "-q", "-m", "seed")
    return root


@pytest.fixture
def worktree(tmp_path, repo) -> Path:
    wt = tmp_path / "wt-a"
    _git(repo, "worktree", "add", "-q", str(wt), "-b", "feature-a")
    return wt


def _set_active(monkeypatch, capsys, cwd: Path, *argv: str) -> tuple[int, str, str]:
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(sys, "argv", ["personetta", "set-active", *argv])
    code = main()
    out = capsys.readouterr()
    return code, out.out, out.err


def _hook(monkeypatch, capsys, file_path: Path | str, *, cwd: Path, env=None) -> dict:
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": str(file_path)},
        "cwd": str(cwd),
    }
    for key, value in (env or {}).items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "personetta",
            "route-hook",
            "--format",
            "claude",
            "--target",
            "project",
            str(Path.home()),
        ],
    )
    assert main() == 0
    text = capsys.readouterr().out
    return json.loads(text) if text else {}


# ── set-active: refusal and override ──────────────────────────────────────────


def test_global_write_refused_inside_linked_worktree(
    monkeypatch, capsys, fake_home, worktree
):
    code, _out, err = _set_active(
        monkeypatch, capsys, worktree, "implement-csharp", "--format", "claude"
    )
    assert code == 2
    assert "Refusing" in err and "--global" in err and "--target project" in err
    assert not (fake_home / ACTIVE).exists()


def test_explicit_global_target_also_refused(monkeypatch, capsys, fake_home, worktree):
    code, _out, err = _set_active(
        monkeypatch, capsys, worktree, "implement-csharp", "-f", "claude", "-t", "global"
    )
    assert code == 2 and "Refusing" in err
    assert not (fake_home / ACTIVE).exists()


def test_global_flag_overrides_refusal(monkeypatch, capsys, fake_home, worktree):
    code, _out, _err = _set_active(
        monkeypatch, capsys, worktree, "implement-csharp", "-f", "claude", "--global"
    )
    assert code == 0
    assert "body of implement-csharp" in (fake_home / ACTIVE).read_text(encoding="utf-8")


def test_main_checkout_still_writes_global(monkeypatch, capsys, fake_home, repo):
    code, _out, _err = _set_active(
        monkeypatch, capsys, repo, "implement-python", "-f", "claude"
    )
    assert code == 0
    assert (fake_home / ACTIVE).is_file()


def test_plain_directory_is_not_a_worktree(monkeypatch, capsys, fake_home, tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    code, _out, _err = _set_active(
        monkeypatch, capsys, plain, "implement-python", "-f", "claude"
    )
    assert code == 0
    assert (fake_home / ACTIVE).is_file()


# ── set-active: project mode is per worktree ──────────────────────────────────


def test_project_target_writes_only_the_worktree(
    monkeypatch, capsys, fake_home, repo, worktree
):
    sub = worktree / "deep" / "dir"
    sub.mkdir(parents=True)
    code, out, _err = _set_active(
        monkeypatch, capsys, sub, "implement-csharp", "-f", "claude", "-t", "project"
    )
    assert code == 0
    written = worktree / ACTIVE
    assert written.name in out
    assert "body of implement-csharp" in written.read_text(encoding="utf-8")
    assert not (sub / ACTIVE).exists()  # bare 'project' means the checkout root
    assert not (repo / ACTIVE).exists()
    assert not (fake_home / ACTIVE).exists()


def test_two_worktrees_hold_different_active_files(
    monkeypatch, capsys, tmp_path, repo, worktree
):
    other = tmp_path / "wt-b"
    _git(repo, "worktree", "add", "-q", str(other), "-b", "feature-b")
    for wt, recipe in ((worktree, "implement-csharp"), (other, "implement-javascript")):
        code, _o, _e = _set_active(
            monkeypatch, capsys, wt, recipe, "-f", "claude", "-t", "project"
        )
        assert code == 0
    assert "implement-csharp" in (worktree / ACTIVE).read_text(encoding="utf-8")
    assert "implement-javascript" in (other / ACTIVE).read_text(encoding="utf-8")


def test_project_target_unknown_recipe_errors(monkeypatch, capsys, worktree):
    code, _out, err = _set_active(
        monkeypatch, capsys, worktree, "no-such-recipe", "-f", "claude", "-t", "project"
    )
    assert code == 1 and "No cached Claude recipe" in err


# ── route-hook: file-routed switching ─────────────────────────────────────────


def test_hook_switches_per_file_in_one_worktree(
    monkeypatch, capsys, fake_home, repo, worktree
):
    result = _hook(monkeypatch, capsys, worktree / "src" / "App.cs", cwd=worktree)
    assert result["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert "body of implement-csharp" in result["hookSpecificOutput"]["additionalContext"]
    assert "implement-csharp" in (worktree / ACTIVE).read_text(encoding="utf-8")

    _hook(monkeypatch, capsys, worktree / "web" / "app.ts", cwd=worktree)
    assert "implement-javascript" in (worktree / ACTIVE).read_text(encoding="utf-8")

    for name, recipe in (
        ("a.py", "implement-python"),
        ("m.psm1", "implement-powershell"),
        ("s.ps1", "implement-powershell"),
        ("q.sql", "implement-tsql"),
    ):
        _hook(monkeypatch, capsys, worktree / name, cwd=worktree)
        assert recipe in (worktree / ACTIVE).read_text(encoding="utf-8")

    assert not (repo / ACTIVE).exists()
    assert not (fake_home / ACTIVE).exists()


def test_hook_is_idempotent_when_answer_unchanged(monkeypatch, capsys, worktree):
    _hook(monkeypatch, capsys, worktree / "a.cs", cwd=worktree)
    active = worktree / ACTIVE
    state = worktree / ".personetta" / "claude-active.json"
    stamp = (active.stat().st_mtime_ns, state.stat().st_mtime_ns)
    result = _hook(monkeypatch, capsys, worktree / "b.cs", cwd=worktree)
    assert result == {}
    assert (active.stat().st_mtime_ns, state.stat().st_mtime_ns) == stamp


def test_hook_restores_deleted_active_file(monkeypatch, capsys, worktree):
    _hook(monkeypatch, capsys, worktree / "a.cs", cwd=worktree)
    (worktree / ACTIVE).unlink()
    _hook(monkeypatch, capsys, worktree / "a.cs", cwd=worktree)
    assert (worktree / ACTIVE).is_file()


def test_hook_unknown_extension_does_nothing(monkeypatch, capsys, worktree):
    result = _hook(monkeypatch, capsys, worktree / "notes.md", cwd=worktree)
    assert result == {}
    assert not (worktree / ACTIVE).exists()
    assert not (worktree / ".personetta").exists()


def test_hook_outside_git_never_writes(monkeypatch, capsys, fake_home, tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    result = _hook(monkeypatch, capsys, plain / "a.cs", cwd=plain)
    assert result == {}
    assert not (plain / ACTIVE).exists()
    assert not (fake_home / ACTIVE).exists()


def test_hook_relative_path_uses_payload_cwd(monkeypatch, capsys, worktree):
    _hook(monkeypatch, capsys, "src/App.cs", cwd=worktree)
    assert "implement-csharp" in (worktree / ACTIVE).read_text(encoding="utf-8")


def test_hook_uninstalled_recipe_is_silent_noop(monkeypatch, capsys, fake_home, worktree):
    (fake_home / ".personetta" / "claude-recipes" / "implement-csharp.md").unlink()
    assert _hook(monkeypatch, capsys, worktree / "a.cs", cwd=worktree) == {}
    assert not (worktree / ACTIVE).exists()


def test_hook_lifecycle_env_selects_family(monkeypatch, capsys, worktree):
    _hook(
        monkeypatch,
        capsys,
        worktree / "a.cs",
        cwd=worktree,
        env={"PERSONETTA_ROUTE_LIFECYCLE": "review"},
    )
    assert "review-csharp" in (worktree / ACTIVE).read_text(encoding="utf-8")


def test_hook_mode_off_does_nothing(monkeypatch, capsys, worktree):
    result = _hook(
        monkeypatch,
        capsys,
        worktree / "a.cs",
        cwd=worktree,
        env={"PERSONETTA_ROUTE_MODE": "off"},
    )
    assert result == {} and not (worktree / ACTIVE).exists()


def test_hook_prompt_payload_still_works(monkeypatch, capsys, worktree):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"prompt": ""})))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "personetta",
            "route-hook",
            "--format",
            "claude",
            "--target",
            "project",
            str(worktree),
        ],
    )
    assert main() == 0
    assert capsys.readouterr().out == ""


def test_install_registers_file_hook(monkeypatch, capsys, tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "personetta",
            "route-hook",
            "--install",
            "--format",
            "claude",
            "--target",
            "project",
            str(root),
        ],
    )
    assert main() == 0
    settings = json.loads(
        (root / ".claude" / "settings.json").read_text(encoding="utf-8")
    )
    assert set(settings["hooks"]) == {"UserPromptSubmit", "PreToolUse"}
    assert (
        settings["hooks"]["PreToolUse"][0]["matcher"]
        == "Edit|Write|MultiEdit|NotebookEdit"
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "personetta",
            "route-hook",
            "--uninstall",
            "--format",
            "claude",
            "--target",
            "project",
            str(root),
        ],
    )
    assert main() == 0
    settings = json.loads(
        (root / ".claude" / "settings.json").read_text(encoding="utf-8")
    )
    assert "hooks" not in settings
    assert os.path.isdir(root)

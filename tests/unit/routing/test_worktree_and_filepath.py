"""Unit tests for git worktree detection and file-path recipe mapping."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from generator import worktree
from generator.routing.filepath import language_for_path, recipe_for_path

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    ("name", "language"),
    [
        ("A.cs", "csharp"),
        ("a.TS", "javascript"),
        ("a.tsx", "javascript"),
        ("a.py", "python"),
        ("a.ps1", "powershell"),
        ("a.psm1", "powershell"),
        ("a.sql", "tsql"),
        ("a.md", None),
        ("Makefile", None),
    ],
)
def test_language_for_path(name, language):
    assert language_for_path(Path(name)) == language


def test_recipe_for_path_lifecycle_and_default():
    assert recipe_for_path(Path("a.cs")) == "implement-csharp"
    assert recipe_for_path(Path("a.cs"), "test") == "test-csharp"
    assert recipe_for_path(Path("a.cs"), "bogus") == "implement-csharp"
    assert recipe_for_path(Path("a.txt"), "test") is None


def test_git_context_plain_directory(tmp_path):
    assert worktree.git_context(tmp_path) is None


def test_git_context_nonexistent_path_walks_up(tmp_path):
    assert worktree.git_context(tmp_path / "no" / "such" / "file.cs") is None


def test_git_context_file_path_uses_parent(tmp_path):
    f = tmp_path / "f.txt"
    f.write_text("x", encoding="utf-8")
    assert worktree.git_context(f) is None


def test_git_context_main_and_linked(tmp_path):
    def git(cwd, *a):
        subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@e.x", *a],
            cwd=cwd,
            check=True,
            capture_output=True,
        )

    main = tmp_path / "m"
    main.mkdir()
    git(main, "init", "-q")
    (main / "f").write_text("x", encoding="utf-8")
    git(main, "add", "f")
    git(main, "commit", "-q", "-m", "s")
    linked = tmp_path / "l"
    git(main, "worktree", "add", "-q", str(linked), "-b", "b")

    ctx_main = worktree.git_context(main)
    ctx_linked = worktree.git_context(linked)
    assert ctx_main is not None and not ctx_main.is_linked_worktree
    assert ctx_main.root == main.resolve()
    assert ctx_linked is not None and ctx_linked.is_linked_worktree
    assert ctx_linked.root == linked.resolve()


def test_git_context_without_git_binary(tmp_path, monkeypatch):
    def boom(*_a, **_k):
        raise FileNotFoundError("git")

    monkeypatch.setattr(worktree.subprocess, "run", boom)
    assert worktree.git_context(tmp_path) is None


def test_git_context_unexpected_output(tmp_path, monkeypatch):
    done = subprocess.CompletedProcess([], 0, stdout="only-one-line\n", stderr="")
    monkeypatch.setattr(worktree.subprocess, "run", lambda *a, **k: done)
    assert worktree.git_context(tmp_path) is None

"""Unit tests for context (language + lifecycle) resolution."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from generator.routing import context
from generator.routing.context import (
    ContextResult,
    detect_languages,
    languages_for_paths,
    recipe_family,
    scan_languages,
    normalize_language,
    parse_languages,
    resolve_context,
)

pytestmark = [pytest.mark.unit]


def _git(root: Path, *argv: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *argv],
        cwd=root,
        check=True,
        timeout=60,
    )


def _touch(root: Path, *names: str) -> None:
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x", encoding="utf-8")


def test_normalize_and_parse_languages():
    assert normalize_language(" TS ") == "javascript"
    assert normalize_language("cobol") is None
    known, unknown = parse_languages("c#, typescript,, ts, cobol")
    assert known == ["csharp", "javascript"] and unknown == ["cobol"]


def test_detect_orders_by_source_count_and_skips_vendored(tmp_path):
    _touch(tmp_path, "a.py", "b.py", "c.py", "x.cs", "node_modules/pkg/index.js")
    assert detect_languages(tmp_path) == ["python", "csharp"]


def test_detect_manifest_alone_counts_and_deep_nesting_is_counted(tmp_path):
    _touch(tmp_path, "App.csproj", "src/Project/Folder/Sub/More/deep.py")
    assert detect_languages(tmp_path) == ["python", "csharp"]
    assert scan_languages(tmp_path)[1] == {"python": 1, "csharp": 0}


def test_depth_is_only_a_safety_net(tmp_path, monkeypatch):
    monkeypatch.setattr(context, "MAX_DEPTH", 2)
    _touch(tmp_path, "App.csproj", "a/b/c/deep.py")
    assert detect_languages(tmp_path) == ["csharp"]


def test_walk_skips_dot_folders_and_gitignored(tmp_path):
    _touch(
        tmp_path,
        ".claude/worktrees/w1/a.ps1",
        ".claude/worktrees/w1/b.ps1",
        "generated/x.ps1",
        "src/keep.cs",
        "src/skip.log.py",
        "lib/pkg.egg-info/z.ps1",
    )
    (tmp_path / ".gitignore").write_text(
        "# comment\n!keep\ngenerated/\n*.log.py\n\n", encoding="utf-8"
    )
    langs, counts = scan_languages(tmp_path)
    assert langs == ["csharp"] and counts == {"csharp": 1}


def test_gitignore_anchored_and_file_patterns(tmp_path):
    _touch(tmp_path, "a/out/x.py", "b/out/y.py", "top.py")
    (tmp_path / ".gitignore").write_text("a/out\ntop.py\n", encoding="utf-8")
    assert scan_languages(tmp_path)[1] == {"python": 1}


def test_git_checkout_counts_tracked_files_only(tmp_path):
    _touch(
        tmp_path,
        "a.cs",
        "b.cs",
        ".claude/worktrees/w/1.ps1",
        ".claude/worktrees/w/2.ps1",
        "c.ps1",
    )
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "a.cs", "b.cs", "c.ps1")
    _git(tmp_path, "commit", "-q", "-m", "x")
    assert scan_languages(tmp_path) == (
        ["csharp", "powershell"],
        {"csharp": 2, "powershell": 1},
    )


def test_missing_git_or_empty_index_falls_back_to_walk(tmp_path, monkeypatch):
    _touch(tmp_path, "a.py")
    _git(tmp_path, "init", "-q")  # git repo with nothing tracked yet
    assert scan_languages(tmp_path)[1] == {"python": 1}

    def no_git(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(context.subprocess, "run", no_git)
    assert context._git_tracked_files(tmp_path) is None
    assert scan_languages(tmp_path)[1] == {"python": 1}


def test_git_failure_returns_none(tmp_path):
    assert context._git_tracked_files(tmp_path) is None


def test_languages_for_paths_orders_by_count_and_ignores_unknown(tmp_path):
    counts = languages_for_paths(
        tmp_path, ["web/a.ts", "web/b.tsx", "src/x.cs", "README.md", "  ", "p.py"]
    )
    assert counts == {"javascript": 2, "csharp": 1, "python": 1}


def test_recipe_family():
    assert recipe_family("review-csharp") == ("csharp", "review")
    assert recipe_family("implement-csharp-backend") == (None, None)
    assert recipe_family("general") == (None, None)
    assert recipe_family("design-diagram") == (None, None)


def test_detect_stops_after_max_files(tmp_path, monkeypatch):
    monkeypatch.setattr(context, "MAX_FILES", 2)
    _touch(tmp_path, "a.py", "b.py", "c.py")
    assert detect_languages(tmp_path) == ["python"]


def test_to_dict_failure_and_success_forms():
    assert ContextResult(False, "nope").to_dict() == {"recipe": None, "reason": "nope"}
    ok = ContextResult(True, "why", {"recipe": "r"}, [{"recipe": "s"}]).to_dict()
    assert ok == {"recipe": "r", "reason": "why", "also": [{"recipe": "s"}]}
    assert "also" not in ContextResult(True, "why", {"recipe": "r"}).to_dict()


def _resolve(real_project, **kw):
    names = kw.pop("names", None)
    if names is None:
        from generator.loader import list_recipes

        names = {r["name"] for r in list_recipes(real_project)}
    base = dict(
        repo=Path("."),
        language_spec=None,
        lifecycle="implement",
        recipe_names=names,
        base_dir=real_project,
    )
    base.update(kw)
    return resolve_context(**base)


def test_unknown_lifecycle(real_project):
    assert "unknown lifecycle" in _resolve(real_project, lifecycle="ship").reason


def test_explicit_languages_primary_and_also(real_project):
    result = _resolve(real_project, language_spec="csharp,typescript")
    assert result.ok and result.primary["recipe"] == "implement-csharp"
    assert [a["recipe"] for a in result.also] == ["implement-javascript"]


def test_unsupported_and_empty_language_specs(real_project):
    assert (
        "unsupported language: cobol"
        in _resolve(real_project, language_spec="cobol").reason
    )
    assert not _resolve(real_project, language_spec=" , ").ok


def test_detect_branches(real_project, tmp_path):
    assert "repo path not found" in _resolve(real_project, repo=tmp_path / "gone").reason
    assert "no supported language" in _resolve(real_project, repo=tmp_path).reason
    _touch(tmp_path, "a.py")
    result = _resolve(real_project, repo=tmp_path)
    assert result.ok and result.reason.startswith("detected python 1")


def test_paths_decide_language_then_fall_back(real_project, tmp_path):
    _touch(tmp_path, "a.py")
    hit = _resolve(real_project, repo=tmp_path, paths=["web/App.tsx", "x.ts", "y.py"])
    assert hit.primary["recipe"] == "implement-javascript"
    assert [a["recipe"] for a in hit.also] == ["implement-python"]
    assert hit.reason.startswith("paths javascript 2, python 1")
    miss = _resolve(real_project, repo=tmp_path, paths=["README.md"])
    assert miss.primary["recipe"] == "implement-python"
    assert "no --paths entry matched a language; detected python 1" in miss.reason
    forced = _resolve(real_project, repo=tmp_path, paths=["a.cs"], language_spec="python")
    assert forced.primary["recipe"] == "implement-python"
    assert forced.reason.startswith("language python")


def test_missing_recipe_noted_or_fatal(real_project):
    names = {"implement-python"}
    partial = _resolve(real_project, language_spec="python,csharp", names=names)
    assert partial.ok and "no recipe: implement-csharp" in partial.reason
    assert (
        "no recipe fits"
        in _resolve(real_project, language_spec="csharp", names=names).reason
    )


def test_compose_failure_is_reported(real_project, monkeypatch):
    monkeypatch.setattr(context, "export_recipe", lambda *a, **k: ({}, []))
    result = _resolve(real_project, language_spec="python")
    assert not result.ok and "failed to compose" in result.reason

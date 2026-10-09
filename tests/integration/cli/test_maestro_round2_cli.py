"""Round-2 Maestro follow-ups through main(): detection, recipe --all, route --paths."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

from generator.cli.main import main

pytestmark = [pytest.mark.integration, pytest.mark.cli]

ROOT = Path(__file__).resolve().parents[3]


def _git(root: Path, *argv: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *argv],
        cwd=root,
        check=True,
        timeout=60,
    )


def _touch(root: Path, *names: str) -> Path:
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x", encoding="utf-8")
    return root


def _route(monkeypatch, capsys, *argv: str) -> tuple[int, dict]:
    monkeypatch.setattr(sys, "argv", ["personetta", "route", "--json", *argv])
    code = main()
    return code, json.loads(capsys.readouterr().out)


def _recipe_all(monkeypatch, capsys, *argv: str) -> tuple[int, str, str]:
    monkeypatch.setattr(sys, "argv", ["personetta", "recipe", *argv])
    code = main()
    captured = capsys.readouterr()
    return code, captured.out, captured.err


@pytest.fixture
def csharp_repo(tmp_path):
    """Tracked C# (deeply nested) outnumbers tracked PowerShell; untracked worktrees hold more PS."""
    repo = tmp_path / "repo"
    tracked = [f"src/Project/Folder/Sub/F{i}.cs" for i in range(4)]
    tracked += ["src/Project/App.csproj", "tools/a.ps1", "tools/b.ps1", "web/src/App.tsx"]
    _touch(repo, *tracked)
    _touch(repo, *[f".claude/worktrees/w{i}/x{i}.ps1" for i in range(30)])
    _git(repo.parent, "init", "-q", str(repo))
    _git(repo, "add", *tracked)
    _git(repo, "commit", "-q", "-m", "seed")
    return repo


# --- item 1: detection ----------------------------------------------------


def test_worktree_noise_and_deep_files_do_not_change_primary(
    csharp_repo, monkeypatch, capsys, real_project
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    code, doc = _route(monkeypatch, capsys, "--repo", str(csharp_repo))
    assert code == 0
    assert doc["recipe"] == "implement-csharp"
    assert doc["reason"].startswith("detected csharp 4, powershell 2, javascript 1")
    assert [a["recipe"] for a in doc["also"]] == [
        "implement-powershell",
        "implement-javascript",
    ]


def test_non_git_walk_counts_in_reason_and_skips_dot_folders(
    tmp_path, monkeypatch, capsys, real_project
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    _touch(tmp_path, "a.cs", "ignored/z.ps1", ".claude/worktrees/w/1.ps1", "x.ps1")
    (tmp_path / ".gitignore").write_text("ignored/\n", encoding="utf-8")
    code, doc = _route(
        monkeypatch, capsys, "--repo", str(tmp_path), "--lifecycle", "test"
    )
    assert code == 0 and doc["recipe"] == "test-csharp"
    assert doc["reason"] == "detected csharp 1, powershell 1, lifecycle test"


# --- item 3: --paths ------------------------------------------------------


def test_paths_pick_javascript_inside_csharp_repo(
    csharp_repo, monkeypatch, capsys, real_project
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    code, doc = _route(
        monkeypatch, capsys, "--repo", str(csharp_repo), "--paths", "web/src/App.tsx"
    )
    assert code == 0
    assert doc["recipe"] == "implement-javascript"
    assert doc["reason"].startswith("paths javascript 1")
    assert "also" not in doc


def test_paths_majority_primary_with_also(
    csharp_repo, monkeypatch, capsys, real_project
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    code, doc = _route(
        monkeypatch,
        capsys,
        "--repo",
        str(csharp_repo),
        "--paths",
        "src/A.cs,web/a.ts,web/b.ts,notes.md",
        "--lifecycle",
        "review",
    )
    assert code == 0 and doc["recipe"] == "review-javascript"
    assert [a["recipe"] for a in doc["also"]] == ["review-csharp"]


def test_unmatched_path_falls_back_to_detection_and_says_so(
    csharp_repo, monkeypatch, capsys, real_project
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    code, doc = _route(
        monkeypatch, capsys, "--repo", str(csharp_repo), "--paths", "README.md"
    )
    assert code == 0 and doc["recipe"] == "implement-csharp"
    assert "no --paths entry matched a language; detected csharp 4" in doc["reason"]


def test_language_wins_over_paths(csharp_repo, monkeypatch, capsys, real_project) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    code, doc = _route(
        monkeypatch,
        capsys,
        "--repo",
        str(csharp_repo),
        "--paths",
        "web/src/App.tsx",
        "--language",
        "python",
    )
    assert code == 0 and doc["recipe"] == "implement-python"


# --- item 2: recipe --all -------------------------------------------------


def test_all_writes_identical_bytes_and_index(
    tmp_path, monkeypatch, capsys, real_project
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    out = tmp_path / "snap"
    code, stdout, _ = _recipe_all(
        monkeypatch, capsys, "--all", "--format", "json", "-o", str(out)
    )
    assert code == 0 and "index.json" in stdout
    index = json.loads((out / "index.json").read_text(encoding="utf-8"))
    schema = json.loads(
        (ROOT / "data/schemas/recipe-index.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.Draft7Validator(schema).validate(index)
    names = [r["name"] for r in index["recipes"]]
    assert names == sorted(names) and len(names) == len(list(out.glob("*.json"))) - 1
    row = next(r for r in index["recipes"] if r["name"] == "review-csharp")
    assert (row["language"], row["lifecycle"]) == ("csharp", "review")
    general = next(r for r in index["recipes"] if r["name"] == "general")
    assert (general["language"], general["lifecycle"]) == (None, None)

    single = tmp_path / "single.json"
    code, _, _ = _recipe_all(
        monkeypatch, capsys, "review-csharp", "--format", "json", "-o", str(single)
    )
    assert code == 0
    assert (out / "review-csharp.json").read_bytes() == single.read_bytes()
    assert row["hash"] == json.loads(single.read_text(encoding="utf-8"))["hash"]

    again = tmp_path / "again"
    _recipe_all(monkeypatch, capsys, "--all", "--format", "json", "-o", str(again))
    assert (again / "index.json").read_bytes() == (out / "index.json").read_bytes()


def test_all_filters_narrow(tmp_path, monkeypatch, capsys, real_project) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    out = tmp_path / "f"
    code, _, _ = _recipe_all(
        monkeypatch,
        capsys,
        "--all",
        "--format",
        "json",
        "-o",
        str(out),
        "--language",
        "ts",
    )
    assert code == 0
    assert {
        r["name"] for r in json.loads((out / "index.json").read_text())["recipes"]
    } == {f"{lc}-javascript" for lc in ("implement", "review", "test", "debug", "design")}
    out2 = tmp_path / "f2"
    code, _, _ = _recipe_all(
        monkeypatch,
        capsys,
        "--all",
        "--format",
        "json",
        "-o",
        str(out2),
        "--language",
        "csharp",
        "--lifecycle",
        "test",
    )
    assert code == 0
    assert sorted(p.name for p in out2.glob("*.json")) == [
        "index.json",
        "test-csharp.json",
    ]


def test_all_filter_matching_nothing_exits_2(
    tmp_path, monkeypatch, capsys, real_project
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    code, _, err = _recipe_all(
        monkeypatch,
        capsys,
        "--all",
        "--format",
        "json",
        "-o",
        str(tmp_path / "none"),
        "--language",
        "tsql",
        "--lifecycle",
        "debug",
    )
    assert code == 2 and "No recipe matches" in err
    assert not (tmp_path / "none").exists()


@pytest.mark.parametrize(
    "argv, fragment",
    [
        (["--all", "--format", "claude", "-o", "OUT"], "--all needs"),
        (["--all", "--format", "json"], "--all needs"),
        (["--all", "x", "--format", "json", "-o", "OUT"], "--all needs"),
        (["--all", "--format", "json", "-o", "OUT", "--install"], "--all needs"),
        (
            ["--all", "--format", "json", "-o", "OUT", "--language", "cobol"],
            "unsupported",
        ),
        (["--format", "json"], "recipe name is required"),
        (["x", "--format", "json", "--language", "csharp"], "need --all"),
    ],
)
def test_all_usage_errors_exit_1(
    argv, fragment, tmp_path, monkeypatch, capsys, real_project
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    argv = [str(tmp_path / "o") if a == "OUT" else a for a in argv]
    code, _, err = _recipe_all(monkeypatch, capsys, *argv)
    assert code == 1 and fragment in err


def test_all_conflict_and_compose_failure_exit_1(
    tmp_path, monkeypatch, capsys, real_project
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr("generator.recipe_bundle.export_recipe", lambda n, b: ({}, []))
    code, _, err = _recipe_all(
        monkeypatch,
        capsys,
        "--all",
        "--format",
        "json",
        "-o",
        str(tmp_path / "o"),
        "--language",
        "python",
        "--lifecycle",
        "test",
    )
    assert code == 1 and "failed to compose" in err

    class Warn:
        severity = "error"
        message = "clash"

    monkeypatch.setattr(
        "generator.recipe_bundle.export_recipe",
        lambda n, b: ({"recipe": n, "version": "1", "hash": "h"}, [Warn()]),
    )
    code, _, err = _recipe_all(
        monkeypatch,
        capsys,
        "--all",
        "--format",
        "json",
        "-o",
        str(tmp_path / "o"),
        "--language",
        "python",
        "--lifecycle",
        "test",
    )
    assert code == 1 and "clash" in err

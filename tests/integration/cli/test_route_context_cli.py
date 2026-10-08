"""`route --json` language/lifecycle resolution, proven through the CLI entry point."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from generator.cli.main import main
from generator.recipe_export import export_recipe
from generator.routing.context import detect_languages, parse_languages

pytestmark = [pytest.mark.integration, pytest.mark.cli]


def _run(monkeypatch, capsys, *argv: str) -> tuple[int, dict]:
    monkeypatch.setattr(sys, "argv", ["personetta", "route", "--json", *argv])
    code = main()
    return code, json.loads(capsys.readouterr().out)


def _touch(root: Path, *names: str) -> Path:
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x", encoding="utf-8")
    return root


REPOS = {
    "csharp": ["src/App.csproj", "src/Program.cs"],
    "javascript": ["package.json", "index.ts"],
    "python": ["pyproject.toml", "app.py"],
    "powershell": ["Mod.psm1", "run.ps1"],
    "tsql": ["db/schema.sql"],
}


@pytest.mark.parametrize("lang", sorted(REPOS))
@pytest.mark.parametrize("lifecycle", ["implement", "review", "test", "design"])
def test_each_language_detected_and_explicit(
    lang, lifecycle, tmp_path, monkeypatch, capsys, real_project
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    repo = _touch(tmp_path, *REPOS[lang])
    expected = f"{lifecycle}-{lang}"
    for extra in ([], ["--language", lang]):
        code, doc = _run(
            monkeypatch, capsys, "--repo", str(repo), "--lifecycle", lifecycle, *extra
        )
        assert code == 0
        assert doc["recipe"] == expected
        export, _ = export_recipe(expected, real_project)
        assert (doc["version"], doc["hash"]) == (export["version"], export["hash"])
        assert doc["reason"]
        assert "also" not in doc


def test_csharp_python_typescript_flag_variants(
    tmp_path, monkeypatch, capsys, real_project
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    code, doc = _run(monkeypatch, capsys, "--repo", str(tmp_path), "--language", "ts")
    assert code == 0 and doc["recipe"] == "implement-javascript"


def test_mixed_repo_primary_and_also(tmp_path, monkeypatch, capsys, real_project) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    _touch(tmp_path, "a.csproj", "A.cs", "B.cs", "C.cs", "package.json", "web.ts")
    code, doc = _run(
        monkeypatch, capsys, "--repo", str(tmp_path), "--lifecycle", "review"
    )
    assert code == 0
    assert doc["recipe"] == "review-csharp"
    assert [a["recipe"] for a in doc["also"]] == ["review-javascript"]
    assert doc["also"][0]["hash"].startswith("sha256:")

    code, doc = _run(
        monkeypatch, capsys, "--language", "csharp,typescript", "--lifecycle", "test"
    )
    assert code == 0
    assert doc["recipe"] == "test-csharp"
    assert doc["also"][0]["recipe"] == "test-javascript"


def test_mixed_repo_primary_follows_source_count(
    tmp_path, monkeypatch, capsys, real_project
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    _touch(tmp_path, "a.csproj", "package.json", "1.ts", "2.ts", "3.ts")
    code, doc = _run(monkeypatch, capsys, "--repo", str(tmp_path))
    assert doc["recipe"] == "implement-javascript"
    assert doc["also"][0]["recipe"] == "implement-csharp"


@pytest.mark.parametrize(
    "argv",
    [
        ["--language", "cobol"],
        ["--language", "csharp,cobol"],
        ["--language", ","],
        ["--language", "tsql", "--lifecycle", "debug"],
        ["--repo", "EMPTY"],
        ["--repo", "MISSING"],
    ],
)
def test_nothing_fits_exits_2_with_json_reason(
    argv, tmp_path, monkeypatch, capsys, real_project
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    empty = tmp_path / "empty"
    empty.mkdir()
    argv = [
        str(empty) if a == "EMPTY" else str(tmp_path / "nope") if a == "MISSING" else a
        for a in argv
    ]
    code, doc = _run(monkeypatch, capsys, *argv)
    assert code == 2
    assert doc["recipe"] is None
    assert doc["reason"]


def test_partial_miss_notes_reason(tmp_path, monkeypatch, capsys, real_project) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    code, doc = _run(
        monkeypatch,
        capsys,
        "--language",
        "csharp,tsql",
        "--lifecycle",
        "debug",
    )
    assert code == 0
    assert doc["recipe"] == "debug-csharp"
    assert "debug-tsql" in doc["reason"]


def test_compose_failure_is_json_exit_2(
    tmp_path, monkeypatch, capsys, real_project
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(
        "generator.routing.context.export_recipe", lambda name, base: ({}, [])
    )
    code, doc = _run(monkeypatch, capsys, "--language", "python")
    assert code == 2
    assert "failed to compose" in doc["reason"]


def test_unexpected_error_is_json_exit_2(
    tmp_path, monkeypatch, capsys, real_project
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))

    def boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr("generator.routing.context.export_recipe", boom)
    code, doc = _run(monkeypatch, capsys, "--language", "python")
    assert code == 2
    assert "boom" in doc["reason"]


def test_defaults_to_cwd_and_text_output(
    tmp_path, monkeypatch, capsys, real_project
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    _touch(tmp_path, "x.py")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["personetta", "route", "--lifecycle", "test"])
    assert main() == 0
    assert capsys.readouterr().out.startswith("test-python")

    monkeypatch.setattr(sys, "argv", ["personetta", "route", "--language", "x"])
    assert main() == 2
    assert "unsupported language" in capsys.readouterr().out


def test_prompt_mode_still_requires_format(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["personetta", "route", "review my python"])
    assert main() == 2
    assert "--format" in capsys.readouterr().err


def test_detection_skips_vendored_dirs_and_unknown_lifecycle(tmp_path) -> None:
    _touch(tmp_path, "node_modules/x/package.json", "deep/a/b/c/d/e/f.py", "a.sql")
    assert detect_languages(tmp_path) == ["tsql"]
    assert parse_languages("C#, ts,ts") == (["csharp", "javascript"], [])


def test_unknown_lifecycle_direct(tmp_path, real_project) -> None:
    from generator.routing.context import resolve_context

    result = resolve_context(
        repo=tmp_path,
        language_spec="python",
        lifecycle="ship",
        recipe_names=set(),
        base_dir=real_project,
    )
    assert not result.ok and "lifecycle" in result.reason

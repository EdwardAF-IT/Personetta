"""Unit tests for context (language + lifecycle) resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.routing import context
from generator.routing.context import (
    ContextResult,
    detect_languages,
    normalize_language,
    parse_languages,
    resolve_context,
)

pytestmark = [pytest.mark.unit]


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


def test_detect_manifest_alone_counts_and_depth_is_bounded(tmp_path):
    _touch(tmp_path, "App.csproj", "a/b/c/d/e/deep.py")
    assert detect_languages(tmp_path) == ["csharp"]


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
    assert result.ok and result.reason.startswith("detected python")


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

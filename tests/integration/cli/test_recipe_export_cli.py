"""JSON recipe export (identity, schema, hash), proven through the CLI entry point."""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import jsonschema
import pytest

from generator.cli.main import main
from generator.recipe_export import (
    build_recipe_export,
    content_hash,
    package_version,
    render_export,
)

pytestmark = [pytest.mark.integration, pytest.mark.cli]

CSHARP_DEV = "data/language_specific/csharp/csharp-developer.yaml"
SCHEMA = "data/schemas/recipe-export.schema.json"


def _run(monkeypatch, *argv: str) -> int:
    monkeypatch.setattr(sys, "argv", ["personetta", *argv])
    return main()


@pytest.fixture
def data_copy(real_project: Path, project_layout, monkeypatch) -> Path:
    root = project_layout.root
    shutil.copytree(real_project / "data", project_layout.base.parent)
    monkeypatch.setenv("PERSONETTA_BASE", str(root))
    return root


def _export(monkeypatch, tmp_path: Path, name: str = "implement-csharp") -> dict:
    out = tmp_path / f"{name}.json"
    assert _run(monkeypatch, "recipe", name, "--format", "json", "-o", str(out)) == 0
    return json.loads(out.read_text(encoding="utf-8"))


def test_export_validates_against_committed_schema(
    real_project: Path, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    doc = _export(monkeypatch, tmp_path)
    schema = json.loads((real_project / SCHEMA).read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
    assert doc["recipe"] == "implement-csharp"
    assert doc["version"] == package_version()
    assert doc["composed_from"][0] == "implementation-developer"
    assert doc["guidelines"] and doc["verification"]
    assert "limits" not in doc


@pytest.mark.parametrize("name", ["implement-csharp", "review-python", "design-diagram"])
def test_every_item_has_id_and_source(
    name: str, real_project: Path, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    doc = _export(monkeypatch, tmp_path, name)
    ids = [g["id"] for g in doc["guidelines"]]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"[A-Z][A-Z0-9]*-\d+", i) for i in ids)
    assert all(g["source"] in doc["composed_from"] for g in doc["guidelines"])
    assert all(re.fullmatch(r"[A-Z][A-Z0-9]*-V\d+", v["id"]) for v in doc["verification"])


def test_export_is_deterministic_and_self_contained(
    real_project: Path, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"
    for out in (first, second):
        assert (
            _run(monkeypatch, "recipe", "implement-csharp", "-f", "json", "-o", str(out))
            == 0
        )
    assert first.read_bytes() == second.read_bytes()
    text = first.read_text(encoding="utf-8")
    assert ".personetta" not in text and str(real_project) not in text
    assert text.endswith("}\n")


def test_stdout_when_no_output_path(real_project: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    assert _run(monkeypatch, "recipe", "implement-csharp", "--format", "json") == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["hash"].startswith("sha256:")


def test_hash_unchanged_by_key_reorder_and_comment(
    data_copy: Path, monkeypatch, tmp_path: Path
) -> None:
    before = _export(monkeypatch, tmp_path)
    path = data_copy / CSHARP_DEV
    lines = path.read_text(encoding="utf-8").splitlines()
    # Comment edit plus moving the top-level 'description' block key order
    path.write_text(
        "# a new comment\n" + "\n".join(lines) + "\n# trailing\n", encoding="utf-8"
    )
    after_comment = _export(monkeypatch, tmp_path)
    assert after_comment["hash"] == before["hash"]

    import yaml

    role = yaml.safe_load(path.read_text(encoding="utf-8"))
    reordered = dict(reversed(list(role.items())))
    path.write_text(yaml.safe_dump(reordered, sort_keys=False), encoding="utf-8")
    after_reorder = _export(monkeypatch, tmp_path)
    assert after_reorder["hash"] == before["hash"]


def test_hash_changes_when_one_guideline_text_changes(
    data_copy: Path, monkeypatch, tmp_path: Path
) -> None:
    before = _export(monkeypatch, tmp_path)
    path = data_copy / CSHARP_DEV
    import yaml

    role = yaml.safe_load(path.read_text(encoding="utf-8"))
    target_id = role["guidelines"][0]["id"]
    role["guidelines"][0]["text"] += " (reworded)"
    path.write_text(yaml.safe_dump(role, sort_keys=False), encoding="utf-8")
    after = _export(monkeypatch, tmp_path)
    assert after["hash"] != before["hash"]
    changed = [g for g in after["guidelines"] if g["id"] == target_id]
    assert changed[0]["text"].endswith("(reworded)")
    assert changed[0]["source"] == "csharp-developer"


def test_install_with_json_is_rejected(real_project: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    assert _run(monkeypatch, "recipe", "implement-csharp", "-f", "json", "--install") == 1
    assert "does not support" in capsys.readouterr().err


def test_unknown_recipe_fails(real_project: Path, monkeypatch) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    with pytest.raises(Exception):
        _run(monkeypatch, "recipe", "no-such-recipe", "-f", "json")


def test_existing_formats_unchanged(
    real_project: Path, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    out = tmp_path / "x.md"
    assert (
        _run(monkeypatch, "recipe", "implement-csharp", "-f", "claude", "-o", str(out))
        == 0
    )
    assert out.read_text(encoding="utf-8").lstrip().startswith("#")


def test_limits_included_only_when_supplied() -> None:
    composed = {
        "_recipe_name": "x",
        "_source_roles": ["r"],
        "guidelines": [],
        "verification": [{"id": "R-V1", "check": "c", "command": "run"}],
        "limits": {"language": "csharp", "type_code_lines": 200},
    }
    doc = build_recipe_export(composed, [], version="9.9.9")
    assert doc["limits"]["type_code_lines"] == 200
    assert doc["version"] == "9.9.9"
    assert doc["verification"][0]["command"] == "run"
    assert doc["model_recommendation"] == {"tier": "fast", "reasoning": "none"}
    assert "limits" not in build_recipe_export({**composed, "limits": {}}, [])


def test_missing_ids_are_errors() -> None:
    from generator.exceptions import LoadError

    base = {"_recipe_name": "x", "_source_roles": [], "verification": []}
    with pytest.raises(LoadError):
        build_recipe_export({**base, "guidelines": ["plain"]}, [])
    with pytest.raises(LoadError):
        build_recipe_export(
            {**base, "guidelines": [], "verification": [{"check": "c"}]}, []
        )


def test_hash_helpers() -> None:
    assert content_hash({"a": 1, "b": 2}) == content_hash({"b": 2, "a": 1})
    assert content_hash({"a": 1}) != content_hash({"a": 2})
    assert render_export({"a": 1}) == '{\n  "a": 1\n}\n'


def test_conflicting_recipe_exits_one(data_copy: Path, monkeypatch, capsys) -> None:
    from generator import recipe_export
    from generator.merge import MergeWarning

    monkeypatch.setattr(
        recipe_export,
        "compose_recipe",
        lambda *a, **k: ({}, [MergeWarning(severity="error", message="boom")]),
    )
    assert _run(monkeypatch, "recipe", "implement-csharp", "-f", "json") == 1
    assert "boom" in capsys.readouterr().err

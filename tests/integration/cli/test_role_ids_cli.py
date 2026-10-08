"""Stable guideline and verification ids, proven through the CLI entry point."""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

import pytest
import yaml

from generator.cli.main import main
from generator.loader import load_merge_config, load_recipe, load_recipe_roles
from generator.merger import compose_recipe
from generator.role_ids import (
    GuidelineText,
    cross_role_id_errors,
    guideline_id,
    normalize_role_ids,
    role_id_errors,
)

pytestmark = [pytest.mark.integration, pytest.mark.cli]

ROLE_GLOBS = ("data/base/**/*.yaml", "data/language_specific/**/*.yaml")
CSHARP_DEV = "data/language_specific/csharp/csharp-developer.yaml"
READABILITY = "data/base/mixins/readability-focused.yaml"


def _role_files(root: Path) -> list[Path]:
    paths: list[Path] = []
    for pattern in ROLE_GLOBS:
        paths.extend(sorted(root.glob(pattern)))
    return [p for p in paths if "base/system" not in p.relative_to(root).as_posix()]


@pytest.fixture
def data_copy(real_project: Path, project_layout, monkeypatch) -> Path:
    """A throwaway copy of the shipped data tree that tests may corrupt."""
    root = project_layout.root
    shutil.copytree(real_project / "data", project_layout.base.parent)
    monkeypatch.setenv("PERSONETTA_BASE", str(root))
    return root


def _run(monkeypatch, *argv: str) -> int:
    monkeypatch.setattr(sys, "argv", ["personetta", *argv])
    return main()


def test_shipped_roles_carry_unique_ids_on_everything(real_project: Path) -> None:
    seen: dict[str, str] = {}
    for path in _role_files(real_project):
        role = yaml.safe_load(path.read_text(encoding="utf-8"))
        for item in role.get("guidelines", []):
            assert re.fullmatch(r"[A-Z][A-Z0-9]*-\d+", item["id"]), path
            assert item["text"].strip()
            assert seen.setdefault(item["id"], path.name) == path.name
        for item in role.get("verification", []):
            assert re.fullmatch(r"[A-Z][A-Z0-9]*-V\d+", item["id"]), path
            assert seen.setdefault(item["id"], path.name) == path.name
    assert len(seen) > 500


def test_validate_passes_on_shipped_data(real_project, monkeypatch, capsys) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    assert _run(monkeypatch, "validate") == 0
    assert "All files valid." in capsys.readouterr().out


def test_validate_fails_on_missing_guideline_id(data_copy, monkeypatch, capsys) -> None:
    path = data_copy / CSHARP_DEV
    text = path.read_text(encoding="utf-8")
    assert "- id: CS-1\n    text:" in text
    path.write_text(text.replace("- id: CS-1\n    text:", "- text:", 1), encoding="utf-8")

    assert _run(monkeypatch, "validate") == 1
    out = capsys.readouterr().out
    assert "csharp-developer.yaml" in out
    assert "guidelines[0]: missing id" in out


def test_validate_fails_on_missing_verification_id(
    data_copy, monkeypatch, capsys
) -> None:
    path = data_copy / CSHARP_DEV
    text = path.read_text(encoding="utf-8")
    assert "- id: CS-V1\n    check:" in text
    path.write_text(
        text.replace("- id: CS-V1\n    check:", "- check:", 1), encoding="utf-8"
    )

    assert _run(monkeypatch, "validate") == 1
    assert "verification[0]: missing id" in capsys.readouterr().out


def test_validate_fails_on_legacy_string_guideline(
    data_copy, monkeypatch, capsys
) -> None:
    path = data_copy / CSHARP_DEV
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace("- id: CS-1\n    text: ", "- ", 1),
        encoding="utf-8",
    )

    assert _run(monkeypatch, "validate") == 1
    assert "guidelines[0]: missing id" in capsys.readouterr().out


def test_validate_fails_on_duplicate_id_within_role(
    data_copy, monkeypatch, capsys
) -> None:
    path = data_copy / CSHARP_DEV
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("- id: CS-2\n", "- id: CS-1\n", 1), encoding="utf-8")

    assert _run(monkeypatch, "validate") == 1
    out = capsys.readouterr().out
    assert "duplicate id 'CS-1'" in out


def test_validate_fails_on_duplicate_id_across_roles(
    data_copy, monkeypatch, capsys
) -> None:
    path = data_copy / READABILITY
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("- id: RB-1\n", "- id: CS-1\n", 1), encoding="utf-8")

    assert _run(monkeypatch, "validate") == 1
    out = capsys.readouterr().out
    assert "id 'CS-1' already used in" in out


def test_validate_fails_on_malformed_id(data_copy, monkeypatch, capsys) -> None:
    path = data_copy / CSHARP_DEV
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("- id: CS-1\n", "- id: cs_one\n", 1), encoding="utf-8")

    assert _run(monkeypatch, "validate") == 1
    assert "does not match" in capsys.readouterr().out


def test_ids_flow_through_composition(real_project: Path) -> None:
    recipe = load_recipe("implement-csharp", real_project)
    compose_roles, mixin_roles = load_recipe_roles(recipe, real_project)
    composed, _ = compose_recipe(
        recipe, compose_roles, mixin_roles, load_merge_config(real_project)
    )

    ids = [guideline_id(g) for g in composed["guidelines"]]
    assert all(ids)
    assert len(set(ids)) == len(ids)
    assert any(i is not None and i.startswith("CS-") for i in ids)
    assert all(
        re.fullmatch(r"[A-Z][A-Z0-9]*-V\d+", v["id"]) for v in composed["verification"]
    )
    # Guidelines still behave as plain strings for every existing consumer.
    assert all(isinstance(g, str) for g in composed["guidelines"])
    assert len(set(composed["guidelines"])) == len(composed["guidelines"])


@pytest.mark.parametrize("fmt", ["claude", "copilot", "cursor", "cline"])
def test_recipe_output_keeps_guideline_wording_with_id_markers(
    real_project, monkeypatch, capsys, fmt
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    assert _run(monkeypatch, "recipe", "implement-csharp", "--format", fmt) == 0
    out = capsys.readouterr().out

    raw = yaml.safe_load((real_project / CSHARP_DEV).read_text(encoding="utf-8"))
    first = raw["guidelines"][0]["text"]
    assert first in out or first[:40] in out
    # Ids appear as a [ID] prefix next to the unchanged wording
    assert re.search(r"\[CS-\d+\] ", out)


def test_unit_normalize_and_error_helpers() -> None:
    role = {"guidelines": [{"id": "X-1", "text": "Do it"}, "legacy", {"text": "no id"}]}
    normalize_role_ids(role)
    first, legacy, noid = role["guidelines"]
    assert isinstance(first, GuidelineText) and first == "Do it" and first.id == "X-1"
    assert guideline_id(first) == "X-1"
    assert legacy == "legacy" and guideline_id(legacy) is None
    assert noid == "no id" and guideline_id(noid) is None

    raw = {
        "guidelines": [{"id": "X-1", "text": "a"}, {"id": "X-1", "text": "b"}, "c"],
        "verification": [{"id": "X-V1", "check": "a"}, {"check": "b"}, "str"],
    }
    errors = role_id_errors(raw)
    assert any("duplicate id 'X-1'" in e for e in errors)
    assert "guidelines[2]: missing id" in errors
    assert "verification[1]: missing id" in errors
    assert "verification[2]: missing id" in errors
    assert role_id_errors({"guidelines": "not a list"}) == []


def test_unit_cross_role_errors_ignore_malformed_items() -> None:
    a = {"guidelines": [{"id": "A-1", "text": "x"}], "verification": [{"id": "A-V1"}]}
    b = {"guidelines": [{"id": "A-1", "text": "y"}, "str", {"text": "z"}]}
    c = {"guidelines": "nope", "verification": [{"id": "A-V1", "check": "k"}]}
    result = cross_role_id_errors([("a", a), ("b", b), ("c", c)])
    assert set(result) == {"b", "c"}
    assert "id 'A-1' already used in a" in result["b"][0]
    assert "id 'A-V1' already used in a" in result["c"][0]
    assert cross_role_id_errors([("a", a), ("a", a)]) == {}

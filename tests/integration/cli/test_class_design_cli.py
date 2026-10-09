"""Class-design mixin and per-language limits, proven through the CLI entry point."""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import jsonschema
import pytest
import yaml

from generator.cli.main import main
from generator.loader import load_merge_config, load_role
from generator.merge import detect_limits_conflicts, merge_roles
from generator.merger import compose_recipe

pytestmark = [pytest.mark.integration, pytest.mark.cli]

EXPORT_SCHEMA = "data/schemas/recipe-export.schema.json"
MIXIN = "data/base/mixins/class-design.yaml"
FAMILIES = ("implement-", "review-", "test-", "debug-", "design-")
LANGUAGES = ("csharp", "javascript", "python", "powershell", "tsql")
LANG_PREFIX = {
    "csharp": "CSCD",
    "javascript": "JSCD",
    "python": "PYCD",
    "powershell": "PSCD",
    "tsql": "TSCD",
}

# The contract's rule text, verbatim (docs/maestro-contract.md, section 3).
CD_TEXT = {
    "CD-1": 'A unit (type, module, function) has a one-sentence purpose; if the sentence needs "and", split it.',
    "CD-2": "One reason to change: a unit changes for one kind of requirement.",
    "CD-3": "Reads top-down: a reader follows it without jumping around.",
    "CD-4": (
        "**A size limit means a redesign, not a workaround.** A unit near its limit got "
        "there by accretion. When a change would push it toward the limit: design for the "
        "unit as it will be after the change, do the redesign as its own step with tests "
        "that pin today's behavior first, and when the redesign is bigger than the task, "
        'stop and say so. Never: partial files, holder or "services" classes, delegation '
        "shims whose only purpose is line count, joined lines, raised baselines."
    ),
    "CD-5": (
        "Methods take 3-4 arguments at most; wider inputs become a record or options type "
        "(records may carry more positional parameters, see the language limits)."
    ),
    "CD-6": (
        "**Readable expressions: name each decision, don't stack syntax.** A condition "
        "joins at most two simple terms (a direct predicate, comparison or null check). "
        "When `&&`/`||` is mixed with a pattern match, an out-variable, a query or a call "
        "chain, extract a named helper even at two terms. Nested decisions become several "
        "helpers, one decision each. A long query chain, or an expression-bodied member "
        "hiding several steps, becomes named steps."
    ),
    "CD-7": (
        "**Named constants, one home each.** Inline literals are allowed only when the "
        "literal is the meaning: `0`, `1`, `-1`, the empty string, `true`/`false`, or a "
        "one-use self-describing local literal (e.g. a one-off display format). "
        "Everything else gets a name in the narrowest shared home all callers can reach, "
        "and every use references that one definition: domain terms, protocol tokens and "
        "wire values in a constants type beside the domain; configuration defaults and "
        "limits in the owning options type; file, folder and marker names in the owning "
        "layout type; reused UI copy in the owning presentation type; test literals "
        "shared across tests in a test constants helper. Two unrelated concepts that "
        "happen to share a value keep two names. Host-rendered line breaks use the "
        "platform newline; a line ending with protocol meaning (CSV's CRLF) is a named "
        "wire constant."
    ),
}

# Fixed by the contract; Maestro's size guard enforces exactly these.
CSHARP_LIMITS = {
    "language": "csharp",
    "type_code_lines": 200,
    "members_per_type": 15,
    "lines_per_method": 30,
    "branch_points_per_method": 10,
    "positional_parameters_per_record": 12,
    "lines_per_file": 1000,
}


def _run(monkeypatch, *argv: str) -> int:
    monkeypatch.setattr(sys, "argv", ["personetta", *argv])
    return main()


def _recipe_languages(root: Path) -> dict[str, str]:
    """Recipe name -> language, for every family recipe built on a language role."""
    result: dict[str, str] = {}
    for path in sorted((root / "data" / "recipes").glob("*.yaml")):
        if not path.name.startswith(FAMILIES):
            continue
        refs = re.findall(r"language[-_]specific/([a-z]+)/", path.read_text("utf-8"))
        langs = set(refs)
        if langs:
            assert len(langs) == 1, path
            result[path.stem] = langs.pop()
    return result


def _lang_role_path(root: Path, language: str) -> Path:
    return (
        root / "data" / "language_specific" / language / f"{language}-class-design.yaml"
    )


ROOT = Path(__file__).resolve().parents[3]
RECIPES = _recipe_languages(ROOT)


@pytest.fixture
def data_copy(real_project: Path, project_layout, monkeypatch) -> Path:
    root = project_layout.root
    shutil.copytree(real_project / "data", project_layout.base.parent)
    monkeypatch.setenv("PERSONETTA_BASE", str(root))
    return root


def test_family_recipes_cover_every_language() -> None:
    assert set(RECIPES.values()) == set(LANGUAGES)
    assert len(RECIPES) >= 50


def test_mixin_carries_contract_rule_text_verbatim(real_project: Path) -> None:
    role = yaml.safe_load((real_project / MIXIN).read_text(encoding="utf-8"))
    assert role["name"] == "class-design" and role["type"] == "mixin"
    assert {g["id"]: g["text"] for g in role["guidelines"]} == CD_TEXT
    contract = (real_project / "docs" / "maestro-contract.md").read_text("utf-8")
    flat = " ".join(contract.split())
    for gid, text in CD_TEXT.items():
        assert f"`{gid}` {text}" in flat, gid


@pytest.mark.parametrize("name", sorted(RECIPES))
def test_every_family_recipe_exports_cd_rules_and_its_limits(
    name: str, real_project: Path, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    out = tmp_path / f"{name}.json"
    assert _run(monkeypatch, "recipe", name, "--format", "json", "-o", str(out)) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads((real_project / EXPORT_SCHEMA).read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)

    language = RECIPES[name]
    assert doc["limits"]["language"] == language
    by_id = {g["id"]: g for g in doc["guidelines"]}
    for gid, text in CD_TEXT.items():
        assert by_id[gid] == {"id": gid, "text": text, "source": "class-design"}
    prefix = LANG_PREFIX[language]
    lang_ids = [g["id"] for g in doc["guidelines"] if g["id"].startswith(prefix + "-")]
    assert lang_ids and all(
        by_id[i]["source"] == f"{language}-class-design" for i in lang_ids
    )
    assert {"class-design", f"{language}-class-design"} <= set(doc["composed_from"])


def test_csharp_numbers_are_the_contract_numbers(
    real_project: Path, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    out = tmp_path / "c.json"
    assert (
        _run(monkeypatch, "recipe", "implement-csharp", "-f", "json", "-o", str(out)) == 0
    )
    assert json.loads(out.read_text(encoding="utf-8"))["limits"] == CSHARP_LIMITS


@pytest.mark.parametrize("language", LANGUAGES)
def test_each_limit_is_stated_in_prose_and_reasoned_in_description(
    language: str, real_project: Path
) -> None:
    role = yaml.safe_load(_lang_role_path(real_project, language).read_text("utf-8"))
    limits = role["limits"]
    assert limits["language"] == language and len(limits) > 3
    prose = " ".join(g["text"] for g in role["guidelines"])
    description = role["description"]
    assert "Source" in description
    for key, value in limits.items():
        if key == "language":
            continue
        assert isinstance(value, int) and value > 0, key
        assert re.search(rf"\b{value}\b", prose), (key, value)
        # Each number is named with its value and reasoning in the description
        assert re.search(rf"\b{key} {value} —", description), key


def test_claude_output_carries_class_design_rules(
    real_project: Path, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    out = tmp_path / "x.md"
    assert (
        _run(monkeypatch, "recipe", "implement-csharp", "-f", "claude", "-o", str(out))
        == 0
    )
    text = out.read_text(encoding="utf-8")
    assert "A size limit means a redesign, not a workaround." in text
    assert "200 code lines" in text


def test_rules_run_cd_1_to_cd_7_in_order(real_project: Path) -> None:
    role = yaml.safe_load((real_project / MIXIN).read_text(encoding="utf-8"))
    assert [g["id"] for g in role["guidelines"]] == [f"CD-{n}" for n in range(1, 8)]


@pytest.mark.parametrize("fmt", ["claude", "copilot", "cursor"])
def test_csharp_worked_examples_appear_in_formatted_output(
    fmt: str, real_project: Path, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    out = tmp_path / "x.md"
    argv = ("recipe", "implement-csharp", "-f", fmt, "-o", str(out))
    assert _run(monkeypatch, *argv) == 0
    text = out.read_text(encoding="utf-8")
    assert "TryGetCitedPaths" in text
    assert "IsWithinHeadroom" in text
    assert "Rfc4180Csv.RowTerminator" in text
    assert "CD-6: " in text and "CD-7: " in text


def test_other_languages_carry_no_csharp_examples(
    real_project: Path, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    out = tmp_path / "p.md"
    argv = ("recipe", "implement-python", "-f", "claude", "-o", str(out))
    assert _run(monkeypatch, *argv) == 0
    assert "TryGetCitedPaths" not in out.read_text(encoding="utf-8")


def test_validate_passes_with_new_roles(real_project, monkeypatch, capsys) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    assert _run(monkeypatch, "validate") == 0
    assert "All files valid." in capsys.readouterr().out


def test_validate_rejects_reused_cd_id(data_copy: Path, monkeypatch, capsys) -> None:
    path = _lang_role_path(data_copy, "python")
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("id: PYCD-1", "id: CD-1"), encoding="utf-8")
    assert _run(monkeypatch, "validate") == 1
    assert "already used" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("  lines_per_function: 25", "  lines_per_function: many"),
        ("  lines_per_function: 25", "  lines_per_function: 0"),
        ("  language: python\n", ""),
        ("  lines_per_function: 25", "  LinesPerFunction: 25"),
    ],
)
def test_validate_rejects_malformed_limits(
    old: str, new: str, data_copy: Path, monkeypatch, capsys
) -> None:
    path = _lang_role_path(data_copy, "python")
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    assert _run(monkeypatch, "validate") == 1
    assert "python-class-design.yaml" in capsys.readouterr().out


def test_two_languages_keep_first_limits_and_warn(real_project: Path) -> None:
    roles = [
        load_role(f"language-specific/{lang}/{lang}-class-design", real_project)
        for lang in ("python", "csharp")
    ]
    recipe = {"name": "mixed", "compose": ["x"]}
    composed, warnings = compose_recipe(
        recipe, roles[:1], roles[1:], load_merge_config(real_project)
    )
    assert composed["limits"]["language"] == "python"
    messages = [w.message for w in warnings if w.severity == "warning"]
    assert any("keeping 'python'" in m and "csharp" in m for m in messages)


def test_limits_conflict_detection_edges() -> None:
    py = {"name": "a", "limits": {"language": "python", "x": 1}}
    assert detect_limits_conflicts([]) == []
    assert detect_limits_conflicts([py, {"name": "b"}]) == []
    assert detect_limits_conflicts([py, {**py, "name": "c"}]) == []
    assert detect_limits_conflicts([py, {"name": "d", "limits": {"x": 1}}]) == []
    found = detect_limits_conflicts(
        [
            py,
            {"name": "e", "limits": {"language": "tsql"}},
            {"limits": {"language": "go"}},
        ]
    )
    assert len(found) == 1
    assert "ignoring tsql, go" in found[0].message and "'a'" in found[0].message


def test_limits_merge_without_config_uses_priority_default() -> None:
    merged = merge_roles(
        [
            {"name": "a"},
            {"name": "b", "limits": {"language": "tsql", "objects_per_file": 1}},
        ]
    )
    assert merged["limits"] == {"language": "tsql", "objects_per_file": 1}
    assert "limits" not in merge_roles([{"name": "a"}])

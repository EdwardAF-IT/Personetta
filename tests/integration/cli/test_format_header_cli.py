"""Version, hash and ids in the claude/copilot/cursor/cline formats, via the CLI."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

from generator.cli.main import main
from generator.formatters import (
    format_claude,
    format_cline,
    format_copilot,
    format_cursor,
)
from generator.loader import load_merge_config, load_recipe, load_recipe_roles
from generator.merger import compose_recipe

pytestmark = [pytest.mark.integration, pytest.mark.cli]

FORMATS = ("claude", "copilot", "cursor", "cline")
RECIPE = "implement-csharp"
HASH_RE = re.compile(r"hash `(sha256:[0-9a-f]{64})`")
VERSION_RE = re.compile(r" v(\S+) · hash")
ID_RE = re.compile(r"^- (?:\[ \] )?\[([A-Z][A-Z0-9]*-(?:V)?\d+)\] ", re.MULTILINE)


def _group(pattern: re.Pattern[str], text: str) -> str:
    match = pattern.search(text)
    assert match is not None
    return match.group(1)


def _run(monkeypatch, *argv: str) -> int:
    monkeypatch.setattr(sys, "argv", ["personetta", *argv])
    return main()


@pytest.fixture
def base(real_project: Path, monkeypatch) -> Path:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    return real_project


def _render(monkeypatch, tmp_path: Path, fmt: str, name: str = RECIPE) -> str:
    out = tmp_path / f"{fmt}-{name}.md"
    assert _run(monkeypatch, "recipe", name, "--format", fmt, "-o", str(out)) == 0
    return out.read_text(encoding="utf-8")


def _export(monkeypatch, tmp_path: Path, name: str = RECIPE) -> dict:
    out = tmp_path / f"{name}.json"
    assert _run(monkeypatch, "recipe", name, "--format", "json", "-o", str(out)) == 0
    return json.loads(out.read_text(encoding="utf-8"))


@pytest.mark.parametrize("fmt", FORMATS)
def test_header_matches_json_export(fmt: str, base, monkeypatch, tmp_path: Path) -> None:
    doc = _export(monkeypatch, tmp_path)
    text = _render(monkeypatch, tmp_path, fmt)

    assert _group(HASH_RE, text) == doc["hash"]
    assert _group(VERSION_RE, text) == doc["version"]
    shown = ID_RE.findall(text)
    expected = [g["id"] for g in doc["guidelines"]] + [
        v["id"] for v in doc["verification"]
    ]
    assert sorted(shown) == sorted(expected)
    assert "CD-4" in shown


@pytest.mark.parametrize("fmt", FORMATS)
def test_header_does_not_change_the_hash(
    fmt: str, base, monkeypatch, tmp_path: Path
) -> None:
    """The hash is computed from content, so rendering twice (header and all) agrees."""
    first = _group(HASH_RE, _render(monkeypatch, tmp_path, fmt))
    second = _group(HASH_RE, _render(monkeypatch, tmp_path, fmt))
    assert first == second == _export(monkeypatch, tmp_path)["hash"]


def test_cursor_frontmatter_stays_first_and_valid(
    base, monkeypatch, tmp_path: Path
) -> None:
    text = _render(monkeypatch, tmp_path, "cursor")
    assert text.startswith("---\ndescription: ")
    front, _, body = text[3:].partition("\n---")
    assert "alwaysApply: true" in front
    assert "sha256" not in front
    assert "sha256" in body.split("## Operating contract")[0]


@pytest.mark.parametrize("fmt", ["claude", "copilot", "cline"])
def test_plain_formats_keep_title_first(
    fmt: str, base, monkeypatch, tmp_path: Path
) -> None:
    lines = _render(monkeypatch, tmp_path, fmt).splitlines()
    assert lines[0] == "# Implement Csharp"
    assert lines[2].startswith("> Personetta recipe `implement-csharp` v")


def _legacy(fmt: str, name: str = RECIPE) -> str:
    """Pre-header output: same formatter with identity and id markers removed."""
    root = Path(__import__("os").environ["PERSONETTA_BASE"])
    recipe = load_recipe(name, root)
    compose, mixin = load_recipe_roles(recipe, root)
    composed, _ = compose_recipe(recipe, compose, mixin, load_merge_config(root))
    composed.pop("_identity")
    composed["guidelines"] = [str(g) for g in composed["guidelines"]]
    for v in composed["verification"]:
        v.pop("id", None)
    fn = {
        "claude": format_claude,
        "copilot": format_copilot,
        "cline": format_cline,
        "cursor": format_cursor,
    }[fmt]
    return fn(composed)


def _strip(text: str) -> str:
    text = re.sub(r"^> Personetta recipe `.*\n(?:\n)?", "", text, flags=re.MULTILINE)
    return re.sub(
        r"^(- (?:\[ \] )?)\[[A-Z][A-Z0-9]*-(?:V)?\d+\] ", r"\1", text, flags=re.MULTILINE
    )


@pytest.mark.parametrize("fmt", ["claude", "copilot", "cline"])
def test_output_differs_only_by_header_and_markers(
    fmt: str, base, monkeypatch, tmp_path: Path
) -> None:
    assert _strip(_render(monkeypatch, tmp_path, fmt)) == _legacy(fmt)


def test_cursor_output_differs_only_by_header_and_markers(
    base, monkeypatch, tmp_path: Path
) -> None:
    text = _render(monkeypatch, tmp_path, "cursor")
    stripped = re.sub(r"^> Personetta recipe `.*\n", "", text, flags=re.MULTILINE)
    stripped = _strip(stripped)
    assert stripped == _legacy("cursor")


def test_installed_cache_and_active_files_carry_header(
    base, monkeypatch, tmp_path: Path
) -> None:
    target = tmp_path / "proj"
    target.mkdir()
    assert (
        _run(
            monkeypatch,
            "recipe",
            RECIPE,
            "--format",
            "claude",
            "--install",
            "--target",
            "project",
            str(target),
        )
        == 0
    )
    cached = next(target.rglob(f"claude-recipes/{RECIPE}.md"))
    assert HASH_RE.search(cached.read_text(encoding="utf-8"))


def test_unknown_ids_degrade_to_no_header() -> None:
    """Hand-built roles without ids still format exactly as before."""
    composed = {"_recipe_name": "x", "guidelines": ["plain"], "verification": []}
    assert "> Personetta recipe" not in format_copilot(composed)
    assert "- plain" in format_copilot(composed)

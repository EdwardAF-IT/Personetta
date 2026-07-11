"""Tests for the ingest source registry loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.ingest.sources import load_sources, resolve_source

pytestmark = [pytest.mark.unit, pytest.mark.readonly]


def test_loads_shipped_registry(project_root: Path) -> None:
    sources = load_sources(project_root)
    assert "dotnet-skills" in sources
    assert sources["dotnet-skills"].name == "dotnet/skills"
    assert sources["dotnet-skills"].owner == "dotnet"
    assert sources["awesome-claude-code"].kind == "index"


def test_resolve_by_key_and_by_name(project_root: Path) -> None:
    sources = load_sources(project_root)
    by_key = resolve_source(sources, "superpowers")
    by_name = resolve_source(sources, "obra/superpowers")
    assert by_key is not None and by_key is by_name


def test_resolve_unknown_returns_none(project_root: Path) -> None:
    assert resolve_source(load_sources(project_root), "nope/missing") is None


def test_missing_registry_returns_empty(tmp_path: Path) -> None:
    assert load_sources(tmp_path) == {}

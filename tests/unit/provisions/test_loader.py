"""Tests for loading and merging the provisions configuration."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from generator.paths import provisions_user_path
from generator.provisions.loader import (
    _merge_docs,
    _merge_named,
    _parse_config,
    default_provisions_path,
    load_provisions,
)

pytestmark = [pytest.mark.unit, pytest.mark.modifying]


def _write_default(base_dir: Path, doc: dict) -> None:
    path = default_provisions_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc), encoding="utf-8")


def _write_user(target: Path, doc: dict) -> None:
    path = provisions_user_path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc), encoding="utf-8")


def test_merge_named_user_deep_merges_over_default() -> None:
    default = {"p": {"kind": "plugin", "enabled": False, "install": {"a": 1}}}
    user = {"p": {"enabled": True, "install": {"b": 2}}}
    merged = _merge_named(default, user)
    assert merged["p"]["enabled"] is True
    assert merged["p"]["install"] == {"a": 1, "b": 2}
    assert merged["p"]["kind"] == "plugin"


def test_merge_named_adds_user_only_entries() -> None:
    merged = _merge_named({}, {"new": {"kind": "behavior"}})
    assert merged["new"]["kind"] == "behavior"


def test_merge_docs_prefers_user_version() -> None:
    merged = _merge_docs({"version": 1}, {"version": 2})
    assert merged["version"] == 2


def test_merge_docs_defaults_missing_sections() -> None:
    merged = _merge_docs({}, {})
    assert merged == {"version": 1, "provisions": {}, "bundles": {}}


def test_parse_config_builds_models() -> None:
    doc = {
        "version": 1,
        "provisions": {
            "p": {"kind": "tool-setting", "enabled": True, "targets": ["claude"]}
        },
        "bundles": {"b": {"members": ["p"], "enabled": True}},
    }
    config = _parse_config(doc)
    assert config.provisions["p"].targets == ("claude",)
    assert config.bundles["b"].members == ("p",)


def test_load_provisions_merges_default_and_user(tmp_path: Path) -> None:
    base_dir = tmp_path / "base"
    target = tmp_path / "home"
    _write_default(
        base_dir,
        {
            "version": 1,
            "provisions": {
                "status-line": {
                    "kind": "tool-setting",
                    "enabled": False,
                    "targets": ["claude"],
                }
            },
        },
    )
    _write_user(target, {"provisions": {"status-line": {"enabled": True}}})

    config = load_provisions(base_dir, target)
    assert config.provisions["status-line"].enabled is True
    assert [p.name for p in config.enabled_provisions()] == ["status-line"]


def test_load_provisions_without_user_file(tmp_path: Path) -> None:
    base_dir = tmp_path / "base"
    target = tmp_path / "home"
    _write_default(
        base_dir,
        {"version": 1, "provisions": {"p": {"kind": "plugin"}}},
    )
    config = load_provisions(base_dir, target)
    assert "p" in config.provisions
    assert config.enabled_provisions() == ()


def test_load_real_default_config() -> None:
    """The shipped default config loads and validates against the schema."""
    from generator.cli.commands._helpers import get_base_dir

    config = load_provisions(get_base_dir(), Path("/nonexistent-target"))
    assert "status-line" in config.provisions
    assert "economy" in config.bundles
    # Deploy-dark: nothing enabled by default.
    assert config.enabled_provisions() == ()
    assert config.enabled_bundles() == ()

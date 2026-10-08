"""Unit tests for ids, the JSON export, limits conflicts and format identity."""

from __future__ import annotations

import importlib.metadata

import pytest

from generator import recipe_export, role_ids
from generator.exceptions import LoadError
from generator.formatters.common import id_marker, identity_line
from generator.merge.conflict_detection import MergeWarning, detect_limits_conflicts
from generator.role_ids import (
    GuidelineText,
    cross_role_id_errors,
    guideline_id,
    normalize_role_ids,
    role_id_errors,
)

pytestmark = [pytest.mark.unit]


# -- role_ids ---------------------------------------------------------------


def test_normalize_turns_mappings_into_id_carrying_text():
    role = {"guidelines": [{"id": "X-1", "text": "do it"}, "plain"]}
    normalize_role_ids(role)
    assert role["guidelines"][0] == "do it"
    assert guideline_id(role["guidelines"][0]) == "X-1"
    assert guideline_id(role["guidelines"][1]) is None


def test_normalize_mapping_without_id_degrades_to_text():
    role = normalize_role_ids({"guidelines": [{"text": "no id"}, {"other": 1}]})
    assert role["guidelines"][0] == "no id"
    assert guideline_id(role["guidelines"][0]) is None
    assert role["guidelines"][1] == {"other": 1}


def test_normalize_ignores_role_without_guidelines():
    assert normalize_role_ids({"name": "r"}) == {"name": "r"}


def test_role_id_errors_reports_missing_and_duplicate():
    role = {
        "guidelines": [{"id": "A-1", "text": "a"}, {"text": "b"}, "bare"],
        "verification": [{"id": "A-1", "check": "c"}, {"id": "", "check": "d"}],
    }
    errors = role_id_errors(role)
    assert "guidelines[1]: missing id" in errors
    assert "guidelines[2]: missing id" in errors
    assert any("duplicate id 'A-1'" in e for e in errors)
    assert "verification[1]: missing id" in errors


def test_role_id_errors_skips_non_list_sections():
    assert role_id_errors({"guidelines": "x", "verification": None}) == []


def test_cross_role_id_errors_flags_reuse_in_later_file():
    roles = [
        ("a.yaml", {"guidelines": [{"id": "Z-1", "text": "t"}]}),
        ("b.yaml", {"verification": [{"id": "Z-1", "check": "c"}, {"check": "x"}]}),
        ("c.yaml", {"guidelines": "nope"}),
    ]
    result = cross_role_id_errors(roles)
    assert list(result) == ["b.yaml"]
    assert "already used in a.yaml" in result["b.yaml"][0]


def test_guideline_text_is_a_str_with_id():
    item = GuidelineText("hello", "H-1")
    assert item == "hello" and item.id == "H-1"
    assert role_ids.guideline_id("plain") is None


# -- recipe_export ----------------------------------------------------------


def test_package_version_falls_back_when_not_installed(monkeypatch):
    def boom(_name):
        raise importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(importlib.metadata, "version", boom)
    assert recipe_export.package_version() == recipe_export.FALLBACK_VERSION


def test_content_hash_ignores_key_order_and_tracks_text():
    a = recipe_export.content_hash({"x": 1, "y": [1, 2]})
    assert a == recipe_export.content_hash({"y": [1, 2], "x": 1})
    assert a != recipe_export.content_hash({"x": 1, "y": [2, 1]})
    assert a.startswith("sha256:")


def _composed(**over) -> dict:
    base = {
        "_recipe_name": "r",
        "_source_roles": ["one"],
        "guidelines": [GuidelineText("g", "G-1")],
        "verification": [
            {"id": "V-1", "check": "c", "command": "cmd"},
            {"id": "V-2", "check": "d"},
        ],
        "tone": "t",
        "output_format": "o",
        "_model_recommendation": {
            "min_tier": "standard",
            "reasoning": "r",
            "rationale": "why",
        },
    }
    base.update(over)
    return base


def test_build_export_shapes_every_section():
    roles = [{"name": "one", "guidelines": [GuidelineText("g", "G-1")]}]
    doc = recipe_export.build_recipe_export(
        _composed(limits={"language": "csharp"}), roles, version="9.9.9"
    )
    assert doc["version"] == "9.9.9"
    assert doc["guidelines"] == [{"id": "G-1", "text": "g", "source": "one"}]
    assert doc["verification"][0] == {"id": "V-1", "check": "c", "command": "cmd"}
    assert "command" not in doc["verification"][1]
    assert doc["model_recommendation"]["rationale"] == "why"
    assert doc["limits"] == {"language": "csharp"}


def test_build_export_omits_limits_and_defaults_model():
    doc = recipe_export.build_recipe_export(
        _composed(_model_recommendation=None), [], version="1"
    )
    assert "limits" not in doc
    assert doc["model_recommendation"] == {"tier": "fast", "reasoning": "none"}
    assert doc["guidelines"][0]["source"] == "?"


def test_guideline_without_id_is_a_load_error():
    with pytest.raises(LoadError, match="without an id"):
        recipe_export.build_recipe_export(_composed(guidelines=["bare"]), [])


def test_verification_without_id_is_a_load_error():
    with pytest.raises(LoadError, match="verification item without an id"):
        recipe_export.build_recipe_export(_composed(verification=[{"check": "c"}]), [])


def test_recipe_identity_none_when_not_exportable():
    assert recipe_export.recipe_identity(_composed(guidelines=["bare"]), []) is None
    identity = recipe_export.recipe_identity(_composed(), [])
    assert identity is not None and identity["hash"].startswith("sha256:")


def test_export_recipe_real_recipe_is_deterministic(real_project):
    first, warnings = recipe_export.export_recipe("implement-csharp", real_project)
    second, _ = recipe_export.export_recipe("implement-csharp", real_project)
    assert first == second and not any(w.severity == "error" for w in warnings)
    assert first["limits"]["language"] == "csharp"
    assert recipe_export.render_export(first).endswith("}\n")


def test_export_recipe_returns_empty_on_merge_error(real_project, monkeypatch):
    err = MergeWarning("error", "boom")
    monkeypatch.setattr(recipe_export, "compose_recipe", lambda *a, **k: ({}, [err]))
    doc, warnings = recipe_export.export_recipe("implement-csharp", real_project)
    assert doc == {} and warnings == [err]


# -- limits conflicts and warnings ------------------------------------------


def test_limits_conflict_names_kept_and_dropped_language():
    roles = [
        {"name": "a", "limits": {"language": "csharp"}},
        {"name": "b", "limits": {"language": "python"}},
        {"name": "c"},
        {"name": "d", "limits": "bad"},
    ]
    (warning,) = detect_limits_conflicts(roles)
    assert (
        warning.is_warning and "csharp" in warning.message and "python" in warning.message
    )


def test_limits_conflict_quiet_for_one_language():
    roles = [{"name": "a", "limits": {"language": "csharp"}}] * 2
    assert detect_limits_conflicts(roles) == []


def test_merge_warning_severity_flags():
    assert MergeWarning("error", "x").is_error
    assert MergeWarning("info", "x").is_info
    with pytest.raises(ValueError):
        MergeWarning("fatal", "x")


# -- format identity --------------------------------------------------------


def test_identity_line_and_marker():
    assert identity_line({}) is None
    line = identity_line(
        {"_recipe_name": "r", "_identity": {"version": "1.2", "hash": "sha256:ab"}}
    )
    assert line and "v1.2" in line and "sha256:ab" in line
    assert id_marker(GuidelineText("t", "CS-4")) == "[CS-4] "
    assert id_marker("plain") == ""
